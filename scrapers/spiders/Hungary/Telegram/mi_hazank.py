''' To run this script use the following command: python -m scrapers.spiders.Hungary.Telegram.mi_hazank
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/mihazankifjai/mihazankifjai_2025_07_03-12_00_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
# csv_path_reply = ''
# Manual_Functions.telegram_to_jl(csv_path_reply)