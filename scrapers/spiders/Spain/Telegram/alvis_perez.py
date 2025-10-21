''' To run this script use the following command: python -m scrapers.spiders.Spain.Telegram.alvis_perez
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Spain/Telegram/AlvisePerez_TELEGRAM/AlvisePerez_2025_06_26-13_11_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Spain/Telegram/AlvisePerez_TELEGRAM/AlvisePerez_2025_06_26-13_11_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply)

Manual_Functions.telegram_to_threads("Alvise Pérez", csv_path_archive, csv_path_reply)