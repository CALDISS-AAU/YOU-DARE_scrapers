''' To run this script use the following command: python -m scrapers.spiders.Spain.Telegram.nucleo_nacional
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Spain/Telegram/unetenucleonacional_TELEGRAM/unetenucleonacional_2025_06_27-08_25_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
