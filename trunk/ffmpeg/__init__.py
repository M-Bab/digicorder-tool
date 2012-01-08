'''
This code is a modified version of the "pyxcoder" by james.townson 
who I want to thank for his MIT-license-code in this Aknowledgement.
More information on google code: http://code.google.com/p/pyxcoder/

@author: james.townson, babutzka
'''

from subprocess import Popen
from subprocess import PIPE
from ffmpeg.options import Options
from ffmpeg.options import build_ffmpeg_args
from ffmpeg.metadata import parse_ffmpeg_metadata
from compiler.pycodegen import EXCEPT


BUF_SIZE = 4096


class FFMPEG:
	def __init__(self, ffmpeg='ffmpeg'):
		self.ffmpeg = ffmpeg
		
	def get_metadata(self, input_filename):
		args = build_ffmpeg_args(input_filename)
		(child_stdout, child_stderr) = self.exec_ffmpeg(args)
		return parse_ffmpeg_metadata(child_stderr)
		
	def transcode(self, input_filename, output_filename, options=None):
		args = build_ffmpeg_args(input_filename, output_filename)
		self.exec_ffmpeg(args)
	
	def get_frame_as_jpeg(self, input_filename, output_filename, frame_number=1):
		args = ['-i', input_filename, '-ss', '00:00:00', '-vframes', '1', '-f', 'mjpeg', output_filename]
		print self.exec_ffmpeg(args)[1].read()
	
	def exec_ffmpeg(self, args):
		args = [self.ffmpeg] + args
		#print ' '.join(args)
		try:
			p = Popen(args, shell=False, bufsize=BUF_SIZE, stderr=PIPE, stdout=PIPE, close_fds=True)
			p.wait()
		except OSError:
			print "OSError when calling \"ffmpeg\". Ensure \"ffmpeg\" is installed and available in PATH."
		return (p.stdout, p.stderr)
