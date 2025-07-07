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

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl Identitaer_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter
'''


### CREATING THE SPIDER ###
class DynamicSpider(
    scrapy.Spider):  # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'Identitaer_SPIDER_wrong'  # Spider name - must be unique within given project
    region = 'Denmark'  # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Generation identitaer - website'  # The source of the articles - NOT the author!
    start_urls = [
        'https://identitaer.dk/category/presse']  # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    items = ScrapersItem()  # Makes the items from items.py accessable within this spider

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
    links_to_follow_CSS = '.oct-post-title a::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''

    article_CSS = 'div .tt-post'
    article_title_CSS = '.text-center::text'
    author_CSS = 'There is no author per se'
    publication_date_CSS = 'span.tt-post-date-single::text'
    article_text_bits_CSS = '.div.simple-text *::text'
    image_links_CSS = 'figure .wp-block-image img::attr(src)'
    external_links_CSS = 'a p *::attr(href)'
    article_HTML_bits_CSS = '.text-center'

    # ... other queries

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None):
        """Initializes the spider and sets optional max_scrolls limit."""
        super().__init__()
        Dynamic_Scrapy.initialize(self, max_scrolls)  # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy.setup_from_crawler(spider, crawler)  # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy.load_existing_links(self.save_path)  # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def parse(self, response):  # Can't be renamed
        """ Entry point that delegates to parse_front for dynamic page rendering. """
        return self.parse_front(response)

    @inlineCallbacks
    def parse_front(self, response):  # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        # Renders the page and creates new selector object
        url = response.url
        page_source = yield deferToThread(asyncio.run, Dynamic_Scrapy.fetch_with_playwright(url, self.max_scrolls))
        sel = Selector(text=page_source)

        # Finds and follows article links
        links = sel.css(self.links_to_follow_CSS).getall()
        links = [urljoin(url, l) for l in links]

        self.logger.info(f"Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        for link in links:
            if link in self.existing_data:  # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield scrapy.Request(
                url=link,
                callback=self.parse_article,  # Calls parse_article on each link
                meta={
                    'article_link': link,
                    # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                }
            )

        # NOTE For dynamic sites, pagination usually requires simulating a click with Playwright
        # If applicable, implement next page logic manually using playwright inside a loop

    def parse_article(self, response):  # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = self.items  # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link']

        if article_link in self.existing_data:  # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        article = response.css(self.article_CSS)
        # Extract 'article_title'
        article_title = article.css(
            self.article_title_CSS).get()  # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.clean_text(article_title)  # Cleans the text - See doc string
        # Extract 'author'
        author = article.css(self.author_CSS).get()
        # Extract 'publication_date'
        publication_date = article.css(self.publication_date_CSS).get()
        # Extract 'article_text'
        article_text_bits = article.css(self.article_text_bits_CSS).getall()
        article_text_clean = General_Functions.join_and_clean(
            article_text_bits)  # Joins and cleans all text elements - See doc string
        # Extract 'image_links'
        image_links = article.css(self.image_links_CSS).getall()
        # Extract 'external_links'
        external_links = article.css(self.external_links_CSS).getall()
        # Extract 'article_HTML'
        article_HTML_bits = article.css(self.article_HTML_bits_CSS).getall()
        article_HTML = ' '.join(article_HTML_bits).strip()

        # Assign variables to items here - the items below are minumum requirenments!
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date  # Retract and assign your own publication date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['external_links'] = external_links
        items[
            'article_HTML'] = article_HTML  # Retract and assign the full HTML (often article_title where not only text is retracted)

        self.existing_data.add(
            article_link)  # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items  # Writes the items to the FEEDS function in the settings.py file hence saving them
