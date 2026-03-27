from scrapers.functions.transcriber_data_functions import Transcriber_data_Functions

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m post-processing.dataprep_YT.prep_for_transcriber_YT
    Replace all paths with actual paths!
''' 

transcriber_prep = Transcriber_data_Functions()
data_path = './data/Romania/cezar_lonascu_YT'

transcriber_prep.clean_transcribed_audio_files_setup(
    base_path=data_path
)