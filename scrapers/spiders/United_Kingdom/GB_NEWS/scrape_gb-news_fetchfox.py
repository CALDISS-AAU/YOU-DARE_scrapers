import requests
import json

url = "https://api.fetchfox.ai/api/scrape"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer ff_z7ccwxmpm6w1brdcjisl91ur3w3owhevofcilph0"
}
payload = {
    "pattern": "https://www.gbnews.com/opinion/*",
    "template": {
        "scrape_date": "Today's date - the date of when this scrape is run in YYYY-MM-DD",
        "publication_date": "The date the article/post is published",
        "article_link": "The URL to the article/post",
        "article_title": "The main title of the article post",
        "article_text": "The text of the article itself including subheadings. Stripped of formatting",
        "embedded_media_links": "Links to media in iframe containers",
        "links_in_text": "Links to other websites - usually inside a tags",
        "image_links": "URLs to images included in the article text",
        "source": "GB News - Opinion"
        },
    "ai": {
        "model": "openai:gpt-4.1",
        "apiKey": "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"
    },
    "max_visits": 500,
    "max_extracts": 5000
}

response = requests.post(url, headers=headers, json=payload)
data = response.json()

data_out_p = "/work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_TEST_SPIDER/data_gb_news_FETCHFOX.json"
data_out_jl_p = "/work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_TEST_SPIDER/data_gb_news_FETCHFOX.jl"

with open(data_out_p, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

with open(data_out_jl_p, "w", encoding="utf-8") as f:
    for item in data:
            f.write(json.dumps(item) + "\n")
