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
from ...functions.scrapy_functions import DynamicScrollAndClick

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl lotus_eaters_analysis_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'lotus_eaters_analysis_SPIDER' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Lotus eaters - analysis' # The source of the articles - NOT the author!
    start_urls = ['https://www.lotuseaters.com/category/analysis'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # ignore /robots.txt for this spider because it doesn't exist
        # Optional but handy:
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "AUTOTHROTTLE_ENABLED": True,
        "DOWNLOAD_DELAY": 0.5,
        # If you want to nuke the robots middleware entirely:
        # "DOWNLOADER_MIDDLEWARES": {
        #     "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": None
        # },
    }

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
    links_to_follow_CSS = '.pageListingItem__readMore a::attr(href)'
    article_container_CSS = '.pageListingItem'
    load_more_button_CSS = 'button.button--default'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'h1::text'
    author_CSS = '.post__meta .author a::text'
    publication_date_CSS = '.post__meta p b::text'
    article_categories_CSS = '.post__meta a.post__category::text'
    article_text_bits_CSS = 'main .post__body p *::text, main h3 *::text'
    image_links_CSS = 'main .image *::attr(src)'
    external_links_CSS = 'main .post__body p a::attr(href)'
    embedded_media_CSS = 'main .post__body iframe::attr(src)'
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
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Renders the frontpage dynamically using Playwright inside a thread
        url = response.url
        rendered_page = yield deferToThread(
            asyncio.run,
            DynamicScrollAndClick.fetch_with_playwright_hybrid(
                url=response.url,
                article_selector=self.article_container_CSS,
                load_more_selector=self.load_more_button_CSS,
                max_cycles=self.max_scrolls,          # keeps your -a max_scrolls semantic (as "click cycles")
                # scrolls_per_cycle=2,                   # tweak per site
                wait_after_click=1400
            )
        )
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
            item = self.parse_article(article_sel, link) # Goes to each article and scrapes relevant information
            if item: # If any information has been scraped the data is added to 'collected_items'
                collected_items.append(item)
        
        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

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
        authors = response.css(self.author_CSS).getall()
        author_clean = ''
        if len(authors)>0: # Only cleans existing authors
            for author in authors:
                author_clean = author_clean + ', ' + General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author_clean
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string

        # Extract article_categories
        article_categories = response.css(self.article_categories_CSS).get()
        if article_categories: # Only cleans existing articles
            article_categories_clean = General_Functions.clean_text(article_categories) # Cleans the text - See doc string
        else:
            article_categories_clean = article_categories
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        
        # Extract 'external_links' 
        external_links = response.css(self.external_links_CSS).getall()

        # Extract 'embedded media' 
        embedded_med = response.css(self.embedded_media_CSS).getall()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author_clean
        items['article_categories'] = article_categories_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_med
        items['external_links'] = external_links
        items['other_items'] = 'None'
        items['article_HTML'] = response.get()

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse 
