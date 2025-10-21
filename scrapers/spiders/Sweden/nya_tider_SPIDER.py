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
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl nya_tider_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
            Using x=300 should be enough (note made 2025-07-02)
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'nya_tider_SPIDER' # Spider name - must be unique within given project
    region = 'Sweden' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Nya Tider' # The source of the articles - NOT the author!
    start_urls = ['https://www.nyatider.nu/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    links_to_follow_CSS = 'article.jeg_post h3 a::attr(href)'
    click_button_selector_CSS = ".jeg_block_loadmore" # CSS selector for the "Load more" button
    # click_button_selector_STOP_XPATH = '//button[@id="load-more-articles" and @current-page="269"]' # CSS for last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
                                                # If this is not relevant, delete this query and delete the argument stop_when_button_has_class in the 
                                                # Dynamic_Scrapy_Click.fetch_links_with_clicking function (inside parse), or set it to it's default value - None
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'h1.jeg_post_title::text'
    author_CSS = '.elementor-post-info__item--type-author::text'
    publication_date_CSS = '.elementor-post-info__item--type-date::text'
    article_text_bits_CSS = 'span.utdrag-artikel::text, .ingress-artikel *::text, .content-inner p *::text, .content-inner h2 *::text, .content-inner h3 *::text, .content-inner ul *::text'
    article_categories_CSS = 'span.utdrag-artikel::text'
    image_links_CSS = 'figure img::attr(src)'
    links_in_text_CSS = '.content-inner a::attr(href)'
    embedded_media_links_CSS = '.content-inner iframe::attr(src)'
    other_items_CSS = 'None'

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None, max_pages=None):
        """Initializes the spider and sets optional max_scrolls and max_pages limit."""
        super().__init__()
        Dynamic_Scrapy_Click.initialize(self, max_pages) # Initializes clicking setup

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy_Click.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy_Click.load_existing_links(self.save_path) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Collects all article links dynamically using Playwright by clicking "Load more" button cumulatively
        url = response.url
        links = yield deferToThread(
            asyncio.run,
            Dynamic_Scrapy_Click.fetch_links_with_clicking(
                url,
                click_button_selector=self.click_button_selector_CSS,
                links_selector=self.links_to_follow_CSS.replace('::attr(href)', ''), # Adjusts selector for link elements
                max_clicks=self.max_pages,
                wait_time=3000,
                stop_when_button_has_class=None
            )
        )
        links = [urljoin(url, l) for l in links if l] # Ensures proper joining and non-None links

        self.logger.info(f"Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        collected_items = []
        
        for link in links:
            if link in self.existing_data: # Only scrapes information for articles that have not yet been scraped
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            # Fetch each article manually
            article_page = yield deferToThread(asyncio.run, Dynamic_Scrapy_Click.fetch_page_with_playwright(link))
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
        # Extract 'author' 
        author = response.css(self.author_CSS).get()
        if author: # Only cleans existing articles
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract 'article_categroies'
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        publication_date_clean = General_Functions.join_and_clean([publication_date] if publication_date else []).strip()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'external_links' 
        raw_links_in_text = response.css(self.links_in_text_CSS).getall()
        links_in_text = [link for link in raw_links_in_text if not link.lower().endswith('.jpg')]
        # Extract 'youtube_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date_clean
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author_clean
        items['article_categories'] = article_categories
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_media_links
        items['links_in_text'] = links_in_text
        items['other_items'] = self.other_items_CSS
        items['article_HTML'] = response.get()

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse
