# -*- coding: utf-8 -*-
from optparse import OptionParser
import os
import sys
import re
import csv
from datetime import datetime, date, time, timedelta
import pysrt
from pydub import AudioSegment
from proscript.proscript import Word, Proscript, Segment
from proscript.utilities import utils

#CONSTANTS
SENTENCE_END_MARKS = ['.', '?', '!', ':', '...']

def checkArgument(argname, isFile=False, isDir=False, createDir=False):
	if not argname:
		return False
	else:
		if isFile and not os.path.isfile(argname):
			return False
		if isDir:
			if not os.path.isdir(argname):
				if createDir:
					print("Creating directory %s"%(argname))
					os.makedirs(argname)
				else:
					return False
	return True

def cutAudioWithPydub(audio_segment, start_time, end_time, outputfile):
	extract = audio_segment[start_time*1000:end_time*1000]
	extract.export(outputfile, format=options.audioformat)

def extract_audio_segments(proscript, audio_segment, output_dir, file_prefix=""):
	'''
	Cuts each segment and outputs as wav+transcript
	'''
	for segment in proscript.segment_list:
		fileId="%s%04d"%(file_prefix, segment.id)

		segmentAudioFile = "%s/%s_audio.wav"%(output_dir, fileId)
		subScriptFile = "%s/%s_sub.txt"%(output_dir, fileId)

		cutAudioWithPydub(audio_segment, segment.start_time, segment.end_time, segmentAudioFile)

		#write subtitle text to a separate file
		with open(subScriptFile, 'w') as f:
			f.write(segment.transcript)

def subriptime_to_seconds(srTime):
	'''
	Convert SubRipTime object to seconds
	'''
	t = datetime.combine(date.min, srTime.to_time()) - datetime.min
	return t.total_seconds()

def normalize_transcript(transcript):
	'''
	All text normalization here
	'''
	transcript = re.sub('\n', ' ', transcript)
	return transcript

def to_proscript(srt_data):
	proscript = Proscript()

	segment_count = 0
	first_utterance = True

	for index, srt_entry in enumerate(srt_data):
		start_time = subriptime_to_seconds(srt_entry.start)
		end_time = subriptime_to_seconds(srt_entry.end)

		transcript = srt_entry.text_without_tags.strip()

		if transcript and not transcript.isspace():
			if first_utterance:
				curr_seg = Segment()
				curr_seg.start_time = start_time
				curr_seg.end_time = end_time
				curr_seg.transcript += transcript
				first_utterance = False
			elif curr_seg.transcript[-1] in SENTENCE_END_MARKS:
				if curr_seg.transcript and not curr_seg.transcript.isspace():
					segment_count += 1
					curr_seg.id = segment_count
					curr_seg.transcript = normalize_transcript(curr_seg.transcript)
					proscript.add_segment(curr_seg)
					# print("----====----")
					# curr_seg.to_string()
					# print("----====----")
				curr_seg = Segment()
				curr_seg.start_time = start_time
				curr_seg.end_time = end_time
				curr_seg.transcript += transcript
				#print("curr_seg:\n%s"%curr_seg.transcript)
			else:
				curr_seg.end_time = subriptime_to_seconds(srt_entry.end)
				curr_seg.transcript += ' ' + transcript
				#print("curr_seg:\n%s"%curr_seg.transcript)

		if index == len(srt_data) - 1:
			if curr_seg.transcript and not curr_seg.transcript.isspace():
				segment_count += 1
				curr_seg.id = segment_count
				curr_seg.transcript = normalize_transcript(transcript)
				proscript.add_segment(curr_seg)
				# curr_seg.to_string()
				# print("----====----")
	return proscript

def main(options):
	checkArgument(options.audiofile, isFile=True)
	checkArgument(options.subfile, isFile=True)
	checkArgument(options.outdir, isDir=True, createDir=True)

	print("Audio: %s\nSubtitles: %s\nLanguage: %s\nTranscription: %s"%(options.audiofile, options.subfile, options.movielang, options.transcribe_dub))
	print("Reading subtitles...", end="")
	srtData = pysrt.open(options.subfile)
	print("done")

	audio = AudioSegment.from_file(options.audiofile, format=options.audioformat)

	movie_proscript = to_proscript(srtData)

	proscript_file = "%s/%s_proscript.csv"%(options.outdir, options.movielang)
	movie_proscript.segments_to_csv(proscript_file, ['id', 'start_time', 'end_time', 'transcript'], delimiter='|')
	print("Segments info written to %s"%proscript_file)

	print("Segmenting subtitle entries...", end="")
	extract_audio_segments(movie_proscript, audio, options.outdir, file_prefix=options.movielang)
	print("done.")
	

if __name__ == "__main__":
    usage = "usage: %prog [-s infile] [option]"
    parser = OptionParser(usage=usage)
    parser.add_option("-a", "--audiofile", dest="audiofile", default=None, help="movie audio file to be segmented", type="string")
    parser.add_option("-s", "--sub", dest="subfile", default=None, help="subtitle file (srt)", type="string")
    parser.add_option("-o", "--output-dir", dest="outdir", default=None, help="Directory to output segments and sentences", type="string")
    parser.add_option("-l", "--lang", dest="movielang", default="", help="Language of the movie audio (Three letter ISO 639-2/T code)", type="string")
    parser.add_option("-t", "--transcribe", dest="transcribe_dub", action="store_true", default=False, help="send dubbed audio segments to wit.ai")
    parser.add_option("-f", "--audioformat", dest="audioformat", default="wav", help="Audio format (wav, mp3 etc.)", type="string")

    (options, args) = parser.parse_args()

    main(options)