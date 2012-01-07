# class Technisat Digicorder communication protocoll

import socket
import collections
import sys
import datetime
import time
import os

filmelement = collections.namedtuple('filmelement','name, number, type, seenflag, size, date')
directory = collections.namedtuple('directory','name, unknownint')
filetype = collections.namedtuple('filetype','id, extension')

class digicorder_comm:
    def __init__(self, a_tcp_adress, a_tcp_port = 2376, a_buffer_size = 8192):
        self.tcp_adress = a_tcp_adress
        self.tcp_port = a_tcp_port
        self.buffer_size = a_buffer_size
    def get_buffer_size(self):
        return(self.buffer_size)
    def get_tcp_port(self):
        return(self.tcp_port)
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        self.socket.connect((self.tcp_adress, self.tcp_port))
        self.socket.settimeout(0.5)
        self.send_ack()
        rehello = self.send_and_receive('\x02')
        if rehello:
            print 'Technisat Digicorder responded with: ' + rehello
        self.send_ack()
    def disconnect(self):
        self.socket.close()
    def send(self, command):
        self.socket.send(command)
    def receive(self, nbytes):
        self.response = ''
        received_bytes = 0
        try:
            while (received_bytes < nbytes):
                if nbytes-received_bytes > self.buffer_size:
                    maxbuffer = self.buffer_size
                else:
                    maxbuffer = nbytes-received_bytes
                self.response += self.socket.recv(maxbuffer)
                received_bytes = len(self.response)
        except socket.timeout:
            print "Socket timeout (" + str(self.socket.timeout) + ") while receiving after " + received_bytes + " Bytes!"
        return(self.response)
    def send_and_receive(self, command):
        self.response = ''
        self.socket.send(command)
        while True:
            self.data = ""
            try:
                self.data = self.socket.recv(self.buffer_size)
                self.response += self.data
            except socket.timeout:
                if self.data:
                    self.response += self.data
                break
        return(self.response)
    def send_and_receive_to_file(self, command, filehandle):
        self.socket.settimeout(10)
        self.socket.send(command)
        while True:
            self.data = ""
            try:
                self.data = self.socket.recv(self.buffer_size)
                filehandle.write(self.data)
            except socket.timeout:
                if self.data:
                    filehandle.write(self.data)
                break
        self.socket.settimeout(0.5)
    def send_ack(self, ntimes = 1):
        self.reack = ''
        for self.i in range(0, ntimes):
            retemp = self.send_and_receive('\x01')
            if retemp <> '\x01':
##                print 'Warning, Technisat did not react on ack-package!'
##                sys.exit(-1)
##            print self.reack
                self.reack += retemp
        return(self.reack)
    def create_film_files_from_raw(self):
        pass
    def listrootdirectoriesraw(self):
        self.rootdirectoriesrawstring = self.send_and_receive('\x03\x00\x00')
        self.send_ack()
        print self.rootdirectoriesrawstring
        return(self.rootdirectoriesrawstring)
    def listelementsraw(self, directoryname):
        self.elementsstring = ''
        self.send_and_receive('\x03\x00\x01')
        retemp = self.send_and_receive(directoryname)
        if len(retemp) > 4:
            self.elementsstring = retemp
        retemp = self.send_ack()
        if len(retemp) > 4:
            self.elementsstring = retemp
        print self.elementsstring
        return(self.elementsstring)
    def cdlist(self, list, directoryname):
        self.listrootdirectoriesraw()
        self.listrootdirectories()
        if directoryname != '':
            self.listelementsraw(directoryname)
            self.listelements(directoryname)
        if list:
            if directoryname == '':
                self.printrootdirectories()
            else:

                self.printlistelements(directoryname)
    def downloadelement(self, filmnumber, targetdirectory):
        self.socket.settimeout(10)
        self.filetypeslist = []
        
        self.send('\x05\x00' + chr(int(filmnumber)) + '\x00\x00\x00\x00\x00\x00\x00\x00')
        # ignore first 8 bytes
        self.receive(8)
        # number of filetype
        self.receive(2)
        self.numberoffiles = ord(self.response[0])*256+ord(self.response[1])
        for i in range(0, self.numberoffiles):
            filetype_id = ord(self.receive(1))
            namelength = ord(self.receive(1))
            name = self.receive(namelength)
            new_filetype = filetype(filetype_id, name)
            self.filetypeslist.append(new_filetype)
        
        #Prepare files:
        filmname = self.get_elementname_from_number(filmnumber)
        dest_directory = os.path.join(targetdirectory, filmname)
        if not os.path.exists(dest_directory):
            os.mkdir(dest_directory)
        
        filelist = []
        for i in range(0, self.numberoffiles):
            filelist.append('')
        for single_filetype in self.filetypeslist:
            filelist[single_filetype.id] = file(os.path.join(dest_directory, filmname + '.' + single_filetype.extension),'wb')
        
        # Download!
        self.send('\x01')
        
        while True:
            actual_filetype = ord(self.receive(1))
            if actual_filetype == 255:
                break
            self.receive(4)
            filepart_size = ord(self.response[0])*256*256*256+ord(self.response[1])*256*256+ord(self.response[2])*256+ord(self.response[3])
            divider_check = self.receive(3)
            
            print divider_check
            print actual_filetype
            print filepart_size
            
            download_buffer = self.receive(filepart_size)
            filelist[actual_filetype].write(download_buffer)
                    
        for single_file in filelist:
            single_file.close()
        
        print 'Download completed successfully'
        self.socket.settimeout(0.5)
        
    def downloadelementtosinglefile(self, filmnumber, filehandle):
        self.downloaddescription = self.send_and_receive('\x05\x00' + chr(int(filmnumber)) + '\x00\x00\x00\x00\x00\x00\x00\x00')
        print 'Starting download: ' + self.downloaddescription
        self.send_and_receive_to_file('\x01', filehandle)
        print 'Download completed!'
        self.send_ack()
        return(self.downloaddescription)
    def listrootdirectories(self):
        self.directorieslist = []
        start = 0
        if ord(self.rootdirectoriesrawstring[start]) == 1: 
            start += 1
        if ord(self.rootdirectoriesrawstring[start]) == 0:
            start += 1
        self.numberofdirectories = ord(self.rootdirectoriesrawstring[start])
        start += 1
        
        name = ''; unknownint = 0;
        for i in range(0, self.numberofdirectories):
            pos = 0
        
            unknownint = 256*ord(self.rootdirectoriesrawstring[start+pos])+ord(self.rootdirectoriesrawstring[start+pos+1])
            pos += 2
            
            namelength = ord(self.rootdirectoriesrawstring[start+pos])
            pos += 1
            
            name = self.rootdirectoriesrawstring[start+pos:start+pos+namelength]
            pos += namelength
            
            start += pos
            singledirectory = directory(name, unknownint)
            self.directorieslist.append(singledirectory)
            name = ''; unknownint = 0;
        return(self.directorieslist)
        
    def get_elementname_from_number(self, number):
        for film in self.filmlist:
            if int(film.number) == int(number):
                return(film.name)
        
    def listelements(self, directoryname):
        self.filmlist = []
        start = 0
        #print self.elementsstring
        if ord(self.elementsstring[start]) == 1: 
            start += 1
        if ord(self.elementsstring[start]) == 0:
            start += 1
        self.numberoffilms = ord(self.elementsstring[start])
        start += 1

##       typeset = 0; numberset = 0; namelengthset = 0; seenset = 0; nameset = 0; sizeset = 0; dateset = 0
        name = ''; number = 0; type = ''; seenflag = 0; size = 0; date = 0; namelength = 0
        for i in range(0,self.numberoffilms):
            pos = 0
            if ord(self.elementsstring[start+pos]) == 4:
                type = 'MPEG SD'
            elif ord(self.elementsstring[start+pos]) == 7:
                type = 'MPEG HD'
            else:
                print "Unknown file type " + self.elementsstring[start+pos] + " at position " + str(start+pos)
                sys.exit(-1)
            pos += 1
            
            number = 256*ord(self.elementsstring[start+pos])+ord(self.elementsstring[start+pos+1])
            pos += 2
            
            namelength = ord(self.elementsstring[start+pos])
            pos += 1
            
            if ord(self.elementsstring[start+pos]) == 5:
                seenflag = 0
            elif ord(self.elementsstring[start+pos]) == 11:
                seenflag = 1
            else:
                print "Unknown seen flag " + self.elementsstring[start+pos] + " at position " + str(start+pos)
                sys.exit(-1)
            pos += 1
            
            name = self.elementsstring[start+pos:start+pos+namelength-1]
            pos += namelength-1
            
            if (ord(self.elementsstring[start+pos]) + ord(self.elementsstring[start+pos+1]) + ord(self.elementsstring[start+pos+1]) ) > 0:
                print "Structure failure at position " + str(start+pos) + " only zeros expected!"
                sys.exit(-1)
            pos += 3
            
            size = (ord(self.elementsstring[start+pos])*256*256+ord(self.elementsstring[start+pos+1])*256+ord(self.elementsstring[start+pos+2]))/16.
            pos += 3
            
            if (ord(self.elementsstring[start+pos]) + ord(self.elementsstring[start+pos+1]) ) > 0:
                print "Structure failure at position " + str(start+pos) + " only zeros expected!"
                sys.exit(-1)
            pos += 2
            
            # Timestamp corresponds to 1.1.2000 00:00:00 = 946681200 s since 1970
            timestamp = ord(self.elementsstring[start+pos])*256*256*256+ord(self.elementsstring[start+pos+1])*256*256
            timestamp += ord(self.elementsstring[start+pos+2])*256+ord(self.elementsstring[start+pos+3])
            reference_datetime = datetime.datetime(2000, 1, 1, 0, 0, 0)
            
            date = datetime.datetime.fromtimestamp(int(timestamp)+int(reference_datetime.strftime("%s"))+time.timezone)
            pos += 4

            start += pos
            film = filmelement(name, number, type, seenflag, size, date)
            ##print film
            self.filmlist.append(film)
            name = ''; number = 0; type = ''; seenflag = 0; size = 0; date = 0; namelength = 0
        return(self.filmlist)
    def printlistelements(self, directoryname):
        print 'Elements in ' + directoryname
        print ''
        print '{0:40} | {1:3} | {2:7} | {3:9} | {4:20}'.format('Name', 'No.', 'Type', 'Size (MB)', 'Date/Time')
        for film in self.filmlist:
            print '{0:40} | {1:3} | {2:7} | {3:9.1f} | {4:20}'.format(film.name, film.number, film.type, film.size, film.date.isoformat(' '))
    def printrootdirectories(self):
        print 'Root directories:'
        print ''
        print '{0:20} | {1:8}'.format('Name', 'Unknown')
        for singledirectory in self.directorieslist:
            print '{0:20} | {1:8}'.format(singledirectory.name, singledirectory.unknownint)
        