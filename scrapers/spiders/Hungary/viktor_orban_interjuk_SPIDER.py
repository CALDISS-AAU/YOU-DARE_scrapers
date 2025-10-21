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
from ...functions.scrapy_functions import DynamicClickAndWait_2 # Custom click with wait
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl viktor_orban_interjuk_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
    OR
        cd ./YOU-DARE/scrapers
        mkdir -p /work/YOU-DARE/scrapers/data/Hungary/viktor_orban_interjuk_SPIDER # If the folder does not yet exist
        nohup scrapy crawl viktor_orban_interjuk_SPIDER > /work/YOU-DARE/scrapers/data/Hungary/viktor_orban_interjuk_SPIDER/viktor_orban_interjuk_2025-08-22_SPIDER.log
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'viktor_orban_interjuk_SPIDER' # Spider name - must be unique within given project
    region = 'Hungary' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Viktor Orban - interjuk' # The source of the articles - NOT the author!
    start_urls = ['https://miniszterelnok.hu/interjuk/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    links_to_follow_XPATH = "//a[contains(@class,'elementor-button')][.//span[contains(normalize-space(),'Elolvasom')]]|//div[contains(@class,'elementor-element')]//a[contains(@class,'jet-listing-dynamic-link__link')][.//span[contains(normalize-space(),'Tovább')]]"
    click_button_selector_XPATH = "//a[contains(@class,'elementor-button')][.//span[contains(normalize-space(),'további interjúk')]]" # CSS selector for the "Load more" button
    # click_button_selector_STOP_CSS = '' # CSS for last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
                                                # If this is not relevant, delete this query and delete the argument stop_when_button_has_class in the 
                                                # Dynamic_Scrapy_Click.fetch_links_with_clicking function (inside parse), or set it to it's default value - None
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'h1.elementor-heading-title::text, h1.jet-listing-dynamic-field__content::text, div#post_title::text'
    author_CSS = 'None'
    publication_date_CSS = 'li[itemprop="datePublished"] time:first-of-type::text' 
    article_text_bits_CSS = 'div.jet-listing-dynamic-field__content *::text, div.elementor-element.elementor-widget.elementor-widget-text-editor *::text, div#post_content_col_1 *::text' 
    image_links_CSS = 'div.jet-listing-dynamic-field__content img::attr(src), div.elementor-element.elementor-widget.elementor-widget-text-editor img::attr(src), div#post_content_col_1 img::attr(src)' # Does not include thumb-nail image which cannot be included without also including 45ish irrelevant images
    external_links_CSS = 'div.jet-listing-dynamic-field__content a::attr(href), div.elementor-element.elementor-widget.elementor-widget-text-editor a::attr(href), div#post_content_col_1 a::attr(href)'
    article_categories_CSS =  'nav[aria-label="breadcrumbs"] a *::text'
    embedded_media_links_CSS =   'div.jet-listing-dynamic-field__content iframe::attr(src), div.elementor-element.elementor-widget.elementor-widget-text-editor iframe::attr(src), div#post_content_col_1 iframe::attr(src)'


    # ... other queries

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
            DynamicClickAndWait_2.click_and_collect_links(
                url,
                click_button_selector=self.click_button_selector_XPATH,
                links_selector=self.links_to_follow_XPATH.replace('::attr(href)', ''), # Adjusts selector for link elements
                max_clicks=self.max_pages,
                wait_time=2000,
                # stop_when_button_has_class=self.click_button_selector_STOP_CSS
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
        author = self.author_CSS
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'categories'
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'external_links' 
        external_links = response.css(self.external_links_CSS).getall()
        # Extract 'youtube_links' 
        embedded_media = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'article_HTML'
        article_HTML = response.get()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['links_in_text'] = external_links
        items['article_categories'] = article_categories
        items['embedded_media_links'] = embedded_media
        items['other_items'] = 'None'
        items['article_HTML'] = article_HTML




        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse
