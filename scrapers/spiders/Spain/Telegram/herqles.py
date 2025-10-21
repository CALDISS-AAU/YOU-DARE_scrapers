''' To run this script use the following command: python -m scrapers.spiders.Spain.Telegram.herqles
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Spain/Telegram/herQles_TELEGRAM/herQles_2025_06_26-09_03_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Spain/Telegram/herQles_TELEGRAM/herQles_2025_06_26-09_03_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply)

Manual_Functions.telegram_to_threads("HerQles", csv_path_archive, csv_path_reply)