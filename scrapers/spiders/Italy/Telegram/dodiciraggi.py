''' To run this script use the following command: python -m scrapers.spiders.Italy.Telegram.dodiciraggi
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Italy/Telegram/dodiciraggi/dodiciraggi_2025_07_02-14_53_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)