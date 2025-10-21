''' To run this script use the following command: python -m scrapers.spiders.Sweden.Telegram.the_golden_one
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Sweden/Telegram/thegoldenone_TELEGRAM/thegoldenone_2025_06_27-11_13_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)