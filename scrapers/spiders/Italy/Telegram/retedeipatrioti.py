''' To run this script use the following command: python -m scrapers.spiders.Italy.Telegram.retedeipatrioti
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Italy/Telegram/retedeipatrioti/retedeipatrioti_2025_07_03-09_59_archive.csv'
Manual_Functions.telegram_to_jl(csv_path)