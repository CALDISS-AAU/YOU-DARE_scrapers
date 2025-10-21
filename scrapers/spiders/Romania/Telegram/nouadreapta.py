''' To run this script use the following command: python -m scrapers.spiders.Romania.Telegram.nouadreapta
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Romania/Telegram/nouadreapta/nouadreapta_2025_07_07-10_32_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)