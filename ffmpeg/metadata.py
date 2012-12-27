'''
This code is a modified version of the "pyxcoder" by james.townson 
who I want to thank for his MIT-license-code in this Aknowledgement.
More information on google code: http://code.google.com/p/pyxcoder/

@author: james.townson, babutzka
'''

import re
import collections

video_stream = collections.namedtuple('video_stream','stream_id, codec, pixel_format, dimension, frame_rate')
audio_stream = collections.namedtuple('audio_stream','stream_id, codec, sample_rate, channels, sampling_precision, bitrate')

class Metadata:
	format = None
	duration = None # the duration of a movie or audio file in seconds.
	start = None
	bitrate = None
	
	video_streams = []
	audio_streams = []

	def __repr__(self):
		return str(self.__dict__)


class FFmpegMetadataParser:
	# Input #0, flv, from 'foo.flv':
	INPUT_PATTERN = re.compile(r'^\s*Input #\d+,.*$')
	# Duration: 00:51:31.9, start: 0.000000, bitrate: 348 kb/s
	DURATION_PATTERN = re.compile(r'^\s*Duration: (.*?), start: (.*?), bitrate: (.*)$')
	# Stream #0.0: Audio: mp3, 44100 Hz, stereo
	AUDIO_STREAM_PATTERN = re.compile(r'^\s*Stream\s+#(\d+[.:]\d+).*:\s+Audio:(.*)$')
	# Stream #0.1: Video: vp6f, yuv420p, 368x288,  0.17 fps(r)
	VIDEO_STREAM_PATTERN = re.compile(r'^\s*Stream\s+#(\d+[.:]\d+).*:\s+Video:(.*)$')

	
	def __init__(self, filelike):
		self.filelike = filelike
		self.raw_metadata_lines = []
		self.unrecognized_lines = []
		self.metadata = None
		
	def parse_input(self, line):
		#print 'parse_input: %s' % line
		metadata = Metadata()
		metadata.format = line.split(',')[1].strip()
		self.metadata = metadata
		
	def parse_duration(self, line):
		#print 'parse_duration: %s' % line
		metadata = self.metadata
		duration, start, bitrate = self.DURATION_PATTERN.match(line).groups()
		metadata.duration = duration
		metadata.start = start
		metadata.bitrate = bitrate
	
	def parse_audio_stream(self, line):
		#print 'parse_audio_stream: %s' % line
		metadata = self.metadata
		try:
			stream_id = self.AUDIO_STREAM_PATTERN.match(line).group(1).strip()
			codec, sample_rate, channels, sampling_precision, bitrate = [each.strip() for each in self.AUDIO_STREAM_PATTERN.match(line).group(2).split(',')][:5]
			single_audio_stream = audio_stream(stream_id, codec, sample_rate, channels, sampling_precision, bitrate)
			metadata.audio_streams.append(single_audio_stream)
		except ValueError:
			pass
		
	def parse_video_stream(self, line):
		#print 'parse_video_stream: %s' % line
		metadata = self.metadata
		try:
			stream_id = self.VIDEO_STREAM_PATTERN.match(line).group(1).strip()
			codec, pixel_format, dimension, frame_rate = [each.strip() for each in self.VIDEO_STREAM_PATTERN.match(line).group(2).split(',')][:4]
			single_video_stream = video_stream(stream_id, codec, pixel_format, dimension, frame_rate)
			metadata.video_streams.append(single_video_stream)
		except ValueError:
			pass
		
	def parse_line(self, line):
		match_any = True
		if self.INPUT_PATTERN.match(line):
			self.parse_input(line)
		elif self.DURATION_PATTERN.match(line):
			self.parse_duration(line)
		elif self.AUDIO_STREAM_PATTERN.match(line):
			self.parse_audio_stream(line)
		elif self.VIDEO_STREAM_PATTERN.match(line):
			self.parse_video_stream(line)
		else:
			self.unrecognized_lines.append(line)
			match_any = False
		if match_any:
			self.raw_metadata_lines.append(line)
	
	def get_metadata(self):
		re.sub(r'(\r\n|\r|\n)', '\n', self.filelike)
		for line in self.filelike.split('\n'):
			self.parse_line(line.strip())
		return self.metadata

def parse_ffmpeg_metadata(filelike):
	return FFmpegMetadataParser(filelike).get_metadata()
