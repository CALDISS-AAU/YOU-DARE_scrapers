from ....functions.pytubefix_functions import Pytubefix_Functions
from urllib.parse import urlparse, parse_qs, unquote

''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m scrapers.spiders.Hungary.PyTube.fidesz_videos_YT
    The first time this script is called after stating up a new UCloud session it will give the following message:
        Please open https://www.google.com/device and input code ABC-DEF-GHI
        Press enter when you have completed this step.
    After you've entered the website and passed the code you'll be asked which YouTube user you want to proceed as.
    Without this check and login PyTube can't age verify and will therefore not download any age restricted audio/video.
'''

def yt_normalize(url: str) -> str:
    u = url.strip()
    # decode percent-encoding once (handles origin=... etc.)
    u = unquote(u)

    p = urlparse(u)
    host = (p.netloc or "").lower()
    path = p.path or ""

    # watch?v=ID
    if "watch" in path:
        q = parse_qs(p.query)
        vid = (q.get("v") or [""])[0]
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"

    # youtu.be/ID
    if "youtu.be" in host:
        vid = path.lstrip("/").split("/")[0]
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"

    # /embed/ID
    if "/embed/" in path:
        vid = path.split("/embed/")[-1].split("/")[0]
        # strip any trailing query fragments
        vid = vid.split("?")[0].split("&")[0]
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"

    # Fallback: if it already has v= in query
    q = parse_qs(p.query)
    vid = (q.get("v") or [""])[0]
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"

    # If nothing matches, return the original (last resort)
    return u

input_txt = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_SPIDER/data_fidesz_videos_merged_SPIDER.txt'
URLS = []

with open(input_txt, 'r') as txt_file:
    for row in txt_file:
        URLS.append(row)

for url in URLS:
    clean_url = yt_normalize(url)
    Pytubefix_Functions.pytubefix_from_single(clean_url, __file__, source = 'Fidesz videos')

# for url in URLS:
#     clean_url = yt_normalize(url)
#     output_path = Pytubefix_Single.pytubefix_from_video(url, __file__, nesting_level=5)