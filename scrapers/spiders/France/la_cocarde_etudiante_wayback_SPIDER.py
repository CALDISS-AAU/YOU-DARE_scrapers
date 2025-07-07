### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
import os.path
import json
import re 
from datetime import datetime
from w3lib.html import remove_tags
# Internal imports #
from ...items import ScrapersItem # Imports the items from the items.py file
from ...functions.general_functions import General_Functions # importing cleaning functions

### INSTRUCTIONS ###
''' To run this scraper open a terminal, change the directory to
        /work/YOU-DARE/scrapers/
    and pass
        scrapy crawl {name}
    to scrape the entire url, and pass
        scrapy crawl {name} -a max_pages=x
    to only scrape x pages
'''
# --- !!! --- #
# --- Since this spider only scrapes new articles and breaks when a new page contains URLs for 
# --- already scraped articles, the first run should always be of the entire web-page, hence
# ---       scrapy crawl CPI_news
# --- !!! --- # 
''' While this spider might need some adjustments within the function code,
    it should for the most parts be ready to go for any web page after changing
    the variables in the beginning of the class.
    This spider is programmed for web pages on the form:
    - From all start URLs the links for the various articles can be scraped (in parse_front)
    - From the start URLs a link for the next page can be found, and this page should look like the first page (from the start URL)
    - From all articles it should be possible to scrape:
        * title
        * publication_date
        * article_text
        * article_HTML (the full HTML of the text - to capture any formatting of the text)
        * image_links
        * external_links (within the text)
    - To scrape any other information from the articles, e.g. author, internal links etc. the CSS-queries for these needs to be added 
        as variables before any functions (in the same way as existing variables) before they are found in the function parse_article
        (in the same way as existing response calls) and should lastly be assigned to its respectible item (in the same way as existing assignments).
        Lastly it is important to define the item within the "items.py" file (in the same way as existing items has been assigned).
'''

### CREATING THE SPIDER ###
class WaybackcocardeSpider(scrapy.Spider):
    name = 'la_cocarde_etudiante_wayback_SPIDER'
    region = 'France'

    urls = [
        'https://cocardeetudiante.com/articles/',
        'https://cocardeetudiante.com/articles/page/2/',
        'https://cocardeetudiante.com/articles/page/3/',
        'https://cocardeetudiante.com/articles/page/4/',
        'https://cocardeetudiante.com/articles/page/5/',
        'https://cocardeetudiante.com/communiques/'
    ]

    save_path = f"./data/{region}/{name}/data_{name}.jl"

    items = ScrapersItem()

    article_CSS = 'article.elementor-post'
    links_to_follow_CSS = 'a.elementor-post__thumbnail__link::attr(href)'
    next_page_CSS = '.page-numbers::attr(href)'
    publication_date_CSS = '.elementor-post-date::text'
    title_CSS = 'h1.elementor-heading-title.elementor-size-default::text'
    article_text_bits_CSS = '.elementor-widget-container p ::text'
    article_HTML_bits_CSS = '.elementor-widget-container p'
    image_links_CSS = '.attachment-large.size-large.wp-image-7186.lazyloading img::attr(src)'
    author_text_CSS = 'p.has-text-align-right *::text'
    themes_CSS = '.elementor-post-info__terms-list a.elementor-post-info__terms-list-item::text'
    article_references_CSS = 'ul.wp-block-list li.has-small-font-size'

    def __init__(self, max_pages=None):
        super().__init__()
        self.MAX_PAGES = int(max_pages) if max_pages else None
        self.save_file = self.save_path
        self.existing_links = set()
        self.scraped_data = []

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WaybackcocardeSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_data = set()

        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            item = json.loads(line.strip())
                            if "article_link" in item:
                                self.existing_data.add(item["article_link"])
                        except json.JSONDecodeError:
                            self.logger.warning("Skipping invalid JSON line.")
                self.logger.info(f"Loaded {len(self.existing_data)} existing articles.")
            except Exception as e:
                self.logger.warning(f"Error reading existing data: {e}, starting fresh.")
                self.existing_data = set()

    def start_requests(self):
        timestamp = '20240101000000'
        self.logger.info("Starting requests from Wayback Machine")

        for url in self.urls:
            wayback_url = f'https://web.archive.org/web/{timestamp}/{url}'
            self.logger.info(f"Generating request for: {wayback_url}")

            yield scrapy.Request(
                url=wayback_url,
                callback=self.parse_front
            )

    def parse_front(self, response):
        articles = response.css(self.article_CSS)

        for article in articles:
            link = article.css(self.links_to_follow_CSS).get()
            publication_date = article.css(self.publication_date_CSS).get()

            self.logger.info(f"Link: {link}, Date: {publication_date}")

            if link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={'article_link': link, 'publication_date': publication_date}
            )

    def parse_article(self, response):
        items = self.items
        timestamp = datetime.now().strftime('%Y-%m-%d')
        article_link = response.meta['article_link']
        publication_date = response.meta['publication_date']

        if article_link in self.existing_data:
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        article_title = response.css(self.title_CSS).get()
        article_text_bits = response.css(self.article_text_bits_CSS).getall()
        article_text = ' '.join(article_text_bits).strip()
        article_HTML_bits = response.css(self.article_HTML_bits_CSS).getall()
        article_HTML = ' '.join(article_HTML_bits).strip()
        themes_text = response.css(self.themes_CSS).getall()
        author = response.css(self.author_text_CSS).getall()

        article_references = response.css(self.article_references_CSS)
        sources = []
        for li in article_references:
            text_parts = li.css('::text').getall()
            hrefs = li.css('a::attr(href)').getall()
            combined_text = ''.join(part.strip() for part in text_parts if part.strip())
            sources.append({
                'text': combined_text,
                'links': hrefs
            })

        article_text = General_Functions.clean_text(article_text)

        items['scrape_date'] = timestamp
        items['article_link'] = article_link
        items['article_title'] = article_title
        items['publication_date'] = publication_date
        items['article_text'] = article_text
        items['image_links'] = response.css(self.image_links_CSS).getall()
        items['themes_text'] = themes_text
        items['references_text'] = sources
        items['author'] = author

        self.existing_links.add(article_link)

        yield items