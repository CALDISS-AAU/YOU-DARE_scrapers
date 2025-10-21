cd /work/YOU-DARE/scrapers

nohup scrapy crawl fidesz_dynamic_Scroll_SPIDER -a max_pages=700 > /work/YOU-DARE/scrapers/data/Hungary/fidesz_dynamic_Scroll_SPIDER/fidesz_SPIDER.log

echo "✔finished with the first 700 pages! Shutting down"