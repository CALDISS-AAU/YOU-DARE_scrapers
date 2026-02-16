''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m dataprep.dataprep_TELEGRAM.prep_post_only
    Replace all paths with actual paths!
'''

from scrapers.functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Sweden/Telegram/GymXIV_OLD/GymXIV_2025_06_27-13_43_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive, 'GymXIV Old')