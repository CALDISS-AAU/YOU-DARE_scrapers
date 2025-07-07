''' To run this script use the following command: python -m scrapers.spiders.Denmark.Telegram.maniphestocore
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Denmark/maniphestocore_TELEGRAM/maniphestocore/maniphestocore_2025_05_01-11_56_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)