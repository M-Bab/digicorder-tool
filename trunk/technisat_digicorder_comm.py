'''
class Technisat Digicorder communication protocoll
'''

import socket
import collections
import sys
import datetime
import time
import os

filmelement = collections.namedtuple('filmelement','name, number, type, seenflag, size, date')
directory = collections.namedtuple('directory','name, unknownint')
filetype = collections.namedtuple('filetype','id, extension')

debugging_mode = 0

class digicorder_comm:
    def __init__(self, a_tcp_adress, a_tcp_port = 2376, a_buffer_size = 8192, a_timeout = 10):
        self.tcp_adress = a_tcp_adress
        self.tcp_port = a_tcp_port
        self.buffer_size = a_buffer_size
        self.timeout = a_timeout
    def get_buffer_size(self):
        return(self.buffer_size)
    def get_tcp_port(self):
        return(self.tcp_port)
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        try:
            self.socket.connect((self.tcp_adress, self.tcp_port))
        except:
            print "Failed to connect to Technisat. Ensure it is switched on, not busy and available under the given ip address: " + self.tcp_adress
            sys.exit(-1)
        self.send_ack(1)
        self.send('\x02')
        while ord(self.receive(1)) == 1:
            pass
        version = ord(self.response)
        lang_count = ord(self.receive(1))
        lang = self.receive(lang_count)
        modelname_count = ord(self.receive(1))
        model = self.receive(modelname_count)
        print 'Connected to model ' + str(model) + ' (language=' + str(lang) + ', version=' + str(version) + ')'
        self.send_ack(0)
    def debugprint(self, pretext, content):
        print pretext
        index = 0
        for index in range(0, len(content), 15):
            partstring = content[index:index+15]
            hexstring = ' '.join(["%02X"%ord(singlebyte) for singlebyte in partstring])
            print hexstring + ' | ' + partstring
    def disconnect(self):
        self.socket.close()
    def send(self, command):
        if debugging_mode == 1:
            self.debugprint('Sending:', command)
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
            print "Socket timeout (" + str(self.socket.gettimeout()) + ") while receiving after " + str(received_bytes) + " Bytes!"
        if debugging_mode == 1:
            self.debugprint('Received:', self.response)
        return(self.response)
    def send_and_receive(self, command, nbytes=-1):
        if nbytes == -1:
            self.socket.settimeout(0.5)
            self.response = ''
            if debugging_mode == 1:
                self.debugprint('Sending:', command)
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
            if debugging_mode == 1:
                self.debugprint('Sending:', self.response)
            self.socket.settimeout(self.timeout)
        else:
            self.send(command)
            self.receive(nbytes)
        return(self.response)
    def send_and_receive_to_file(self, command, filehandle):
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
    def send_ack(self, nbytes = -1):
        self.reack = ''
        if nbytes == -1:
            retemp = self.send_and_receive('\x01')
            if retemp <> '\x01':
                self.reack += retemp
        else:
            self.reack = self.send_and_receive('\x01', nbytes)
        return(self.reack)
    def listelementsraw(self, directoryname):
        self.elementsstring = ''
        self.send_and_receive('\x03\x00\x01')
        retemp = self.send_and_receive(directoryname)
        if len(retemp) > 4:
            self.elementsstring = retemp
        retemp = self.send_ack()
        if len(retemp) > 4:
            self.elementsstring = retemp
        return(self.elementsstring)
    def cdlist(self, list, directoryname):
        self.listrootdirectories()
        if directoryname != '':
            self.listelements(directoryname)
        if list:
            if directoryname == '':
                self.printrootdirectories()
            else:
                self.printlistelements(directoryname)
    def downloadelement(self, filmnumber, targetdirectory):
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
                print 'Download completed successfully'
                break
            self.receive(4)
            filepart_size = ord(self.response[0])*256*256*256+ord(self.response[1])*256*256+ord(self.response[2])*256+ord(self.response[3])
            divider_check = self.receive(3)
            
            if divider_check != '***':
                print 'Consistency check failed. Download aborted.'
                break
            
            download_buffer = self.receive(filepart_size)
            filelist[actual_filetype].write(download_buffer)
                    
        for single_file in filelist:
            single_file.close()
        
    def downloadelementtosinglefile(self, filmnumber, filehandle):
        self.downloaddescription = self.send_and_receive('\x05\x00' + chr(int(filmnumber)) + '\x00\x00\x00\x00\x00\x00\x00\x00')
        print 'Starting download: ' + self.downloaddescription
        self.send_and_receive_to_file('\x01', filehandle)
        print 'Download completed!'
        self.send_ack()
        return(self.downloaddescription)
    def listrootdirectories(self):
        self.directorieslist = []

        self.send('\x03\x00\x00')
        self.receive(1)
        self.send_ack(1)
        
        if ord(self.receive(1)) == 0:
            self.receive(1)
        self.numberofdirectories = ord(self.response)

        name = ''; unknownint = 0;
        for i in range(0, self.numberofdirectories):
            self.receive(2)
            unknownint = 256*ord(self.response[1])+ord(self.response[0])
            
            namelength = ord(self.receive(1))
            
            name = (self.receive(namelength)).decode("iso-8859-15").encode(sys.getfilesystemencoding())

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
        
        self.send_and_receive('\x03\x00\x01', 1)
        self.send_and_receive(directoryname, 1)
        self.send_ack(1)
        
        if ord(self.receive(1)) == 1: 
            if ord(self.receive(1)) == 0:
                pass
            else:
                self.debugprint("Unexpected listelements reply", self.response)
        else:
                if ord(self.receive(1)) == 0:
                    pass
        self.numberoffilms = ord(self.receive(1))

##       typeset = 0; numberset = 0; namelengthset = 0; seenset = 0; nameset = 0; sizeset = 0; dateset = 0
        name = ''; number = 0; type = ''; seenflag = 0; size = 0; date = 0; namelength = 0
        for i in range(0,self.numberoffilms):
            self.receive(1)
            if ord(self.response) == 4:
                type = 'MPEG SD'
            elif ord(self.response) == 7:
                type = 'MPEG HD'
            else:
                type = 'Unknown'
                print "Unknown file type " + str(ord(self.response)) + " at Filmelement " + str(i) 
                #sys.exit(-1)
            
            self.receive(2)
            number = 256*ord(self.response[0])+ord(self.response[1])
            
            namelength = ord(self.receive(1))-1
            
            self.receive(1)
            if ord(self.response) == 5:
                seenflag = 0
            elif ord(self.response) == 11:
                seenflag = 1
            else:
                seenflag = 0
                print "Unknown seen flag " + str(ord(self.response)) + " at film element " + str(i)
                #sys.exit(-1)
            
            name = (self.receive(namelength)).decode("iso-8859-15").encode(sys.getfilesystemencoding())
            
            self.receive(3)
            if (ord(self.response[0]) + ord(self.response[1]) + ord(self.response[2]) ) > 0:
                print "Structure failure at film number " + str(i) + " only zeros expected!"
                sys.exit(-1)
            
            self.receive(3)
            size = (ord(self.response[0])*256*256+ord(self.response[1])*256+ord(self.response[2]))/16.
            
            self.receive(2)
            if (ord(self.response[0]) + ord(self.response[1]) ) > 0:
                print "Structure failure at film number " + str(i) + " only zeros expected!"
                sys.exit(-1)
            
            # Timestamp corresponds to 1.1.2000 00:00:00 = 946681200 s since 1970
            self.receive(4)
            timestamp = ord(self.response[0])*256*256*256+ord(self.response[1])*256*256
            timestamp += ord(self.response[2])*256+ord(self.response[3])
            reference_datetime = datetime.datetime(2000, 1, 1, 0, 0, 0)
            
            date = datetime.datetime.fromtimestamp(int(timestamp)+int(reference_datetime.strftime("%s"))+time.timezone)

            film = filmelement(name, number, type, seenflag, size, date)
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
        