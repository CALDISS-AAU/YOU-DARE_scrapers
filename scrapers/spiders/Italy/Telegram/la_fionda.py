''' To run this script use the following command: python -m scrapers.spiders.Italy.Telegram.la_fionda
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Italy/Telegram/lafionda/lafionda_2025_07_03-10_50_archive.csv'
# Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Italy/Telegram/lafionda/lafionda_2025_07_03-10_50_reply_archive.csv'
# Manual_Functions.telegram_to_jl(csv_path_reply)


Manual_Functions.telegram_to_threads("La Fionda", csv_path_archive, csv_path_reply) #CALL FUNCTION WITH source, post csv, and reply csv in that order! 