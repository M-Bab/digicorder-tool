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
    for single_file in sorted(filelist, cmp=lambda x,y: cmp(x.lower(), y.lower())):
        if fnmatch.fnmatch(single_file, pattern):
            matched_files.append(os.path.join(directory, single_file))
    return(matched_files)

def combine_files(file_list, target_file_handle, buffer_size=1048576):
    total_file_size = 0
    iteration_index = 0
    for input_file_name in file_list:
        total_file_size += os.path.getsize(input_file_name)
    for input_file_name in file_list:
        input_file = file(input_file_name,'rb')
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
    sys.stdout.write('\r[{0:20}] {1}%'.format('#'*(int(progress*100)/5), int(progress*100)))
    sys.stdout.flush()

def construct_ffmpeg_arguments(inputfilename, outputfilename, metadata, noac3=False):
    args = ['-y', '-i', inputfilename]
    args += ['-map']
    args += [metadata.video_streams[0].stream_id]
    audiostreams_count = 0
    for audiostream in metadata.audio_streams:
        if (not (noac3 and audiostream.codec == 'ac3')):
            args += ['-map']
            args += [audiostream.stream_id]
            audiostreams_count += 1
    args += ['-f', 'matroska', '-vcodec', 'copy', '-acodec', 'copy', outputfilename]
    for index_number in range(1, audiostreams_count):
#        args += ['-acodec', 'copy', '-newaudio'] # Removed newaudio - not required in recent ffmpeg versions
        args += ['-acodec', 'copy']
    return(args)