''' To run this script use the following command: python -m scrapers.spiders.Hungary.Telegram.inczebela_TELEGRAM
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path_archive = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/InczeBelaLegionarius/InczeBelaLegionarius_2025_08_22-14_22_archive.csv'
Manual_Functions.telegram_to_jl(csv_path_archive)

csv_path_reply = ''
#Manual_Functions.telegram_to_jl(csv_path_reply)


#RUN THIS TO CONVERT TO THREADS!
Manual_Functions.telegram_to_threads("Incze Bela Legionarius", csv_path_archive, csv_path_reply)