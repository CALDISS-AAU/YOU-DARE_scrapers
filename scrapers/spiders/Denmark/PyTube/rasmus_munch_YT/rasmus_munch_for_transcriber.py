from .....functions.transcriber_data_functions import Transcriber_data_Functions
import os
''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Denmark.PyTube.rasmus_munch_YT.rasmus_munch_for_transcriber
'''

transcriber_prep = Transcriber_data_Functions()
transcriber_prep.clean_transcribed_audio_files_setup(
    base_path='/work/YOU-DARE/scrapers/data/Denmark/rasmus_munch_YT'
)

transcriber_prep.add_transcribed_text_to_video_data(
    dataset_path='/work/YOU-DARE/scrapers/data/Denmark/rasmus_munch_YT/videos.jl',
    transcriptions_dir='/work/YOU-DARE/scrapers/data/Denmark/rasmus_munch_YT/transcribed'
)
