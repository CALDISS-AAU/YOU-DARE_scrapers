# version: simple log parser for modernity_SPIDER

import json

log_file = "/work/YOU-DARE/scrapers/data/United_Kingdom/modernity_SPIDER/modernity_SPIDER.log"
output_file = "/work/YOU-DARE/scrapers/data/United_Kingdom/modernity_SPIDER/modernity_links.jl"

def extract_links(log_file, output_file):
    links = set()
    prefix = "DEBUG:modernity_SPIDER:Article link:"
    i = 0

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                i = i + 1
                link = line[len(prefix):].strip()
                if link:
                    links.add(link)

    with open(output_file, "w", encoding="utf-8") as f:
        for link in sorted(links):
            f.write(json.dumps({"url": link}) + "\n")

    print(f"Extracted {len(links)} unique links to {output_file}. \nTotal number of links: {i}")

if __name__ == "__main__":
    extract_links(log_file, output_file)
