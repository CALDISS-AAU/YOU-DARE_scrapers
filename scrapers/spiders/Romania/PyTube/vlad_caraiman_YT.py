from ....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m scrapers.spiders.Romania.PyTube.vlad_caraiman_YT
    The first time this script is called after stating up a new session it will give the following message:
        Please open https://www.google.com/device and input code ABC-DEF-GHI
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

# The links of interest
channel_url_full = 'https://www.youtube.com/@alphaacademyro'
channel_url_videos = 'https://www.youtube.com/@alphaacademyro/videos'
video_1 = 'https://www.youtube.com/watch?v=FTIGYGavSjk'
video_2 = 'https://www.youtube.com/watch?v=PnJXQfPjZIE'
video_3 = 'https://www.youtube.com/watch?v=dpR0lCJk7jI'
video_4 = 'https://www.youtube.com/watch?v=urz9ImJy6Ss'
video_5 = 'https://www.youtube.com/watch?v=_D8eQ0n1WA4'

# Generating the proper output path
output_path = Pytubefix_Functions.generate_output_path(__file__)

# Generates a jsonlines file and downloads all audio from all videos and deposits it on the generated output path
Pytubefix_Functions.pytubefix_from_channel(
    channel_url_full, 
    __file__, 
    shorts=True, 
    live=True, 
    check_for_downloaded=True, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_channel(
    channel_url_videos, 
    __file__, 
    shorts=True, 
    live=True, 
    check_for_downloaded=True, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_single(
    video_1, 
    __file__, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_single(
    video_2, 
    __file__, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_single(
    video_3, 
    __file__, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_single(
    video_4, 
    __file__, 
    source='Vlad Caraiman'
)
Pytubefix_Functions.pytubefix_from_single(
    video_5, 
    __file__, 
    source='Vlad Caraiman'
)

# Retries videos that couldn't be downloaded
Pytubefix_Functions.retry_failed_downloads(output_path)
