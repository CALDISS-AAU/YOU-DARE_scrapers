''' To run this script use the following command: python -m scrapers.spiders.Romania.Telegram.comunitatea_identitara
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Romania/Telegram/comunitateaidentitara/comunitateaidentitara_2025_07_03-14_18_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Romania/Telegram/comunitateaidentitara/comunitateaidentitara_2025_07_03-14_18_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply)


Manual_Functions.telegram_to_threads("Comunitatea Identitară", csv_path_archive, csv_path_reply)