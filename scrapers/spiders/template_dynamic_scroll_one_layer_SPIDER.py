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

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl template_dynamic_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'template_dynamic_SPIDER' # Spider name - must be unique within given project
    region = 'Country' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'name of website' # The source of the articles - NOT the author!
    start_urls = ['https://www.some.website/page'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    article_container_CSS = 'some css'
    article_link_CSS = 'some css'
    article_title_CSS = 'some css'
    publication_date_CSS = 'some css'
    article_text_bits_CSS = 'some css'
    article_HTML_bits_CSS = 'some css'
    image_links_CSS = 'some css'
    image_captions_CSS = 'some css'
    external_links_CSS = 'some css'
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
        # Renders the page and creates new selector object
        url = response.url
        page_source = yield deferToThread(asyncio.run, Dynamic_Scrapy.fetch_with_playwright(url, self.max_scrolls))

        sel = Selector(text=page_source)
        articles = sel.css(self.article_container_CSS) 
        items_list = []
        timestamp = datetime.now().strftime('%Y-%m-%d')

        # Finds data for each article 
        for art in articles:
            article_link = art.css(self.article_link_CSS).get()
            if article_link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {article_link}") # Only scrapes information from articles that has not yet been scraped
                continue

            it = ScrapersItem() 
            # Extract 'article_title'
            article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
            # Extract 'publication_date'
            publication_date = art.css(self.publication_date_CSS).get()
            # Extract 'article_text'
            article_text_bits = response.xpath(self.article_text_bits_XPATH).getall() 
            article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
            # Extract 'article_HTML'
            article_HTML_bits = art.css(self.article_HTML_bits_CSS).getall()
            joined_html = ' '.join(article_HTML_bits).strip()
            # Extract 'image_links'
            image_links = art.css(self.image_links_CSS).getall()
            # Extract 'image_captions'
            image_captions_html = art.css(self.image_captions_CSS).getall()
            # Detects what images have captions
            captioned_image_srcs = [
                img for img in image_links
                if art.xpath(f".//figure[.//img[@src='{img}']]")
            ]
            # Matches image captions to relevant images
            fixed_captions = Dynamic_Scrapy.match_images_with_captions(
                image_links=image_links,
                image_captions_html=image_captions_html,
                captioned_image_srcs=captioned_image_srcs
            )
            # Extract 'external_links'
            external_links = art.css(self.external_links_CSS).getall()

            # Assigns all scraped data to relevant items
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

            # Appends relevant items to items_list and adds link to list of scraped articles
            items_list.append(it)
            self.existing_data.add(article_link)

        # Returns the items_list with all articles for scrapy to save dynamically
        returnValue(items_list) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

