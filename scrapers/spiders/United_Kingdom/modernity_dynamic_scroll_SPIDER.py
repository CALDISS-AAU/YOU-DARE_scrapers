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
        scrapy crawl modernity_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter to limit the number of scrolls to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/United_Kingdom/modernity_SPIDER # If the folder does not yet exist
        nohup scrapy crawl modernity_SPIDER -a max_scrolls=0 > ./data/United_Kingdom/modernity_SPIDER/modernity_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class DynamicScrollSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'modernity_SPIDER' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'modernity' # The source of the articles - NOT the author!
    start_urls = ['https://modernity.news/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    articles_CSS = '.cs-entry__title a'
    links_to_follow_CSS = '.cs-entry__title a::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1 *::text'
    publication_date_CSS = '.cs-entry__header-info .cs-meta-date::text'
    author_CSS = '.cs-entry__header-info .cs-author::text'
    article_categories_CSS = '.cs-entry__category-label::text'
    article_text_CSS = '.cs-entry__subtitle::text, .entry-content>p *::text, .entry-content blockquote p::text'
    image_links_CSS = '.entry-content figure img::attr(data-pk-src)'
    embedded_media_links_CSS = '.entry-content iframe::attr(src)'
    links_in_text_CSS = '.entry-content>p a::attr(href)'
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None):
        """Initializes the spider and sets optional max_scrolls limit."""
        super().__init__()
        Dynamic_Scroll_Scrapy.initialize(self, max_scrolls) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicScrollSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scroll_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Dynamic_Scroll_Scrapy.load_existing_links(self.save_path) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Renders the frontpage dynamically using Playwright inside a thread
        url = response.url
        rendered_page = yield deferToThread(
            asyncio.run,
            Dynamic_Scroll_Scrapy.fetch_with_playwright_adaptive(
                url,
                self.articles_CSS,               
                self.max_scrolls,
                # start_wait=2000, # default value = 1000, increase if needed
                max_wait=600000, # default value = 60000, increase if needed
                # growth_factor=5.0, # default value = 2.0, increase if needed
                # plateau_checks=5, # default value = 2, increase if needed
                # post_scroll_pause=3000 # default value = 1500, increase if needed
            )
        )        
        sel = Selector(text=rendered_page)

        # Finds all article links
        links = sel.css(self.links_to_follow_CSS).getall()
        links = [response.urljoin(l) for l in links]

        self.logger.info(f"Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        collected_items = []
        
        for link in links:
            if link in self.existing_links: # Only scrapes information for articles that have not yet been scraped
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            # Fetch each article manually
            article_page = yield deferToThread(
                asyncio.run, 
                Dynamic_Scroll_Scrapy.fetch_with_playwright(
                    link, 
                    self.max_scrolls, 
                    wait_time=5000
                )
            )
            article_sel = Selector(text=article_page)

            # Parse and yield the article
            item = self.parse_article(article_sel, link) # Goes to each article and scrapes relevant information
            if item: # If any information has been scraped the data is added to 'collected_items'
                collected_items.append(item)
        
        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

    def parse_article(self, response, article_link): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing titles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'author' 
        author = response.css(self.author_CSS).get()
        if author: # Only cleans existing authors
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract article_categories
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded media_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        links_in_text = response.css(self.links_in_text_CSS).getall()
        # Extract 'other_items' 
        other_items = self.other_items
        #Extract 'article HTML'
        article_HTML = response.get()
        
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
        
        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse 
