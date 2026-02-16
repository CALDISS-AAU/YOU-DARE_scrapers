from ....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m scrapers.spiders.Sweden.PyTube.inblick_med_nick_YT
    The first time this script is called after stating up a new session it will give the following message:
        Please open https://www.google.com/device and input code ABC-DEF-GHI
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

''' dates must be on the form "2020", "2020-01" or "2020-01-01"
parse_partial_date uses dateparser, hence "2020" will be read as "2020-01-01" and "2020-02" as "2020-02-01"!! '''
from_date = Pytubefix_Functions.parse_partial_date("2021-06-01")
to_date = Pytubefix_Functions.parse_partial_date("2025-06-30")

# The link to the channel of interest
channel_url = 'https://www.youtube.com/@NickAlinia/videos'

# Generates a jsonlines file and downloads all audio from all videos and deposits it on the generated output path
output_path = Pytubefix_Functions.pytubefix_from_channel(
    channel_url, 
    __file__,
    from_date=from_date,
    to_date=to_date
)

# Retries videos that couldn't be downloaded
Pytubefix_Functions.retry_failed_downloads(output_path)