''' To run this script use the following command: python -m scrapers.spiders.Hungary.Telegram.jobbszelso_TELEGRAM
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/jobbszelso/jobbszelso_2025_08_22-13_17_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)
csv_path_reply = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/jobbszelso/jobbszelso_2025_08_22-13_17_reply_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_reply)


#RUN THIS TO CONVERT TO THREADS!
Manual_Functions.telegram_to_threads("Jobbszelso", csv_path_archive, csv_path_reply)