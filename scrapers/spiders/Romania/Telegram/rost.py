''' To run this script use the following command: python -m scrapers.spiders.Romania.Telegram.rost
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Romania/Telegram/revistaRost/revistaRost_2025_08_19-10_58_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Romania/Telegram/revistaRost/revistaRost_2025_08_19-10_58_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply)

# Manual_Functions.telegram_to_threads("Rost", csv_path_archive, csv_path_reply) #CALL FUNCTION WITH source, post csv, and reply csv in that order! 



