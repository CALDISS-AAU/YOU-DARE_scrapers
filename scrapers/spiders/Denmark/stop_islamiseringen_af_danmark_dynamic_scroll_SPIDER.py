### IMPORTS ###
# External imports #
import scrapy
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.dynamic_scroll_scrapy_functions import Dynamic_Scroll_Scrapy  # Custom shared functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl stop_islamiseringen_af_danmark_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter to limit the number of scrolls to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/Denmark/stop_islamiseringen_af_danmark_SPIDER # If the folder does not yet exist
        nohup scrapy crawl stop_islamiseringen_af_danmark_SPIDER -a max_scrolls=0 > ./data/Denmark/stop_islamiseringen_af_danmark_SPIDER/stop_islamiseringen_af_danmark_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider):
    name = 'stop_islamiseringen_af_danmark_SPIDER'
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Stop Islamiseringen Af Danmark' # The source of the articles - NOT the author!
    start_urls = [
        'https://siaddk.wordpress.com/',
    ]

    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_css') and 'some_xpath' must use response.xpath('some_xpath')
        For clarrification:
            Front page referes to the first site the spider encounters after following the start_urls
            Article page referes to the site of each individual article
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            articles_CSS # The outer container of each article used to determine when to stop scrolling (when no more articles are rendered after as scroll -> stop)
            links_to_follow # The links to the individual articles
    '''
    articles_CSS = 'article.post'
    article_link_CSS = 'h1 a::attr(href)'

    article_title_CSS = 'h1 a::text'
    publication_date_CSS = 'time::text'
    author_CSS = None 
    article_categories_CSS = None
    article_text_CSS = 'div.content p *::text, div.content figure *::text'
    image_links_CSS = 'div.content img::attr(src)'
    embedded_media_links_CSS = None
    links_in_text_CSS = 'div.content p a::attr(href), div.content figure a::attr(href)'
    other_items = None

    def __init__(self, max_scrolls=None):
        super().__init__()
        Dynamic_Scroll_Scrapy.initialize(self, max_scrolls)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scroll_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info(f"Loading from save file: {self.save_path}")
        self.existing_links = Dynamic_Scroll_Scrapy.load_existing_links(self.save_path)

    @inlineCallbacks
    def parse(self, response):
        url = response.url
        rendered_page = yield deferToThread(
            asyncio.run, 
            Dynamic_Scroll_Scrapy.fetch_with_playwright_adaptive(
                url,
                article_selector=self.articles_CSS,     
                max_scrolls=self.max_scrolls,
                # start_wait=2000, # default value = 1000, increase if needed
                # max_wait=90000, # default value = 60000, increase if needed
                # growth_factor=5.0, # default value = 2.0, increase if needed
                # plateau_checks=5, # default value = 2, increase if needed
                # post_scroll_pause=3000 # default value = 1500, increase if needed
            )
        )
        sel = Selector(text=rendered_page)

        articles = sel.css(self.articles_CSS)
        collected_items = []

        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source'
        source = self.source

        for article in articles:
            article_link = article.css(self.article_link_CSS).get()
            article_link = response.urljoin(article_link)
            if article_link in self.existing_links:
                self.logger.info(f"Skipping duplicate article: {article_link}") # Only scrapes information from the front page for articles that has not yet been scraped
                continue

            # Extract 'article_title' 
            article_title = article.css(self.article_title_CSS).get()
            if article_title:
                article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
            else: 
                article_title_clean = article_title
            # Extract 'publication_date' 
            publication_date = article.css(self.publication_date_CSS).get()
            # Extract 'author' 
            author_clean = self.author_CSS
            # Extract 'article_categories' 
            article_categories = self.article_categories_CSS
            # Extract 'article_text' 
            article_text_bits = article.css(self.article_text_CSS).getall()
            article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans text
            # Extract 'image_links' 
            image_links = article.css(self.image_links_CSS).getall()
            # Extract 'embedded_media_links' 
            embedded_media_links = self.embedded_media_links_CSS
            # Extract 'links_in_text'
            links_in_text = article.css(self.links_in_text_CSS).getall()
            # Extract 'other_items' 
            other_items = self.other_items
            #Extract 'article HTML'
            article_HTML = article.get()

            items = ScrapersItem() # Makes the items from items.py accessable within this spider for every single article

            # Assign variables to items here
            items['scrape_date'] = timestamp
            items['source'] = source
            items['article_link'] = article_link
            items['article_title'] = article_title_clean
            items['publication_date'] = publication_date
            items['author'] = author_clean
            items['article_categories'] = article_categories
            items['article_text'] = article_text_clean
            items['image_links'] = image_links
            items['embedded_media_links'] = embedded_media_links
            items['links_in_text'] = links_in_text
            items['other_items'] = other_items
            items['article_HTML'] = article_HTML

            self.logger.info(f"Scraped article: {article_title} ({article_link})") # Logs successful scrape

            collected_items.append(items)

            self.existing_links.add(article_link)

        returnValue(collected_items)