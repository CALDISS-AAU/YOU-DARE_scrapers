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
import json
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Dynamic_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' This scraper uses the links collected from gb_news_v2_reduced and re-downloads contents using a different parser.
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl gb_news_SPIDER_rerun -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter
    OR
        cd ./YOU-DARE/scrapers
        mkdir -p /work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_SPIDER_rerun # If the folder does not yet exist
        nohup scrapy crawl gb_news_SPIDER_rerun > /work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_SPIDER/gb_news_SPIDER_DATE.out
'''

# READ COLLECTED ARTICLES
data_p = "/work/YOU-DARE/scrapers/data/United_Kingdom/gb_news_v2_reduced_SPIDER/data_gb_news_v2_reduced_SPIDER.jl"

collected_urls = []

with open(data_p, "r") as f:
    for line in f:
        entry = json.loads(line)

        article_url = entry.get('article_link')

        if article_url:
            collected_urls.append(article_url)


### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'gb_news_SPIDER_rerun' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'GB news - opinion' # The source of the articles - NOT the author!
    start_urls = collected_urls # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    links_to_follow_CSS = 'article .widget__head>a::attr(href)'
    articles_CSS = 'article .widget__head>a'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'h1 *::text'
    author_CSS = '.custom-author__name-desc a::text'
    # publication_date_CSS = '.custom-dates p::text'
    publication_date_XPATH = 'normalize-space(substring-after(string(//*[contains(@class,"custom-dates")]//p[contains(@class,"created-date")]), "Published: "))'
    # article_text_bits_CSS = '.body-description p:not(.image-media p):not(.conversation-starter-wrapper p):not(.media-caption p):not(.trending-item)::text'
    article_text_bits_XPATH = (
        '//div[contains(@class, "body-description")]//p['
        'not(ancestor::*[contains(@class, "image-media") or '
        'contains(@class, "conversation-starter-wrapper") or '
        'contains(@class, "media-caption") or '
        'contains(@class, "trending-item")])]/text()[normalize-space()!="GB NEWS"]'
        ' | //h2[contains(concat(" ", normalize-space(@class), " "), " widget__subheadline-text ")]//text()[normalize-space()!="GB NEWS"]'
        ' | //h2[contains(concat(" ", normalize-space(@class), " "), " widget__subheadline-text ")]/following-sibling::*[1][self::p]//text()[normalize-space()!="GB NEWS"]'
    )
    article_categories_CSS = 'None' 
    image_links_CSS = [] # Can't catch them
    # external_links_CSS = '.body-description p:not(.image-media p, .conversation-starter-wrapper p, .media-caption p, .trending-item p, .posts-wrapper p) a::attr(href)'
    external_links_XPATH = '//div[contains(@class, "body-description")]//p[' \
        'not(ancestor::*[contains(@class, "image-media") or ' \
        'contains(@class, "conversation-starter-wrapper") or ' \
        'contains(@class, "media-caption") or ' \
        'contains(@class, "trending-item") or ' \
        'contains(@class, "posts-wrapper")])]' \
        '//a/@href'
    embedded_media_CSS = '.body-description iframe::attr(src)'
    # ... other queries

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None):
        """Initializes the spider and sets optional max_scrolls limit."""
        super().__init__()
        Dynamic_Scrapy.initialize(self, max_scrolls) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy.load_existing_links(self.save_path) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def parse(self, response): # Can't be renamed

        sel = Selector(text=response.text)
        item = self.parse_article(sel, response.url)
        
        if item:
            yield item

    def parse_article(self, response, article_link): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        items = ScrapersItem() # Makes the items from items.py accessable within this function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # # Extract 'author' 
        author = response.css(self.author_CSS).get()
        if author: # Only cleans existing articles
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).get()
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string

        # Extract article_categories
        article_categories = self.article_categories_CSS #response.css(self.article_categories_CSS).getall()
        # Extract 'image_links' 
        image_links = self.image_links_CSS#response.css(self.image_links_CSS).getall()
        
        # Extract 'external_links' 
        external_links = response.xpath(self.external_links_XPATH).getall()

        # Extract 'embedded media' 
        embedded_med = response.css(self.embedded_media_CSS).getall()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author_clean
        items['article_categories'] = article_categories
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_med
        items['external_links'] = external_links
        items['other_items'] = 'None'
        items['article_HTML'] = ''
        
        
        self.logger.info(f"Scraped article: {article_title} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse 
