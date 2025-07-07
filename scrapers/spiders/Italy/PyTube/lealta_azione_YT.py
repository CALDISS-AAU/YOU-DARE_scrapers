from ....functions.pytubefix_functions import Pytubefix_Functions
from datetime import date

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Italy.PyTube.lealta_azione_YT
    The first time this script is called after stating up a new UCloud session it will give the following message:
        Please open https://www.google.com/device and input code RJQ-YVM-HVF
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

''' dates must be on the form "2020", "2020-01" or "2020-01-01"
parse_partial_date uses dateparser, hence "2020" will be read as "2020-01-01" and "2020-02" as "2020-02-01"!! '''
# from_date = Pytubefix_Functions.parse_partial_date("2017-12")
# to_date = Pytubefix_Functions.parse_partial_date("2018")

# The link to the channel of interest
channel_url = 'https://www.youtube.com/@lealtaazione6032/videos'
# Generates a jsonlines file and downloads all audio from all videos and places it on the generated output path
output_path = Pytubefix_Functions.pytubefix_from_channel(channel_url, __file__)#, from_date=from_date, to_date=to_date)
Pytubefix_Functions.retry_failed_downloads(output_path)