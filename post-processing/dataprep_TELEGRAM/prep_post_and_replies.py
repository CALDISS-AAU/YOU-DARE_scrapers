''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m dataprep.dataprep_TELEGRAM.prep_post_and_replies
    Replace all paths with actual paths!
'''

from scrapers.functions.manual_functions import Manual_Functions  # Custom shared functions

source = 'Vito Quiles'
csv_path_archive = '/work/YOU-DARE/scrapers/data/Spain/Telegram/vitoquilestelegram/vitoquilestelegram_2025_08_21-13_47_archive.csv'#'./data/Country/Telegram/source/source_yyyy_mm_dd-hh_MM_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive, source)
print('Archive på jl')
csv_path_reply = '/work/YOU-DARE/scrapers/data/Spain/Telegram/vitoquilestelegram/vitoquilestelegram_2025_08_21-13_47_reply_archive.csv'#'./data/Country/Telegram/source/source_yyyy_mm_dd-hh_MM_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply, source)
print('Replies på jl')

Manual_Functions.telegram_to_threads(csv_path_archive, csv_path_reply, source=source)