### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from datetime import datetime

# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from scrapers.functions.scrapy_functions import Static_Scrapy  # Custom shared functions

### CREATING THE SPIDER ###
class NordfrontSpider(scrapy.Spider):
    name = 'NF_TEST_SPIDER'
    region = 'ZZ_Examples'
    start_urls = ['https://www.nordfront.dk/']

    items = ScrapersItem()

    article_CSS = '.post-title'
    links_to_follow_CSS = 'a::attr(href)'
    next_page_CSS = '.next.page-numbers::attr(href)'
    title_CSS = '.post-title::text'

    def __init__(self, max_pages=None):
        super().__init__()
        Static_Scrapy.initialize(self, max_pages)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(NordfrontSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_data = Static_Scrapy.load_existing_links(self.save_file, self.logger)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front,
                meta={'current_page': 1}
            )

    def parse_front(self, response):
        current_page = response.meta['current_page']
        article = response.css(self.article_CSS)
        links_to_follow = article.css(self.links_to_follow_CSS).extract()
        print(f'These are the links to follow: {links_to_follow}')

        for link in links_to_follow:
            if link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={'article_link': link}
            )

        next_page = response.css(self.next_page_CSS).get()
        if next_page and (self.MAX_PAGES is None or current_page < self.MAX_PAGES):
            yield response.follow(
                next_page,
                callback=self.parse_front,
                meta={'current_page': current_page + 1}
            )

    def parse_article(self, response):
        items = self.items
        timestamp = datetime.now().strftime('%Y-%m-%d')
        article_link = response.meta['article_link']

        if article_link in self.existing_data:
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        article_title = response.css(self.title_CSS).get()

        items['scrape_date'] = timestamp
        items['article_link'] = article_link
        items['article_title'] = article_title

        self.existing_links.add(article_link)

        yield items
