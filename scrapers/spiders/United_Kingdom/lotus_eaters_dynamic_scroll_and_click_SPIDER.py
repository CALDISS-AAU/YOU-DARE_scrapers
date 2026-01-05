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
from ...functions.scraper_functions.dynamic_scroll_and_click_scrapy_functions import Dynamic_Scroll_And_Click  # Custom shared click functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl lotus_eaters_SPIDER -a max_loads=x # MUST MATCH SPIDER NAME!
    where -a max_loads=x is an optional parameter to limit the number of scrolls/clicks to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/United_Kingdom/lotus_eaters_SPIDER # If the folder does not yet exist
        nohup scrapy crawl lotus_eaters_SPIDER -a max_loads=5 > ./data/United_Kingdom/lotus_eaters_SPIDER/lotus_eaters_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'lotus_eaters_SPIDER' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Lotus eaters' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.lotuseaters.com/category/entertainment', 
        'https://www.lotuseaters.com/category/news', 
        'https://www.lotuseaters.com/category/analysis'
    ] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # ignore /robots.txt for this spider because it doesn't exist
    }

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
            load_more_button_CSS # The link to the button rendering more articles
            click_button_selector_STOP # The indicator-class of the last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
    '''
    links_to_follow_CSS = '.pageListingItem__readMore a::attr(href)'
    article_container_CSS = '.pageListingItem'
    load_more_button_CSS = 'button.button--default'
    load_more_button_STOP_CSS = None # If this is not relevant, set this query to None
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1::text'
    publication_date_CSS = '.post__meta p b::text'
    author_CSS = '.post__meta .author a::text'
    article_categories_CSS = '.post__meta a.post__category::text'
    article_text_CSS = 'main .post__body p *::text, main h3 *::text'
    image_links_CSS = 'main .image *::attr(src)'
    embedded_media_links_CSS = 'main .post__body iframe::attr(src)'
    links_in_text_CSS = 'main .post__body p a::attr(href)'
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_loads=None):
        """Initializes the spider and sets optional max_loads limit."""
        super().__init__()
        Dynamic_Scroll_And_Click.initialize(self, max_loads) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scroll_And_Click.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Dynamic_Scroll_And_Click.load_existing_links(self.save_path) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Renders the frontpage dynamically using Playwright inside a thread
        url = response.url
        rendered_page = yield deferToThread(
            asyncio.run,
            Dynamic_Scroll_And_Click.load_and_collect_links(
                url,
                article_selector=self.article_container_CSS,
                load_more_selector=self.load_more_button_CSS,
                max_loads=self.max_loads,
                wait_after_click=1400, # # default value = 1200, increase if needed
                stop_when_button_has_class=self.load_more_button_STOP_CSS
            )
        )
        article_sel = Selector(text=rendered_page)

        # Finds all article links
        links = article_sel.css(self.links_to_follow_CSS).getall()
        links = [response.urljoin(l) for l in links if l] # Ensures proper joining and non-None links

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
                Dynamic_Scroll_And_Click.fetch_page_with_playwright(
                    link,
                    # timeout_time=90000, # default value = 60000, increase if needed
                    # wait_time=5000 # default value = 2000, increase if needed
                )
            )

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
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'author' 
        authors = response.css(self.author_CSS).getall()
        author_clean = ''
        if len(authors)>0: # Only cleans existing authors
            for author in authors:
                author_clean = author_clean + ', ' + General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = authors
        # Extract article_categories
        article_categories = response.css(self.article_categories_CSS).get()
        if article_categories: # Only cleans existing articles
            article_categories_clean = General_Functions.clean_text(article_categories) # Cleans the text - See doc string
        else:
            article_categories_clean = article_categories
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        links_in_text = response.css(self.links_in_text_CSS).getall()
        # Extract 'other_items' 
        other_items = self.other_items
        # Extract 'article_HTML'
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

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse 
