import os 
import pandas as pd
from os import path
import json
import jsonlines
import re

# Merging Noua Dreapta datasets
# importing data 
opinii = pd.read_json(
    '/work/YOU-DARE/scrapers/data/Romania/noua_dreapta_opinii_SPIDER/data_noua_dreapta_opinii_SPIDER.jl',
    lines=True
)
actuini = pd.read_json(
    '/work/YOU-DARE/scrapers/data/Romania/noua_dreapta_actiuni_SPIDER/data_noua_dreapta_actiuni_SPIDER.jl',
    lines=True
)

# combine vertically (stack rows)
combined = pd.concat([actuini, opinii], ignore_index=True)

# write back to .jl
with open(
    '/work/YOU-DARE/scrapers/data/Romania/noua_dreapta_actiuni_SPIDER/data_noua_dreapta_RO_SPIDER.jl',
    'w',
    encoding='utf-8'
) as f:
    for record in combined.to_dict(orient='records'):
        json.dump(record, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')


# fixing Rost sources
Rost = pd.read_json(
   '/work/YOU-DARE/scrapers/data/Romania/rost_SPIDER/data_rost_SPIDER.jl',
   lines=True 
)

# Overwrite column value
Rost["source"] = "Rost"

# write back in JSON lines format
with open('/work/YOU-DARE/scrapers/data/Romania/rost_SPIDER/data_rost_SPIDER.jl', 'w', encoding='utf-8') as f:
    for record in Rost.to_dict(orient='records'):
        json.dump(record, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')

# Fixing Cultura vietii sources
Cultura = pd.read_json(
   '/work/YOU-DARE/scrapers/data/Romania/cultura_vietii_SPIDER/data_cultura_vietii_SPIDER.jl',
   lines=True 
)

# Overwrite column value
Cultura["source"] = "Cultura Vietii"

# write back in JSON lines format
with open('/work/YOU-DARE/scrapers/data/Romania/cultura_vietii_SPIDER/data_cultura_vietii_2_SPIDER.jl', 'w', encoding='utf-8') as f:
    for record in Cultura.to_dict(orient='records'):
        json.dump(record, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')

