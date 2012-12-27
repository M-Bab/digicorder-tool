#!/usr/bin/env python

TCP_IP = '192.168.3.2'

from technisat_digicorder_comm import digicorder_comm
from optparse import OptionParser
from technisat_digicorder_fileops import *
from ffmpeg import FFMPEG
from subprocess import Popen
from subprocess import PIPE
from shlex import split as procsplit
import tempfile
import ConfigParser

def main():
    parser = OptionParser(version="%prog 0.2.3", usage="%prog [OPTIONS] [ELEMENT(S)]")
    parser.add_option("-c", "--cd", dest="cd", metavar="DIRECTORY", default='', help="Change DIGICORDER directory before executing 'list', 'get' or 'put'")
    parser.add_option("-l", "--list", dest="list", action="store_true", default=False, help="List directories/objects on DIGICORDER in current directory")
    parser.add_option("-g", "--get", dest="get", action="store_true", default=False, help="Download ELEMENT(S) FROM DIGICORDER current directory TO CWD or specified local directory. Use \"+\" to download all elements")
    parser.add_option("-p", "--put", dest="put", action="store_true", default=False, help="Upload ELEMENT(S) given as paths/directories TO DIGICORDER current directory. Usage of wildcards is possible")
    parser.add_option("--localdirectory", dest="local_directory", metavar="DIRECTORY", help="Local destination/source directory for get/put, otherwise CWD is used")
    # parser.add_option("--overwrite", dest="overwrite", action="store_true", default=False, help="Overwrite element if changed")
    parser.add_option("--ts4tomkv", dest="convert_ts4tomkv", action="store_true", default=False, help="Convert HD ELEMENT which is a subdirectory IN CWD or specified local directory to mkv video. Requires ffmpeg with extensions")
    parser.add_option("--tstompg", dest="convert_tstompg", action="store_true", default=False, help="Convert SD ELEMENT which is a subdirectory IN CWD or specified local directory to mpg video. Requires projectx and mplex")
    parser.add_option("--noac3", dest="convert_noac3", action="store_true", default=False, help="Drop existing ac3-audio streams when converting to mpg or mkv")
    parser.add_option("--ip", dest="ip", metavar="123.123.123.123", help="IP address of the TechniSat overrides the config file")
    
    (options, args) = parser.parse_args()
    elements = args
    
    config = ConfigParser.RawConfigParser()
    config.read(construct_maindir_path('options.cfg'))
    
    if (options.cd or options.list or options.get or options.put):
        if (options.ip):
            TCP_IP = options.ip
        elif(config.get('main', 'TCP_IP')):
            TCP_IP = config.get('main', 'TCP_IP')
        else:
            print 'No IP-Adress specified in CMD line or config file!'
            exit(-1)
        
        if (config.get('main', 'DEBUG')):
            digi_debug = config.get('main', 'DEBUG')
        else:
            digi_debug = False
        
        my_digi_comm = digicorder_comm(TCP_IP, digi_debug)
        my_digi_comm.connect()
        
        my_digi_comm.cdlist(options.list, options.cd)
        
        if (options.get and options.put):
            print 'Get and Put are optionally exclusive - either use get to download elements from digicorder or put to upload elements to digicorder'
            exit(-1)
        
        if options.get:
            if elements[0] == '+' and len(elements) == 1:
                my_digi_comm.downloadall(construct_abs_path(None , options.local_directory))
            for single_element in elements:
                my_digi_comm.downloadelement(single_element, construct_abs_path(None , options.local_directory))
        if options.put:
            print 'Upload via put is not yet implemented.'
            pass
        
        my_digi_comm.disconnect()
        
    if (options.convert_ts4tomkv):
        for current_element in elements:
            sourcedir = construct_abs_path(current_element, options.local_directory)
            sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]4')
            if(sourcefiles):
                combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts4", delete=False)
                print "Combining files in \"" + os.path.abspath(sourcedir) + "\" to temporary file " + combined_temporary_file.name
                combine_files(sourcefiles, combined_temporary_file)
                
                if (config.get('tools', 'FFMPEG_CMD')):
                    xcoder = FFMPEG(procsplit(config.get('tools', 'FFMPEG_CMD')))
                else:
                    xcoder = FFMPEG()
                metadata = xcoder.get_metadata(combined_temporary_file.name)
#                print os.path.basename(os.path.abspath(sourcedir))
#                print metadata
#                print metadata.video_streams
#                print metadata.audio_streams
                targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mkv").replace(" ","_"))
                ffmpeg_mkv_args = construct_ffmpeg_arguments(combined_temporary_file.name, targetfile, metadata, options.convert_noac3)
                print "Converting files in \"" + os.path.abspath(sourcedir) + "\" to " + targetfile
                (ffmpeg_stdout, ffmpeg_stderr) = xcoder.exec_ffmpeg(ffmpeg_mkv_args)
                
                if(os.path.exists(combined_temporary_file.name)):
                    os.remove(combined_temporary_file.name)
            
    if (options.convert_tstompg):
        for current_element in elements:
            sourcedir = construct_abs_path(current_element, options.local_directory)
            sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]')
            if(sourcefiles):
                combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts", delete=False)
                print "Combining files in \"" + os.path.abspath(sourcedir) + "\" to temporary file " + combined_temporary_file.name
                combine_files(sourcefiles, combined_temporary_file)
                
                if (config.get('tools', 'PROJECTX_CMD')):
                    args = [procsplit(config.get('tools', 'PROJECTX_CMD')), combined_temporary_file.name]                
                else:    
                    args = ['projectx', combined_temporary_file.name]
                try:
                    p = Popen(args, shell=False, stderr=PIPE, stdout=PIPE)
                    print "Demuxing video file with projectx"
#                    print " ".join(args)
                    output, errors = p.communicate()
                    p.wait()
                except OSError:
                    print "OSError when calling \"projectx\". Ensure \"projectx\" is installed and available in PATH."
                    
                if(os.path.exists(combined_temporary_file.name)):
                    os.remove(combined_temporary_file.name)
                
                m2v_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[mM][2][vV]')
                mp2_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[mM][pP][2]')
                ac3_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[aA][cC][3]')
                log_files = retrieve_sorted_file_list(os.path.dirname(combined_temporary_file.name), os.path.splitext(os.path.basename(combined_temporary_file.name))[0]+'*.[tT][xX][tT]')
                
                if (m2v_files):
                    targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mpg").replace(" ","_"))
                    if (config.get('tools', 'MPLEX_CMD')):
                        mplex_command = [procsplit(config.get('tools', 'MPLEX_CMD')), '-f', '8', '-o', targetfile]
                    else:
                        mplex_command = ['mplex', '-f', '8', '-o', targetfile]
                    if(options.convert_noac3): mplex_command += ac3_files
                    mplex_command += m2v_files
                    mplex_command += mp2_files
                    print "Converting files in \"" + os.path.abspath(sourcedir) + "\" to " + targetfile
                    try:
                        p = Popen(mplex_command, shell=False, stderr=PIPE, stdout=PIPE)
                        output, errors = p.communicate()
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
                

if __name__ == "__main__":
    main()
