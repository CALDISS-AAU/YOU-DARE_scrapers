''' To run this script use the following command: python -m scrapers.spiders.France.Telegram.papacitofdp
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/France/papacitofdp_TELEGRAM/papacitofdp_2025_04_28-15_06_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)