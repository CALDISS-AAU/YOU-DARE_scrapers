import os
os.environ["PATH"] = "/work/YOU-DARE/ffmpeg-7.0.2-amd64-static:" + os.environ["PATH"]

from pydub import AudioSegment
import glob
import os

video_dir = '/work/YOU-DARE/scrapers/data/France/ThaisdEscufon_YT/m4a_files'
extension_list = ('*.webm', '*.mkv', '*.m4a')

os.chdir(video_dir)

for ext in extension_list:
    for video in glob.glob(ext):
        m4a_filename = os.path.splitext(os.path.basename(video))[0] + ".m4a"
        AudioSegment.from_file(video).export(m4a_filename, format='mp4')
