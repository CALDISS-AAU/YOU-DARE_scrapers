# version 2025-10
import json

input_path = "/work/YOU-DARE/scrapers/data/Hungary/fidesz_hirek_SPIDER/data_fidesz_hirek_SPIDER_OLD.jl"
output_path = "/work/YOU-DARE/scrapers/data/Hungary/fidesz_hirek_SPIDER/data_fidesz_hirek_SPIDER.jl"

with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
    for line in infile:
        if line.strip():
            item = json.loads(line)
            item["author"] = None
            outfile.write(json.dumps(item, ensure_ascii=False) + "\n")

print("✅ Author field set to null and file saved successfully.")
