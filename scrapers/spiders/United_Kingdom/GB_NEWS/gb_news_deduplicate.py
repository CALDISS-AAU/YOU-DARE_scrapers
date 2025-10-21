import json

data_p = "/work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_SPIDER_rerun/data_gb_news_SPIDER_rerun.jl"

urls = []
articles_keep = []

with open(data_p, "r") as f:
    for line in f:
        entry = json.loads(line)

        if entry.get('article_link') not in urls:
            articles_keep.append(entry)
            urls.append(entry.get('article_link'))

out_p = "/work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_SPIDER_rerun/data_gb_news_rerun_dedupl_SPIDER.jl"

with open(out_p, "w", encoding = "utf-8") as f:
    for entry in articles_keep:
        json.dump(entry, f)
        f.write("\n")