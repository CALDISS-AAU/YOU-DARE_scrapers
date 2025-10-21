''' To run this script use the following command: python -m scrapers.spiders.Hungary.Telegram.durodora_mihazank_TELEGRAM
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/durodora/durodora_2025_08_22-12_55_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/durodora/durodora_2025_08_22-12_55_reply_archive.csv'
#Manual_Functions.telegram_to_jl(csv_path_reply)


#RUN THIS TO CONVERT TO THREADS!
Manual_Functions.telegram_to_threads("Duro Dora - Mi hazank", csv_path_archive, csv_path_reply)