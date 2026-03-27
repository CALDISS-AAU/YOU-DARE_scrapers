from ....functions.pytubefix_functions import Pytubefix_Functions

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m scrapers.spiders.Romania.PyTube.cezar_lonascu_YT
    The first time this script is called after stating up a new session it will give the following message:
        Please open https://www.google.com/device and input code ABC-DEF-GHI
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

# The links of interest
channel_url_videos = 'https://www.youtube.com/@cezarionascu71/videos'
channel_url_streams = 'https://www.youtube.com/@cezarionascu71/streams'
playlist_1 = 'https://www.youtube.com/playlist?list=PLnB67EAd_txZ81eBrY4EKMpyMHPG7h2wr'
playlist_2 = 'https://www.youtube.com/playlist?list=PLhwbvb1FMcC2BoZdNGTyUP7_3y8Xr1otU'
video_1 = 'https://www.youtube.com/watch?v=U61WrjhnJSU'
video_2 = 'https://www.youtube.com/watch?v=gIBXN1gFBVI'
video_3 = 'https://www.youtube.com/watch?v=ZuSgAlfk9s8'
video_4 = 'https://www.youtube.com/watch?v=zy9IwbdtJ84'
video_5 = 'https://www.youtube.com/watch?v=D6RDsGSVP1A'
video_6 = 'https://www.youtube.com/watch?v=uUOb1WuyPBI'
video_7 = 'https://www.youtube.com/watch?v=U-hPIhGzWc4'
video_8 = 'https://www.youtube.com/watch?v=pyPuc63m8x0'
video_9 = 'https://www.youtube.com/watch?v=XUIsW7EMoKo'
video_10 = 'https://www.youtube.com/watch?v=_yX9ElPMM3g'
video_11 = 'https://www.youtube.com/watch?v=OZa4FuOcIaM'
video_12 = 'https://www.youtube.com/watch?v=dtqA_LpUJtY'

# Generating the proper output path
output_path = Pytubefix_Functions.generate_output_path(__file__)

# Generates a jsonlines file and downloads all audio from all videos and deposits it on the generated output path
Pytubefix_Functions.pytubefix_from_channel(
    channel_url_videos, 
    __file__, 
    shorts=True, 
    live=True, 
    check_for_downloaded=True, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_channel(
    channel_url_streams, 
    __file__, 
    shorts=True, 
    live=True, 
    check_for_downloaded=True, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_playlist(
    playlist_1, 
    __file__, 
    source='Cezar Lonascu', 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_playlist(
    playlist_2, 
    __file__, 
    source='Cezar Lonascu', 
    check_for_downloaded=True
)
Pytubefix_Functions.pytubefix_from_single(
    video_1, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_2, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_3, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_4, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_5, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_6, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_7, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_8, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_9, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_10, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_11, 
    __file__, 
    source='Cezar Lonascu'
)
Pytubefix_Functions.pytubefix_from_single(
    video_12, 
    __file__, 
    source='Cezar Lonascu'
)

# Retries videos that couldn't be downloaded
Pytubefix_Functions.retry_failed_downloads(output_path)
