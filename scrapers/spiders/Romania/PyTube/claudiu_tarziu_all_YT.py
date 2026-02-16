from ....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m scrapers.spiders.Romania.PyTube.claudiu_tarziu_all_YT
    The first time this script is called after stating up a new session it will give the following message:
        Please open https://www.google.com/device and input code ABC-DEF-GHI
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

# The links of interest
channel_url = 'https://www.youtube.com/@Claudiu.Tarziu'
playlist1 = 'https://www.youtube.com/playlist?list=PLSfRvqOFLFUHnsVwtWTl3k0HEudFqgTkc'
playlist2 = 'https://www.youtube.com/playlist?list=PLSfRvqOFLFUEBdX9Q0Eor34eYuv7SKdo9'
playlist3 = 'https://www.youtube.com/playlist?list=PLSfRvqOFLFUH8spjKSSPJNq1CurHrbcdt'
single_video = 'https://www.youtube.com/watch?v=mo8Pc-VsNZQ'

# Generating the proper output path
output_path = Pytubefix_Functions.generate_output_path(__file__)

# Generates a jsonlines file and downloads all audio from all videos and deposits it on the generated output path
Pytubefix_Functions.pytubefix_from_channel(
    channel_url, 
    __file__, 
    shorts=True, 
    live=True, 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_playlist(
    playlist1, 
    __file__, 
    source='Claudiu.Tarziu', 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_playlist(
    playlist2, 
    __file__, 
    source='Claudiu.Tarziu', 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_playlist(
    playlist3, 
    __file__, 
    source='Claudiu.Tarziu', 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_single(
    single_video, 
    __file__, 
    source='Claudiu.Tarziu'
)

# Retries videos that couldn't be downloaded
Pytubefix_Functions.retry_failed_downloads(output_path)
