import pandas as pd
import os
from os import path
import json
import jsonlines

# importing data 
nordfront_main = pd.read_json('/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_SWE.jl', lines=True)
nordfront_SMR = pd.read_json('/work/YOU-DARE/scrapers/data/Sweden/nordfront_SMR_SPIDER/data_nordfront_SMR.jl', lines=True)

nordfront_main['article_link'] = nordfront_main['article_link'].str.replace('\\/', '/', regex=True)
nordfront_SMR['article_link'] = nordfront_SMR['article_link'].str.replace('\\/', '/', regex=True)


merged = nordfront_main.merge(
    nordfront_SMR,
    on='article_link',
    how='left',
    suffixes=('', '.SMR')
)


with open('/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_SWE_complete.jl', 'w', encoding='utf-8') as f:
    for record in merged.to_dict(orient='records'):
        json.dump(record, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')


input_file = '/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_SWE.jl'
output_file = '/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_SWE_COMPLETE_SPIDER.jl'

# Remove articles where link is ending on .smr 🤣
def should_keep(entry):
    return not entry.get("article_link", "").endswith(".smr")

# Yeeting those pesky .smr files
with open(input_file, "r") as infile, open(output_file, "w") as outfile:
    for line in infile:
        entry = json.loads(line)
        if should_keep(entry):
            outfile.write(json.dumps(entry) + "\n")

# remerging
with open("data_nordfront_SWE_COMPLETE_SPIDER.jl", "w") as outfile:
    for fname in ["/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_clean.jl", "/work/YOU-DARE/scrapers/data/Sweden/nordfront_SMR_SPIDER/data_nordfront_SMR.jl"]:
        with open(fname) as infile:
            for line in infile:
                if line.strip():  # skip empty lines
                    outfile.write(line)