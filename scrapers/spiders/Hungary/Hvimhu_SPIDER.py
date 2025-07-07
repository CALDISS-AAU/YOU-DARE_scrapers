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
from ...functions.scrapy_functions import Dynamic_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl Hvimhu_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter
'''


### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'Hvimhu_SPIDER' # Spider name - must be unique within given project
    region = 'Hungary' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Hvim.hu' # The source of the articles - NOT the author!
    start_urls = ['https://www.hvim.hu/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    links_to_follow_CSS = 'a.O16KGI::attr(href)'

    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'title::text'
    date_of_scraping = datetime.now()
    publication_date_CSS = 'meta[property="article:published_time"]::attr(content)'
    article_text_bits_CSS = 'article *::text'
    image_links_CSS = 'wow-image img::attr(data-pin-media)'
    external_links_CSS = '.VQDdIN a::attr(href)'
    article_HTML_bits_CSS = 'article'

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
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Renders the frontpage dynamically using Playwright inside a thread
        url = response.url
        rendered_page = yield deferToThread(asyncio.run, Dynamic_Scrapy.fetch_with_playwright(url, self.max_scrolls))
        sel = Selector(text=rendered_page)

        # Finds all article links
        links = sel.css(self.links_to_follow_CSS).getall()
        links = [urljoin(url, l) for l in links]

        self.logger.info(f"Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        collected_items = []
        
        for link in links:
            if link in self.existing_data: # Only scrapes information for articles that have not yet been scraped
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            # Fetch each article manually
            article_page = yield deferToThread(asyncio.run, Dynamic_Scrapy.fetch_with_playwright(link, self.max_scrolls))
            article_sel = Selector(text=article_page)

            # Parse and yield the article
            items = self.parse_article(article_sel, link) # Goes to each article and scrapes relevant information
            if items: # If any information has been scraped the data is added to 'collected_items'
                collected_items.append(items)
        
        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!



    def parse_article(self, response_selector, article_link): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        items = ScrapersItem() # Makes the items from items.py accessable within this function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_title'
        article_title = response_selector.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        # Extract 'article_text'
        article_text_bits = response_selector.css(self.article_text_bits_CSS).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        #Article externals links and links to pictures
        external_links = response_selector.css(self.external_links_CSS).getall()
        image_links = response_selector.css(self.image_links_CSS).getall()
        #Article HTML bits
        article_HTML = response_selector.css(self.article_HTML_bits_CSS)


        # Assign variables to items here - the items below are minumum requirenments! 
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean.split('http')[0].strip()
        items['publication_date'] = response_selector.css(self.publication_date_CSS).get(default='').strip() #Retract and assign own publication dat
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['external_links'] = external_links
        items['article_HTML'] = response_selector.css(self.article_HTML_bits_CSS).get(default='').strip() # Retract and assign the full HTML (often article_title where not only text is retracted)

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape
        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the item to parse 
