#!/usr/bin/env python

TCP_IP = '192.168.3.2'

from technisat_digicorder_comm import digicorder_comm
from optparse import OptionParser
import os
import fnmatch
import tempfile
import sys
import time
from ffmpeg import FFMPEG
from subprocess import Popen
from subprocess import PIPE


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
        args += ['-acodec', 'copy', '-newaudio']
    return(args)

def main():
    parser = OptionParser(version="%prog 0.1", usage="%prog [OPTIONS] [ELEMENT(S)]")
    parser.add_option("-c", "--cd", dest="cd", metavar="DIRECTORY", help="Change DIGICORDER directory before executing 'list', 'get' or 'put'.")
    parser.add_option("-l", "--list", dest="list", action="store_true", default=False, help="List directories/objects on DIGICORDER in current directory")
    parser.add_option("-g", "--get", dest="get", action="store_true", default=False, help="Download ELEMENT(S) FROM DIGICORDER current directory TO CWD or specified local directory.")
    parser.add_option("-p", "--put", dest="put", action="store_true", default=False, help="Upload ELEMENT(S) which is a subdirectory IN CWD or specified local directory TO DIGICORDER current directory.")
    parser.add_option("--localdirectory", dest="local_directory", metavar="DIRECTORY", help="Local destination/source directory for get/put, otherwise CWD is used")
    # parser.add_option("--overwrite", dest="overwrite", action="store_true", default=False, help="Overwrite element if changed")
    parser.add_option("--ts4tomkv", dest="convert_ts4tomkv", action="store_true", default=False, help="Convert HD ELEMENT which is a subdirectory IN CWD or specified local directory to mkv video. Requires ffmpeg with extensions.")
    parser.add_option("--tstompg", dest="convert_tstompg", action="store_true", default=False, help="Convert SD ELEMENT which is a subdirectory IN CWD or specified local directory to mpg video. Requires projectx and mplex.")
    parser.add_option("--noac3", dest="convert_noac3", action="store_true", default=False, help="Drop existing ac3-audio streams when converting to mpg or mkv.")
    
    (options, args) = parser.parse_args()
    elements = args
    
    if (options.cd or options.list or options.get or options.put):
        my_digi_comm = digicorder_comm(TCP_IP)
        my_digi_comm.connect()
        
        my_digi_comm.disconnect()
        
    if (options.convert_ts4tomkv):
        for current_element in elements:
            sourcedir = construct_abs_path(current_element, options.local_directory)
            sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]4')
            if(sourcefiles):
                combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts4")
                print "Combining files in \"" + os.path.abspath(sourcedir) + "\" to temporary file " + combined_temporary_file.name
                combine_files(sourcefiles, combined_temporary_file)
                
                xcoder = FFMPEG()
                metadata = xcoder.get_metadata(combined_temporary_file.name)
                print os.path.basename(os.path.abspath(sourcedir))
                targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mkv").replace(" ","_"))
                ffmpeg_mkv_args = construct_ffmpeg_arguments(combined_temporary_file.name, targetfile, metadata, options.convert_noac3)
                print "Converting files in \"" + os.path.abspath(sourcedir) + "\" to " + targetfile
                (ffmpeg_stdout, ffmpeg_stderr) = xcoder.exec_ffmpeg(ffmpeg_mkv_args)
            
    if (options.convert_tstompg):
        for current_element in elements:
            sourcedir = construct_abs_path(current_element, options.local_directory)
            sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]')
            if(sourcefiles):
                combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts")
                print "Combining files in \"" + os.path.abspath(sourcedir) + "\" to temporary file " + combined_temporary_file.name
                combine_files(sourcefiles, combined_temporary_file)
                
                args = ['projectx', combined_temporary_file.name]
                try:
                    p = Popen(args, shell=False, stderr=PIPE, stdout=PIPE)
                    p.wait()
                except OSError:
                    print "OSError when calling \"projectx\". Ensure \"projectx\" is installed and available in PATH."
                
                m2v_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[mM][2][vV]')
                mp2_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[mM][pP][2]')
                ac3_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[aA][cC][3]')
                log_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[tT][xX][tT]')
                
                if (m2v_files):
                    targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mpg").replace(" ","_"))
                    mplex_command = ['mplex', '-f', '8', '-o', targetfile]
                    if(options.convert_noac3): mplex_command += ac3_files
                    mplex_command += m2v_files
                    mplex_command += mp2_files
                    print "Converting files in \"" + os.path.abspath(sourcedir) + "\" to " + targetfile
                    try:
                        p = Popen(mplex_command, shell=False, stderr=PIPE, stdout=PIPE)
                        p.wait()
                    except OSError:
                        print "OSError when calling mplex. Ensure mplex is installed and available in PATH."
                else:
                    print "No video data found in TS-files in \"" + os.path.abspath(sourcedir) + "\""
                
                for filename in m2v_files:
                    os.remove(filename)   
                for filename in mp2_files:
                    os.remove(filename)
                for filename in ac3_files:
                    os.remove(filename)
                for filename in log_files:
                    os.remove(filename)
                
#TCP_IP = '192.168.3.2'
#
#my_digi_comm = digicorder_comm(TCP_IP)
#file = open('reallybigfilm.dat', 'wb', my_digi_comm.get_buffer_size())
#
#my_digi_comm.connect()
#print 'Root directories: '
##file.write(my_digi_comm.listelementsraw("recordings"))
#my_digi_comm.listelements("recordings")
#print my_digi_comm.downloadelementtofile(13, file)
#
#my_digi_comm.disconnect()
#file.close()


if __name__ == "__main__":
    main()
