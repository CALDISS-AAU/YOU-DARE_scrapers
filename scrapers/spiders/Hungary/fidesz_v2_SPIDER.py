### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from datetime import datetime
from urllib.parse import urljoin
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Dynamic_Scrapy_Click  # Custom shared click functions
from ...functions.scrapy_functions import DynamicClickAndWait # Custom click with wait
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl fidesz_hirek_v2_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
    OR
        cd ./YOU-DARE/scrapers
        mkdir -p /work/YOU-DARE/scrapers/data/Hungary/fidesz_hirek_v2_SPIDER # If the folder does not yet exist
        nohup scrapy crawl fidesz_hirek_v2_SPIDER > /work/YOU-DARE/scrapers/data/Hungary/fidesz_hirek_v2_SPIDER/fidesz_hirek_SPIDER_2025-10-30_SPIDER.log
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider):
    name = 'fidesz_hirek_v2_SPIDER'
    region = 'Hungary'
    source = 'Fidesz'
    start_urls = ['https://fidesz.hu/hirek']

    # LISTING SELECTORS (verify these!)
    links_to_follow_CSS = '.news-item-text-container a::attr(href)'
    # Try alternates if ^ is empty:
    alt_links_css = [
        '.news__item a::attr(href)',
        'article a::attr(href)',
        '.news-list a::attr(href)'
    ]

    # ARTICLE SELECTORS (prefer robust locators over absolute XPaths)
    article_title_XPATH = '//*[@id="content"]//h1/text() | //*[@id="content"]//h2/text()'
    author_XPATH = ''#'//*[@id="content"]//*[contains(@class,"author") or contains(text(),"Szerző")]/text()'
    publication_date_XPATH = '//*[@id="content"]//*[contains(@class,"date") or self::time or strong]/text()'
    article_text_bits_CSS = '.news__lead *::text, .news__body *::text'#, article *::text'
    image_links_CSS = '.news.news--details img::attr(src), article img::attr(src)'
    external_links_CSS = '.news.news--details a::attr(href), article a::attr(href)'
    youtube_CSS = '.news.news--details iframe::attr(src), article iframe::attr(src)'

    custom_settings = {
        # Make logs noisier while debugging
        'LOG_LEVEL': 'INFO',
        # Avoid re-downloading the same index pages if you re-run
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.RFPDupeFilter',
    }

    def __init__(self, max_scrolls=None, max_pages=None):
        super().__init__()
        Dynamic_Scrapy_Click.initialize(self, max_pages)
        self.max_pages = int(max_pages) if max_pages else 1
        self.seen_links = set()
        self.existing_data = set()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy_Click.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        try:
            self.existing_data = Dynamic_Scrapy_Click.load_existing_links(self.save_path) or set()
        except Exception as e:
            self.logger.warning(f"load_existing_links failed: {e}")
            self.existing_data = set()

    def start_requests(self):
        base = 'https://fidesz.hu/hirek'
        # Many sites start at page=0; include it to be safe.
        index_urls = [base] + [f'{base}?page={i}' for i in range(0, self.max_pages)]
        for url in index_urls:
            yield scrapy.Request(url, callback=self.parse_index, dont_filter=True, meta={'index_url': url})

    def parse_index(self, response):
        url = response.meta['index_url']
        # Render with Playwright and WAIT for the listing container/links to appear.
        # Adjust wait_for selector to something stable present on listing pages.
        wait_for = '.news, .news-list, .news-item-text-container, article'
        try:
            listing_html = Dynamic_Scrapy_Click.fetch_page_with_playwright(url, wait_for=wait_for, wait_timeout_ms=8000)
        except Exception as e:
            self.logger.warning(f"Playwright render failed for {url}: {e}")
            return

        if not listing_html or len(listing_html) < 2000:
            self.logger.warning(f"Rendered HTML suspiciously short ({len(listing_html) if listing_html else 0}) for {url}")
        listing_sel = Selector(text=listing_html)

        hrefs = listing_sel.css(self.links_to_follow_CSS).getall() or []
        if not hrefs:
            for css in self.alt_links_css:
                alt = listing_sel.css(css).getall() or []
                if alt:
                    self.logger.info(f"Selector fallback hit on {url} -> {css} gave {len(alt)} links")
                    hrefs = alt
                    break

        # Log a tiny snippet to verify we’re on the right DOM
        if not hrefs:
            snippet = listing_sel.xpath('string(//body)').get() or ''
            self.logger.warning(f"No links on {url}. Body snippet: {snippet[:300].strip().replace('\\n',' ')}")
            # Heuristic: if first empty page encountered deep in pagination, stop scheduling further pages
            return

        page_links = []
        for h in hrefs:
            if not h: continue
            full = urljoin(url, h)
            if full in self.seen_links or full in self.existing_data: continue
            self.seen_links.add(full)
            page_links.append(full)

        self.logger.info(f"Found {len(page_links)} new article links on {url}")
        for l in page_links[:5]:
            self.logger.debug(f"Sample link from {url}: {l}")

        for link in page_links:
            # We still render the article with Playwright in parse_article to get dynamic content if needed
            yield scrapy.Request(link, callback=self.parse_article, dont_filter=True)

    def parse_article(self, response):
        # Render with Playwright again to be safe on dynamic bodies
        try:
            article_html = Dynamic_Scrapy_Click.fetch_page_with_playwright(response.url, wait_for='article, .news.news--details, #content', wait_timeout_ms=8000)
        except Exception as e:
            self.logger.warning(f"Playwright render failed for article {response.url}: {e}")
            return
        if not article_html:
            self.logger.warning(f"Empty article HTML for {response.url}")
            return
        sel = Selector(text=article_html)

        items = ScrapersItem()
        timestamp = datetime.now().strftime('%Y-%m-%d')

        title = sel.xpath(self.article_title_XPATH).get()
        title_clean = General_Functions.clean_text(title) if title else None

        author = self.author_XPATH #sel.xpath(self.author_XPATH).get()
        author_clean = General_Functions.clean_text(author) if author else None

        pub_raw = sel.xpath(self.publication_date_XPATH).get()
        publication_date_clean = pub_raw.strip() if pub_raw else None

        text_bits = sel.css(self.article_text_bits_CSS).getall()
        article_text_clean = General_Functions.join_and_clean(text_bits)

        image_links = sel.css(self.image_links_CSS).getall()
        external_links = sel.css(self.external_links_CSS).getall()
        youtube_links = sel.css(self.youtube_CSS).getall()

        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date_clean
        items['source'] = self.source
        items['article_link'] = response.url
        items['article_title'] = title_clean
        items['article_categories'] = 'None'
        items['author'] = author_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = youtube_links
        items['links_in_text'] = external_links
        items['other_items'] = 'None'
        # items['article_HTML'] = article_html  # enable only if you need full HTML

        if not title_clean and not article_text_clean:
            # Log first 200 chars for debugging
            snippet = sel.xpath('string(//body)').get() or ''
            self.logger.warning(f"No content parsed for {response.url}. Body snippet: {snippet[:200].strip().replace('\\n',' ')}")
            return

        self.logger.info(f"Scraped article: {title_clean} ({response.url})")
        self.existing_data.add(response.url)
        yield items
