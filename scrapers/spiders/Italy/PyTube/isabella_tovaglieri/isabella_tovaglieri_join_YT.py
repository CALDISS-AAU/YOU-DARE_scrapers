from .....functions.transcriber_data_functions import Transcriber_data_Functions

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Italy.PyTube.isabella_tovaglieri.isabella_tovaglieri_join_YT
'''

transcriber_prep = Transcriber_data_Functions()

directory = '/work/YOU-DARE/scrapers/data/Italy/isabella_tovaglieri_YT'
dataset_path = f'{directory}/videos.jl'
transcriptions_dir = f'{directory}/transcribed'
transcriber_prep.add_transcribed_text_to_video_data(dataset_path, transcriptions_dir)

print(f'\n\n\n#### Meta-data and transcibed text has been merged ####\n\n\n')

