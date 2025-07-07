''' To run this script use the following command: python -m scrapers.spiders.Denmark.Manual.DFUngdom
    IMPORTANT! If multiple image links use | as a seperator in the CSV file!
'''

from ....functions.manual_functions import Manual_Functions  # Custom shared functions

csv_path = '/work/YOU-DARE/scrapers/data/Denmark/DFUngdom_MANUAL/DF_Ungdom_MANUAL.csv'
Manual_Functions.csv_to_jl(csv_path)