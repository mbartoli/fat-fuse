'''
@title		FAT-like file-system
@filename	fat-fuse.py
@class		CS137 - File Systems 
@author		Mike Bartoli
@email		michael.bartoli@pomona.edu

External resources used:
Linux man pages
Korokithakis blog post on writing a sample FUSE filesystem 
with fusepy https://www.stavros.io/posts/python-fuse-filesystem/
'''
#!/usr/bin/env python

from __future__ import with_statement
from time import time
from errno import ENOENT

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
free_list_path = 'free_list.pkl' 
folder_enc = 16893
file_enc = 33204

class Passthrough(Operations):
    def __init__(self, root, mountpoint):
        self.root = root
	self.mountpoint = mountpoint

	#check if valid block size
        if fat_disk_size % 512 != 0:
		raise ValueError('Bad block size')	

	#if the disk doesn't exit, create one
	if os.path.isfile(disk_path) != True:
		table = {}
		for i in range(0, fat_disk_size/block_size):
			table[i] = ['00']*block_size	
		pkl_file = open(disk_path,'wb')
		pickle.dump(table, pkl_file)
		pkl_file.close()
	
	#if the block table doesn't exist, create it
        if os.path.isfile(block_table_path) != True:
                table = {}
                for i in range(0, fat_disk_size/block_size):
                        table[i] = 0
                pkl_file = open(block_table_path,'wb')
                pickle.dump(table, pkl_file)
                pkl_file.close()

	#if the superblock doesn't exist, create it
	if os.path.isfile(superblock_path) != True:
                # encoding is [file_type, size, file_name, first_block] 
		table = [[folder_enc, block_size, '/', 0]]
		pkl_file = open(superblock_path,'wb')
		pickle.dump(table, pkl_file)
		pkl_file.close()
  
	#if the freelist doesn't exist, create it 
	if os.path.isfile(free_list_path) != True:
		freelist = []
		for i in range(1, fat_disk_size/block_size):
			freelist.append(i)
		pkl_file = open(free_list_path,'wb')
		pickle.dump(freelist, pkl_file)
		pkl_file.close()
		

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _full_mount_path(self, partial):
	if partial.startswith("/"):
	    partial = partial[1:]
	path = os.path.join(self.mountpoint, partial)
	return path

    def _get_free_list(self):
	'''pkl_file = open(block_table_path, 'rb') 
	block_table = pickle.load(pkl_file)
	free_list = []
	keys = block_table.keys()
	for key in keys: 
		value = block_table[key]
		if value == 0: #doesn't work bc end of linked list  
			free_list.append(str(key))
	pkl_file.close()
	return free_list
	'''
        pkl_file = open(free_list_path,'rb')
        free_list = pickle.load(pkl_file)
        pkl_file.close()
	return free_list
	
	

    def _get_starting_block(self, partial):
	if partial.startswith("/"):
	    partial = partial[1:] #filename
	pkl_file = open(superblock_path, 'rb')
	superblock = pickle.load(pkl_file)
	file_info = superblock[partial] 
	starting_block = file_info[3]
	pkl_file.close() 
	return starting_bock

    def _get_free_space(self):
	free_list = self._get_free_list() 
	free_bytes = len(free_list)*block_size
	return free_bytes

    def _get_file_size(self, path):
	pkl_file = open(superblock_path, 'rb')
        superblock = pickle.load(pkl_file)
	try:
		file_size = 0
		for entry in superblock:
			if entry[2] == path:				
        			file_size = entry[1]
	except:
		file_size = 0
		pass
        pkl_file.close()
        return file_size

    def _get_file_mode(self, path):
        pkl_file = open(superblock_path, 'rb')
        superblock = pickle.load(pkl_file)
        try:
                file_type = 0
                for entry in superblock:
                        if entry[2] == path:
                                file_type = entry[0]

		pkl_file.close() 
		return file_type
	except:
		file_type = 0
		pkl_file.close()
		pass
        return file_type

    def _get_hard_links(self, path):
	return 2

    # Filesystem methods
    # ==================

    def access(self, path, mode):
	if debug:
		print "access"
        """full_path = self._full_mount_path(path)
	print full_path
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)"""

    def getattr(self, path, fh=None):
	if debug:
		print "getattr"
        full_path = self._full_path(path)
	print path
        pkl_file = open(superblock_path, 'rb')
        superblock = pickle.load(pkl_file)
        pkl_file.close()

	data = {
		"st_ctime" : 1456615173,
                "st_mtime" : 1456615173,
                "st_nlink" : self._get_hard_links(path),
		"st_mode" : self._get_file_mode(path),
        	"st_size" : self._get_file_size(path),
                "st_gid" : 1000,
		"st_uid" : 1000,
                "st_atime" : time(),
	}

	print 'getattr path: ' + path
        for entry in superblock:
	        if entry[2] == path:
			return data
	raise FuseOSError(ENOENT)
	return 0

    def readdir(self, path, fh):
	if debug:
		print "readdir"
        full_path = self._full_mount_path(path)
        superblock_pkl = open(superblock_path,'rb')
        superblock = pickle.load(superblock_pkl)
        superblock_pkl.close()
	dirents = ['.', '..']
	for key in superblock:
		raw_path = key[2]
		if path == '/':
			rel_path = raw_path.split('/')
			if len(rel_path) == 2 and rel_path != ['','']:
				dirents.append(rel_path[1])
		elif raw_path.startswith(path) and raw_path != path:
			rel_path = raw_path[len(path):]
			sp_rel_path = rel_path.split('/')
			if len(sp_rel_path) == 2:
				dirents.append(sp_rel_path[1])
        for r in dirents:
            yield r

    def readlink(self, path): #ignore
	if debug:
		print "readlink"
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev): #ignore 
	if debug:
		print "mknod"
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path): #ignore
	if debug:
		print "rmdir" 
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode): 
	if debug:
		print "mkdir"
        superblock_pkl = open(superblock_path,'rb')
	old_superblock = pickle.load(superblock_pkl)
	superblock_pkl.close()
	
	# allocate space from the free list
	old_freelist = self._get_free_list()
	freelist = old_freelist[1:]
	folder_block = old_freelist[0]	
	if debug:
		print "folder block:  "+str(folder_block)

        freelist_pkl = open(free_list_path,'wb')
        pickle.dump(freelist, freelist_pkl)
	
	# update the superblock
	superblock = old_superblock	
	superblock.append([folder_enc, block_size, path, folder_block])
	superblock_pkl = open(superblock_path,'wb')
	pickle.dump(superblock, superblock_pkl)

	# ignore block table
	# ignore disk	

        freelist_pkl.close()
        superblock_pkl.close()
        return 0

    def statfs(self, path):
	if debug:
		print "statfs"
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path): #ignore
        return os.unlink(self._full_path(path))

    def symlink(self, name, target): #ignore
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new): #ignore
	if debug:
		print "rename" 
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name): #ignore
	if debug:
		print "link"
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None): #ignore
        return os.utime(self._full_path(path), times)

    # File methods (currently unimplemented) 
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

    def flush(self, path, fh): #ignore
        return os.fsync(fh)

    def release(self, path, fh): #ignore
        return os.close(fh)

    def fsync(self, path, fdatasync, fh): #ignore
        return self.flush(path, fh)


def main(mountpoint, root):
    FUSE(Passthrough(root,mountpoint), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
