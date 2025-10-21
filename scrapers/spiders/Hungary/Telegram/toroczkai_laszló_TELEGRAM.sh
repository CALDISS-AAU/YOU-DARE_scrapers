#!/usr/bin/env bash
# packages
pip3 install --upgrade pip
pip3 install telepathy
pip3 install cryptg

# things to get
telepathy --target toroczkai --comprehensive --replies

# '''
#     --target = tag efter s/ i telegram URL
#     --comprehensive = tilføjer ekstra meta data, e.g. emoji reactions 
#     --replies = sørger for at vi får replies med 

#     run by parsing this to the terminal:
#         cd /work/YOU-DARE/telepathy
#         bash /work/YOU-DARE/scrapers/scrapers/spiders/Hungary/Telegram/toroczkai_laszló_TELEGRAM.sh

#     Afterwards use mv -f /work/YOU-DARE/telepathy/telepathy_files/toroczkai /work/YOU-DARE/scrapers/data/Hungary/Telegram
# ''' 