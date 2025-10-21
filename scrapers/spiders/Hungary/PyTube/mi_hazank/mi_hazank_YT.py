from datetime import time
import sys
from pathlib import Path
from .....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Hungary.PyTube.mi_hazank.mi_hazank_YT
    The first time this script is called after stating up a new UCloud session it will give the following message:
        Please open https://www.google.com/device and input code 
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

# The link to the channel of interest
channel_url = 'https://www.youtube.com/@DuroDoraHivatalos/videos'
# source = 'Mi hazank YouTube'

# Generating the proper output path
generated_output_path = Pytubefix_Functions.generate_output_path(__file__, nesting_level=5)

# Generates a jsonlines file and downloads all audio from all videos and places it on the generated output path
Pytubefix_Functions.pytubefix_from_channel(channel_url, __file__, nesting_level=5)

Pytubefix_Functions.retry_failed_downloads(generated_output_path)
# Pytubefix_Functions.pytubefix_from_channel_jsonlines(channel_url, generated_output_path)