# class Technisat Digicorder communication protocoll

import socket
import collections
import sys

filmelement = collections.namedtuple('filmelement','name, number, type, seenflag, size, date')
directory = collections.namedtuple('directory','name')

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
        return(self.rootdirectoriesrawstring)
    def listelementsraw(self, directoryname):
        self.send_and_receive('\x03\x00\x01')
        retemp = self.send_and_receive(directoryname)
        if len(retemp) > 4:
            self.elementsstring = retemp
        retemp = self.send_ack()
        if len(retemp) > 4:
            self.elementsstring = retemp
        return(self.elementsstring)
    def listrootdirectories(self, rootdirectoriesrawstring = ''):
        self.rootdirectoriesrawstring = rootdirectoriesrawstring
        if self.rootdirectoriesrawstring == '':
            self.rootdirectoriesrawstring = self.listrootdirectoriesraw()
    def downloadelementtofile(self, filmnumber, filehandle):
        self.downloaddescription = self.send_and_receive('\x05\x00' + chr(filmnumber) + '\x00\x00\x00\x00\x00\x00\x00\x00')
        print self.downloaddescription
        self.send_and_receive_to_file('\x01', filehandle)
        print 'Download completed!'
        self.send_ack()
        return(self.downloaddescription)
    def listelements(self, directoryname):
        self.listelementsraw(directoryname)
        self.filmlist = []
        start = 0
        print self.elementsstring
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
            
            date = ord(self.elementsstring[start+pos])*256*256*256+ord(self.elementsstring[start+pos+1])*256*256
            date += ord(self.elementsstring[start+pos+2])*256+ord(self.elementsstring[start+pos+3])
            pos += 4
            
            start += pos
            film = filmelement(name, number, type, seenflag, size, date)
            print film
            self.filmlist.append(film)
            name = ''; number = 0; type = ''; seenflag = 0; size = 0; date = 0; namelength = 0
        return(self.filmlist)