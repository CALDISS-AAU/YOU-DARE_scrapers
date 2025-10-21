#!/usr/bin/env bash
# packages
pip3 install --upgrade pip
pip3 install telepathy
pip3 install cryptg

# things to get
telepathy --target novakelod --comprehensive --replies

#ROOT = '/work/YOU-DARE/scrapers/data/Hungary/Telegram/novakelod_mihazank_TELEGRAM'

#mv -f '/work/YOU-DARE/telepathy/telepathy_files/novakelod.mihazank' $ROOT

# '''
#     --target = tag efter s/ i telegram URL
#     --comprehensive = tilføjer ekstra meta data, e.g. emoji reactions 
#     --replies = sørger for at vi får replies med 

#     run by parsing this to the terminal:
#         cd /work/YOU-DARE/telepathy
#         bash /work/YOU-DARE/scrapers/scrapers/spiders/Hungary/Telegram/novakelod_mihazank_TELEGRAM.sh

#
# ''' 