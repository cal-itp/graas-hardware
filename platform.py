"""
Abstraction layer for platform dependencies, useful e.g. for porting.

To port this to e.g. client-side JS, files could be replaced by localStorage
blobs.
"""
import os
from zipfile import ZipFile

def get_text_file_contents(path):
    return open(path)

def read_file(path):
    #print('read_file()')
    #print(f'- path: {path}')
    with open(path, 'r') as f:
        return f.read()

def write_to_file(path, content):
    with open(path, 'wb') as f:
        f.write(content)
        f.close()

def get_mtime(path):
    return os.path.getmtime(path)

def resource_exists(path):
    return os.path.exists(path)

def ensure_resource_path(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def copy_file(src_path, dst_path):
    os.system(f'cp {src_path} {dst_path}')

def unpack_zip(url, dst_path, files):
    #print(f'storage.unpack_zip()')
    #print(f'- url: {url}')
    #print(f'- dst_path: {dst_path}')
    #print(f'- files: {files}')

    gtfs_zip = ZipFile(url)

    for n in files:
        #print(f'-- zip entry: {n}')
        ze = gtfs_zip.open(n)
        content = ze.read().decode('utf-8')

        #print(f'++ name: {dst_path + n}')
        with open(dst_path + n, 'w') as ff:
            ff.write(content)
            ff.close()
