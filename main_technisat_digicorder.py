#!/usr/bin/env python

from technisat_digicorder_comm import digicorder_comm
from optparse import OptionParser
from technisat_digicorder_fileops import *
#from shlex import split as procsplit
import tempfile
import configparser
import subprocess

VERSION="0.3.0"

def main():
    parser = OptionParser(version="%prog {}".format(VERSION), usage="%prog [OPTIONS] [ELEMENT(S)]")
    parser.add_option("-c", "--cd", dest="cd", metavar="DIRECTORY", default='', help="Change DIGICORDER directory before executing 'list', 'get' or 'put'")
    parser.add_option("-l", "--list", dest="list", action="store_true", default=False, help="List directories/objects on DIGICORDER in current directory")
    parser.add_option("-g", "--get", dest="get", action="store_true", default=False, help="Download ELEMENT(S) FROM DIGICORDER current directory TO CWD or specified local directory. Use \"+\" to download all elements")
    parser.add_option("-p", "--put", dest="put", action="store_true", default=False, help="Upload ELEMENT(S) given as paths/directories TO DIGICORDER current directory. Usage of wildcards is possible")
    parser.add_option("--localdirectory", dest="local_directory", metavar="DIRECTORY", help="Local destination/source directory for get/put, otherwise CWD is used")
    parser.add_option("--convert", dest="convert", action="store_true", default=False, help="Convert SD/HD ELEMENT which is a subdirectory IN CWD or specified local directory to mpg/mkv video. Requires ffmpeg with extensions")
    parser.add_option("--ip", dest="ip", metavar="123.123.123.123", help="IP address of the TechniSat overrides the config file")
    
    (options, args) = parser.parse_args()
    elements = args
    
    config = configparser.RawConfigParser()
    config.read(construct_maindir_path('options.cfg'))
    
    if (options.cd or options.list or options.get or options.put):
        if (options.ip):
            TCP_IP = options.ip
        elif(config.get('main', 'TCP_IP', fallback=False)):
            TCP_IP = config.get('main', 'TCP_IP')
        else:
            print('No IP-Adress specified in CMD line or config file!')
            exit(-1)
        
        digi_debug = config.get('main', 'DEBUG', fallback=False)
        
        my_digi_comm = digicorder_comm(TCP_IP, digi_debug)
        my_digi_comm.connect()
        
        my_digi_comm.cdlist(options.list, options.cd)
        
        if (options.get and options.put):
            print('Get and Put are optionally exclusive - either use get to download elements from digicorder or put to upload elements to digicorder')
            exit(-1)
        
        if options.get:
            if elements[0] == '+' and len(elements) == 1:
                my_digi_comm.downloadall(construct_abs_path(None , options.local_directory))
            for single_element in elements:
                my_digi_comm.downloadelement(single_element, construct_abs_path(None , options.local_directory))
        if options.put:
            print('Upload via put is not yet implemented.')
            pass
        
        my_digi_comm.disconnect()
        
    if (options.convert):
        ffmpeg_cmd = config.get('tools', 'FFMPEG_CMD', fallback="ffmpeg")
    
#         if (config.get('tools', 'FFMPEG_CMD', fallback=False)):
#             ffmpeg_cmd = procsplit(config.get('tools', 'FFMPEG_CMD'))
        
        for current_element in elements:
            sourcedir = construct_abs_path(current_element, options.local_directory)
            
            # Check for HD video files in element
            sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]4')
            
            if(sourcefiles):
                combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts4", delete=False)
                targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mkv").replace(" ","_"))
            else:
                # No HD video files, check for SD video files
                sourcefiles = retrieve_sorted_file_list(sourcedir, '*.[tT][sS]')
                if(sourcefiles):
                    combined_temporary_file = tempfile.NamedTemporaryFile(suffix=".ts", delete=False)
                    targetfile = os.path.join(sourcedir, (os.path.basename(os.path.abspath(sourcedir)) + ".mpg").replace(" ","_"))
            
            if(sourcefiles):
                sourcefile_name = combined_temporary_file.name
                # Skip combining files if it is a singular file
                if(len(sourcefiles) == 1):
                    sourcefile_name = sourcefiles[0]
                else:
                    print("Combining files in \"" + os.path.abspath(sourcedir) + "\" to temporary file " + combined_temporary_file.name)
                    combine_files(sourcefiles, combined_temporary_file)
                
                ffmpeg_run_args = construct_ffmpeg_arguments(ffmpeg_cmd, sourcefile_name, targetfile)
                print("Converting files in \"" + os.path.abspath(sourcedir) + "\" to " + targetfile)
                try:
                    subprocess.run(ffmpeg_run_args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, check=True)
                except subprocess.CalledProcessError as e:
                    print("ffmpeg conversion not successful!")
                
                if(os.path.exists(combined_temporary_file.name)):
                    os.remove(combined_temporary_file.name)
            
if __name__ == "__main__":
    main()
