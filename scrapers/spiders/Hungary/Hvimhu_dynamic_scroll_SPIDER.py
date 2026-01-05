### IMPORTS ###
# External imports #
import re 
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
        scrapy crawl Hvimhu_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter to limit the number of scrolls to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/Hungary/Hvimhu_SPIDER # If the folder does not yet exist
        nohup scrapy crawl Hvimhu_SPIDER -a max_scrolls=0 > ./data/Hungary/Hvimhu_SPIDER/Hvimhu_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class DynamicScrollSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'Hvimhu_SPIDER' # Spider name - must be unique within given project
    region = 'Hungary' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Hvim.hu' # The source of the articles - NOT the author!
    start_urls = ['https://www.hvim.hu/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    articles_CSS = 'a[href*="/post/"]'
    links_to_follow_CSS = 'a[href*="/post/"]::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'title::text'
    publication_date_CSS = 'meta[property="article:published_time"]::attr(content)'
    author_CSS = None
    article_categories_CSS = None
    article_text_CSS = '.VQDdIN *::text'
    image_links_CSS = '.VQDdIN wow-image img::attr(data-pin-media)'
    embedded_media_links_css = 'iframe::attr(src)'
    links_in_text_CSS = '.VQDdIN a::attr(href)'
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
    def parse(self, response):
        # Renders the frontpage dynamically using Playwright inside a thread
        url = response.url
        self.logger.info("[spider] calling with post_scroll_pause=50000")      
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
                post_scroll_pause=50000 # default value = 1500, increase if needed
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
                    # max_scrolls=10, # default value = None, set to value if the scrolls on each article should be limited
                    wait_time=5000 # default value = 2000, increase if needed
                )
            )
            article_sel = Selector(text=article_page)

            # Parse and yield the article
            item = self.parse_article(article_sel, link) # Goes to each article and scrapes relevant information
            if item: # If any information has been scraped the data is added to 'collected_items'
                collected_items.append(item)
        
        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

    def parse_article(self, response, article_link_parsed): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_link' 
        article_link = article_link_parsed
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title:
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else: 
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.css(self.publication_date_CSS).get(default='').strip()
        # Extract 'author' 
        author_clean = self.author_CSS
        # Extract 'article_categories' 
        article_categories = self.article_categories_CSS
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_CSS).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.css(self.embedded_media_links_css).getall()
        # Extract 'links_in_text'
        links_in_text = response.css(self.links_in_text_CSS).getall()
        # Extract 'other_items' 
        other_items = self.other_items
        #Extract 'article HTML'
        article_HTML = response.get()

        # --- Fallback for lazy-loaded embedded videos (no <iframe> until click) ---
        # The preview button has a background-image like:
        #   url("https://i.ytimg.com/vi/<VIDEO_ID>/maxresdefault.jpg")
        # We extract <VIDEO_ID> and reconstruct an embed URL for each.
        if not embedded_media_links:
            preview_styles = response.css('button.react-player__preview::attr(style)').getall()
            yt_ids = []
            for style in preview_styles:
                m = re.search(r'i\.ytimg\.com/vi/([^/]+)/', style)
                if m:
                    yt_ids.append(m.group(1))

            # (Optional) broader sweep: any inline style on the page that references i.ytimg.com/vi/
            if not yt_ids:
                extra_styles = response.css('[style*="i.ytimg.com/vi/"]::attr(style)').getall()
                for style in extra_styles:
                    m = re.search(r'i\.ytimg\.com/vi/([^/]+)/', style)
                    if m:
                        yt_ids.append(m.group(1))

            if yt_ids:
                embedded_med = [f'https://www.youtube.com/embed/{vid}?autoplay=0&mute=0&controls=1' for vid in yt_ids]
        # -------------------------------------------------------------------------

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
