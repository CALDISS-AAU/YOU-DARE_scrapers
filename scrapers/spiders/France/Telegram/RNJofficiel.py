''' To run this script use the following command: python -m scrapers.spiders.France.Telegram.RNJofficiel
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/France/RNJofficiel_TELEGRAM/RNJofficiel_2025_04_28-15_07_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)