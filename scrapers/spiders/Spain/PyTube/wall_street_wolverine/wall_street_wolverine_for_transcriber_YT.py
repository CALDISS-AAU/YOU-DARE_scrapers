from .....functions.transcriber_data_functions import Transcriber_data_Functions

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Spain.PyTube.wall_street_wolverine.wall_street_wolverine_for_transcriber_YT
'''

transcriber_prep = Transcriber_data_Functions()

transcriber_prep.clean_transcribed_audio_files_setup(
    base_path='/work/YOU-DARE/scrapers/data/Spain/wall_street_wolverine_YT'
)