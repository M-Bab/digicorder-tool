'''
Created on 03.01.2012

@author: babutzka
'''

import os
import sys
import fnmatch

def construct_abs_path(main, localpath):
    constructed_path = None
    if (main):
        if (os.path.isabs(main)):
            constructed_path = main
        else:
            if (localpath):
                constructed_path = os.path.join(os.path.abspath(localpath), main)
            else:
                constructed_path = os.path.join(os.path.curdir, main)
    else:
        if (localpath):
            constructed_path = os.path.abspath(localpath)
        else:
            constructed_path = os.path.curdir
    if (not os.path.isdir(constructed_path)):
        constructed_path = os.path.dirname(constructed_path)
    return(constructed_path)

def construct_maindir_path(filename):
    return(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),filename))

def retrieve_sorted_file_list(directory, pattern):
    matched_files = []
    filelist = os.listdir(directory)
    for single_file in sorted(filelist, key=str.lower):
        if fnmatch.fnmatch(single_file, pattern):
            matched_files.append(os.path.join(directory, single_file))
    return(matched_files)

def combine_files(file_list, target_file_handle, buffer_size=1048576):
    total_file_size = 0
    iteration_index = 0
    for input_file_name in file_list:
        total_file_size += os.path.getsize(input_file_name)
    for input_file_name in file_list:
        input_file = open(input_file_name,'rb')
        while True:
            data = input_file.read(buffer_size)
            if not data:
                break
            target_file_handle.write(data)
            iteration_index += 1
            update_progress(iteration_index*buffer_size/float(total_file_size))
        input_file.close()
    sys.stdout.write('\n')
    target_file_handle.close()
        
def update_progress(progress):
    if(progress > 1.0):
        progress = 1.0
    sys.stdout.write('\r[{0:20}] {1}%'.format("".join(('#',)*int(progress*100/5)), int(progress*100)))
    sys.stdout.flush()

def construct_ffmpeg_arguments(ffmpeg_cmd, inputfilename, outputfilename):
    args = [ffmpeg_cmd, '-err_detect', 'ignore_err', '-y', '-i', inputfilename]
    args += ['-map', '0:u', '-map', '-0:s?', '-c', 'copy', '-ignore_unknown', outputfilename]
    return(args)