from ....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./YOU-DARE/scrapers
        python -m scrapers.spiders.Romania.PyTube.noua_drepta_Emisiunea_Destin_Demografic_YT.py
    The first time this script is called after stating up a new UCloud session it will give the following message:
        Please open https://www.google.com/device and input code RJQ-YVM-HVF
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

# The link to the channel of interest
playlist_url = 'https://www.youtube.com/playlist?list=PL0TmVsuh8_nxgrbN9CQzAIVvlsHefD_0K'
# source = 'Iseul and Anne - Le Café des Antigones YouTube'

# Generating the proper output path
generated_output_path = Pytubefix_Functions.generate_output_path(__file__)

# Generates a jsonlines file and downloads all audio from all videos and places it on the generated output path
Pytubefix_Functions.pytubefix_from_channel(playlist_url, __file__)
# Pytubefix_Functions.pytubefix_from_channel_jsonlines(channel_url, generated_output_path)3