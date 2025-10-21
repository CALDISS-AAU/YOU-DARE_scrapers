from yt_dlp import YoutubeDL

vox_url = 'https://www.youtube.com/c/VoxEspa%C3%B1aTV/videos'  # Change if you like

ydl_opts = {
    'format': 'bestaudio[ext=m4a]/bestaudio', # Determining output type
    'outtmpl': {
        'default': '/work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/yt-dlp_files/m4a_files/%(id)s.%(ext)s', # output folder
        'infojson': '/work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/yt-dlp_files/m4a_files/metadata/%(id)s.%(ext)s'}, # Where to put the metadata
    'ffmpeg_location': '/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static', # Program for downloading best quality and stuff
    'writeinfojson': True, # Metadata set as True
    'download_archive': '/work/YOU-DARE/vox_audio/archive.txt', # Download archive document for logging downloaded files
    'sleep_interval': 4,             # seconds between videos (min delay)
    'max_sleep_interval': 14,         # random delay up to this max
    'ratelimit': 2.0, # Max requests/sec
    'retries': 10, # Retrying
    'fragment_retries': 10, # Fragmentation retries
    'concurrent_fragment_downloads': 1,
    'cookiefile': '/work/YOU-DARE/scrapers/cookies.txt', # Cookies from MKAP's browser for downloading age restricted videos
    'postprocessors': [], # Write stuff here to use ffmpeg stuff
    'ignoreerrors': True,  # Skip videos that fail
    'quiet': False        # See what's happening in terminal
}

with YoutubeDL(ydl_opts) as ydl:
    ydl.download([vox_url])