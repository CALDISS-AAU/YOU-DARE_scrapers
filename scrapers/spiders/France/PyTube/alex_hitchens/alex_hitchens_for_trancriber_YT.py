from .....functions.transcriber_data_functions import Transcriber_data_Functions

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers

        python -m scrapers.spiders.France.PyTube.alex_hitchens.alex_hitchens_for_trancriber_YT
'''

transcriber_prep = Transcriber_data_Functions()

transcriber_prep.clean_transcribed_audio_files_setup(
     base_path='/work/YOU-DARE/scrapers/data/France/alex_hitchens_YT'
)


