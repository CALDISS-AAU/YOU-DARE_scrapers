''' MAY NOT BE DELETED!!
    Use cd /work/YOU-DARE/scrapers
    scrapy crawl SIAD_SPIDER -a max_scrolls=2
'''

### IMPORTS ###
# For scrapy
import scrapy
from scrapy.selector import Selector
from ...items import ScrapersItem
# For playwright
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
# For formatting and saving
from datetime import datetime
# Custom functions
from ...functions.scrapy_functions import Dynamic_Scrapy
from ...functions.general_functions import General_Functions

### CREATING THE SPIDER ###
class SIADSpider(scrapy.Spider):
    name = 'SIAD_SPIDER'
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Stop Islamiseringen Af Danmark' # The source of the articles - NOT the author!
    start_urls = [
        'https://siaddk.wordpress.com/',
    ]

    article_container_CSS = 'article.post'
    article_link_CSS = 'h1 a::attr(href)'
    article_title_CSS = 'h1 a::text'
    publication_date_CSS = 'time::text'
    article_text_bits_CSS = 'div.content p *::text, div.content figure *::text'
    article_HTML_bits_CSS = 'div.content p, div.content figure'
    image_links_CSS = 'div.content img::attr(src)'
    image_captions_CSS = 'figcaption *::text'
    external_links_CSS = 'div.content p a::attr(href), div.content figure a::attr(href)'

    def __init__(self, max_scrolls=None):
        super().__init__()
        Dynamic_Scrapy.initialize(self, max_scrolls)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(SIADSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info(f"Loading from save file: {self.save_path}")
        self.existing_data = Dynamic_Scrapy.load_existing_links(self.save_path)
        self.logger.info(f"Loaded {len(self.existing_data)} existing links.")

    @inlineCallbacks
    def parse(self, response):
        url = response.url
        page_source = yield deferToThread(
            asyncio.run,
            Dynamic_Scrapy.fetch_with_playwright(url, self.max_scrolls)
        )
        sel = Selector(text=page_source)
        articles = sel.css(self.article_container_CSS)
        items_list = []
        timestamp = datetime.now().strftime('%Y-%m-%d')

        for art in articles:
            article_link = art.css(self.article_link_CSS).get()
            if article_link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {article_link}") # Only scrapes information from the front page for articles that has not yet been scraped
                continue

            it = ScrapersItem()
            article_title = art.css(self.article_title_CSS).get()
            publication_date = art.css(self.publication_date_CSS).get()
            article_text_bits = art.css(self.article_text_bits_CSS).getall()
            joined_text = General_Functions.clean_text(' '.join(article_text_bits).strip())
            article_HTML_bits = art.css(self.article_HTML_bits_CSS).getall()
            joined_html = ' '.join(article_HTML_bits).strip()
            image_links = art.css(self.image_links_CSS).getall()
            image_captions_html = art.css(self.image_captions_CSS).getall()

            captioned_image_srcs = [
                img for img in image_links
                if art.xpath(f".//figure[.//img[@src='{img}']]")
            ]

            fixed_captions = Dynamic_Scrapy.match_images_with_captions(
                image_links=image_links,
                image_captions_html=image_captions_html,
                captioned_image_srcs=captioned_image_srcs
            )

            external_links = art.css(self.external_links_CSS).getall()

            it['scrape_date'] = timestamp
            it['source'] = self.source
            it['article_link'] = article_link
            it['article_title'] = General_Functions.clean_text(article_title if article_title else '')
            it['publication_date'] = publication_date
            it['article_text'] = joined_text
            it['image_links'] = image_links
            it['image_captions'] = fixed_captions
            it['external_links'] = external_links
            it['article_HTML'] = joined_html

            items_list.append(it)
            self.existing_data.add(article_link)

        returnValue(items_list)