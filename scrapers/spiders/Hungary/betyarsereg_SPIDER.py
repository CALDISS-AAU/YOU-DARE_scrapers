### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from datetime import datetime

import os
from pathlib import Path
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl betyarsereg_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
    OR
        cd ./YOU-DARE/scrapers
        mkdir -p /work/YOU-DARE/scrapers/data/Hungary/betyarsereg_SPIDER # If the folder does not yet exist
        nohup scrapy crawl betyarsereg_SPIDER > /work/YOU-DARE/scrapers/data/Hungary/betyarsereg_SPIDER/betyarsereg_SPIDER_2025-08-21_SPIDER.log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'betyarsereg_SPIDER' # Spider name - must be unique within given project
    region = 'Hungary' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Betyarsereg' # The source of the articles - NOT the author!
    start_urls = ['https://betyarsereg.hu'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    # 1) Deliver 403s to callback instead of raising HttpError
    handle_httpstatus_list = [403]

    # 3) Optional but recommended: bring back browser-ish headers & retries
    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
            # "Accept-Encoding": "gzip, deflate, br, zstd",
            "Upgrade-Insecure-Requests": "1",
            # Chromium client hints (modern browsers send these)
            "sec-ch-ua": '"Google Chrome";v="128", "Chromium";v="128", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            # Fetch metadata headers seen on real navigations
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.google.com/",
        },
        # Modern Chrome UA
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),

        # politeness / retries
        "COOKIES_ENABLED": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "RETRY_HTTP_CODES": [403, 429, 502, 503, 520, 522],
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3,
        "AUTOTHROTTLE_MAX_DELAY": 15,
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "ROBOTSTXT_OBEY": True,
    }

    items = ScrapersItem() # Makes the items from items.py accessable within this spider

    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_css') and 'some_xpath' must use response.xpath('some_xpath')
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            links_to_follow # The links to the individual articles
            next_page # The links to the next page
        How to pass information from the parse_front function to the parse_article function will be described in greater detail later on.
    '''
    links_to_follow_CSS = 'div#tdi_204 h3 a::attr(href), div#tdi_126 h3 a::attr(href)'
    next_page_CSS = 'div.page-nav a[aria-label="next-page"]::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'div.tdb-block-inner h1 *::text'
    author_CSS = 'No author'
    publication_date_CSS = 'div#tdi_88 time *::text'
    article_text_bits_CSS = 'div.tdb-block-inner p *::text, div.tdb-block-inner h2 *::text'
    image_links_CSS = 'div.tdb-block-inner img.entry-thumb::attr(src), div.tdb-block-inner img.alignnone::attr(src), p img::attr(src), div.wp-block-image figure a::attr(href)' 
    embedded_media_links_CSS = 'div.tdb-block-inner iframe::attr(src)'
    links_in_text_CSS = 'div.tdb-block-inner p a::attr(href)' 
    article_categories_XPATH = '//*[contains(@class, "tdb-tags")]//text()[normalize-space() != "Cimkék:"]' 
    other_items_CSS = 'nothing else'
    # ... other queries


    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_pages=None):
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Static_Scrapy.initialize(self, max_pages) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(StaticSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Static_Scrapy.load_existing_links(self.save_file, self.logger) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def _errback_403(self, failure):
        resp = getattr(failure.value, "response", None)
        if resp:
            self.logger.warning("403 page snippet: %r", resp.text[:1000])

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front,
                meta={'current_page': 1}
            )

    def _save_403_html(self, response):
        outdir = Path(f"data/{self.region}/{self.name}")
        outdir.mkdir(parents=True, exist_ok=True)
        fname = outdir / f"403_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(response.text)
        self.logger.warning("Saved 403 HTML to %s", fname)

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        if response.status == 403:
            self.logger.warning("403 body snippet: %r", response.text[:1000])
            self._save_403_html(response)
            return

        current_page = response.meta['current_page'] # Saves 'current_page' from start_request

        # Finds and follows article links 
        links = response.css(self.links_to_follow_CSS).getall() # Gets all article links 
        for link in links:
            if link in self.existing_data: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article, # Calls parse_article on each link
                meta={
                    'article_link': link, # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                }
            )

        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the nex page if the page is not None
            yield next_page_url

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = self.items # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link'] 
        
        if article_link in self.existing_data: # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'author' 
        author = self.author_CSS #response.css(self.author_CSS).get()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        links_in_text = response.css(self.links_in_text_CSS).getall()
        # Extract 'article_categories' 
        article_categories = response.xpath(self.article_categories_XPATH).getall()
        # Extract 'other_items' 
        other_items = self.other_items_CSS

        # Assign variables to items here - the items below are minumum requirenments! 
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['author'] = author
        items['links_in_text'] = links_in_text
        items['embedded_media_links'] = embedded_media_links
        items['article_categories'] = article_categories
        items['other_items'] = other_items
        items['article_HTML'] = response.text  # Raw HTML of the article

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them