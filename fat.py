'''
@title		FAT-like file-system
@filename	fat-fuse.py
@class		CS137 - File Systems 
@author		Mike Bartoli
@email		bartolimichael@gmail.com
'''
#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import cPickle as pickle
import pprint

from fuse import FUSE, FuseOSError, Operations

debug = True
block_table_path = 'block_table.pkl'
disk_path = 'fat_disk.pkl'
fat_disk_size = 10485760 #10MB
block_size = 4096
superblock_path = 'superblock.pkl'
max_num_of_files = fat_disk_size / block_size

class Passthrough(Operations):
    def __init__(self, root):
        self.root = root

	#check if valid block size
        if fat_disk_size % 512 != 0:
		raise ValueError('Bad block size')	

	#if the file allocation table doesn't exit, create one
	if os.path.isfile(disk_path) != True:
		table = {}
		for i in range(0, fat_disk_size/block_size):#fat_disk_size/block_size):
			table[i] = [00]*4096	
		pkl_file = open(disk_path,'wb')
		pickle.dump(table, pkl_file)
		pkl_file.close()
	
	#if the binary file holding the data doesn't exist, create it
        if os.path.isfile(block_table_path) != True:
                table = {}
                for i in range(0, fat_disk_size/block_size):#fat_disk_size/block_size):
                        table[i] = 0
                pkl_file = open(block_table_path,'wb')
                pickle.dump(table, pkl_file)
                pkl_file.close()

	#if the superblock doesn't exist, create it
	if os.path.isfile(superblock_path) != True: 
		table = {}
		pkl_file = open(superblock_path,'wb')
		pickle.dump(table, pkl_file)
		pkl_file.close()
                #table['.'] = [1]
                #table['..'] = [2]
  

	if debug:
		print os.stat(block_table_path).st_size
		pkl_file = open(block_table_path,'rb')
		data1 = pickle.load(pkl_file) 
		#pprint.pprint(data1)
		pkl_file.close()

	if debug:
		if os.path.isfile(disk_path) and os.path.isfile(block_table_path):
			print 'success!'
		else:
			print 'you screwed up, no fat'
		free_list = self._get_free_list()


    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _get_free_list(self):
	pkl_file = open(block_table_path, 'rb') 
	block_table = pickle.load(pkl_file)
	free_list = []
	keys = block_table.keys()
	for key in keys: 
		value = block_table[key]
		if value == 0: 
			free_list.append(str(key))
	pkl_file.close()
	return free_list

    def _get_starting_block(self, partial):
	if partial.startswith("/"):
	    partial = partial[1:] #filename
	pkl_file = open(superblock_path, 'rb')
	superblock = pickle.load(pkl_file)
	file_info = superblock[partial] 
	starting_block = file_info[0]
	pkl_file.close() 
	return starting_bock

    def _get_free_space(self):
	free_list = self._get_free_list() 
	free_bytes = len(free_list)*block_size
	return free_bytes

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
	if debug:
		print "getattr"
        full_path = self._full_path(path)
	print path
	print full_path
        st = os.lstat(full_path)
        data = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
	#print data
	return data

    def readdir(self, path, fh):
	if debug:
		print "readdir"
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
	if debug:
		print "rmdir" 
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
	if debug:
		print "mkdir"
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new):
	if debug:
		print "rename" 
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
	print "open" 
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
	print "create" 
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
	print "read" 
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
	print "write" 
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
	print "truncate" 
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def main(mountpoint, root):
    FUSE(Passthrough(root), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
