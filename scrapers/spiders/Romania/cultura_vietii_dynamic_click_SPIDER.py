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
from ...functions.scraper_functions.dynamic_click_scrapy_functions import Dynamic_Click_Scrapy  # Custom shared click functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl cultura_vietii_SPIDER -a max_clicks=x # MUST MATCH SPIDER NAME!
    where -a max_clicks=x is an optional parameter to limit the number of clicks to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/Romania/cultura_vietii_SPIDER # If the folder does not yet exist
        nohup scrapy crawl cultura_vietii_SPIDER -a max_clicks=0 > ./data/Romania/cultura_vietii_SPIDER/cultura_vietii_SPIDER_$(date +%F).log
'''
 
### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'cultura_vietii_SPIDER' # Spider name - must be unique within given project
    region = 'Romania' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Cultura Vietii' # The source of the articles - NOT the author!
    start_url_template = "https://www.culturavietii.ro/{}"
    keywords = [
        "?s=sexualitate",
        "?s=demografie",
        "?s=esential",
        "?s=bunastarea-familiei",
        "?s=educatie",
        "?s=politica-legislatie",
        "?s=bioetica",
        "?s=reproducere-asistata",
        "?s=stiinte-juridice-si-filosofie",
        "?s=religie",
        "tag/video",
        "tag/restabilirea-ordinii-naturale/",
        "tag/demografia-este-destin/",
        "tag/casatoria/",
        "tag/Mituri-despre-avort/",
        "tag/noua-era-intunecata/",
        "tag/bazele-conceptiei-sociale-ale-bisericii-ortodoxe/",
        "tag/omul-viitorului/",
        "tag/probleme-fundamentale-de-bioetica/",
        "tag/bioethica-militans/",
        "tag/medicina-si-crestinism/",
    ]
    start_urls = []
    for k in keywords:
        start_urls.append(start_url_template.format(k))

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
            links_to_follow # The links to the individual articles
            click_button_selector # The links to the button rendering more articles
            click_button_selector_STOP # The indicator-class of the last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
    '''
    links_to_follow_XPATH = '//div[contains(@class,"tdb-category-loop-posts")]//h3/a[@href]'
    click_button_selector_XPATH = '//a[contains(@class, "td_ajax_load_more")]' # xpath selector for the "Load more" button
    click_button_selector_STOP_XPATH = None # If this is not relevant, set this query to None
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_XPATH = '//h1/text()'
    publication_date_XPATH = '//time/text()'
    author_XPATH = '//article//a[contains(@class, "tdb-author-name")]/text()'
    article_categories_XPATH = None
    article_text_XPATH = '//article//div[contains(@class, "tdb-block-inner")]//p//text() | //div[contains(@class, "su-heading-inner")]/text()'
    image_links_XPATH = '//article//img/@src'
    embedded_media_links_XPATH = '//a[contains(@href, "youtube.com")]/@href'
    links_in_text_XPATH = '//article//a[starts-with(@href, "http") and not(contains(@href, "culturavietii.ro")) and not(descendant::img)]/@href'
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_clicks=None):
        """Initializes the spider and sets optional max_clicks limit."""
        super().__init__()
        Dynamic_Click_Scrapy.initialize(self, max_clicks) # Initializes clicking setup

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Click_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Dynamic_Click_Scrapy.load_existing_links(self.save_path) # See doc string
    
    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Collects all article links dynamically using Playwright by clicking "Load more" button cumulatively
        url = response.url
        links = yield deferToThread(
            asyncio.run,
            Dynamic_Click_Scrapy.click_and_collect_links(
                url,
                click_button_selector=self.click_button_selector_XPATH,
                links_selector=self.links_to_follow_XPATH.replace('::attr(href)', ''), # Adjusts selector for link elements
                max_clicks=self.max_clicks,
                wait_time=2000,
                # wait_time=5000, # default value = 2000, increase if needed
                timeout_time=100000, # default value = 30000, increase if needed
                stop_when_button_has_class=self.click_button_selector_STOP_XPATH,
                # pagination_navigates = True, # default value = False, set to true if new articles "overwrite" older ones in the DOM
                incremental_retries = 10000 # default value = 5, increase if needed
            )
        )
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
                Dynamic_Click_Scrapy.fetch_page_with_playwright(
                    link,
                    timeout_time=100000, # default value = 60000, increase if needed
                    # wait_time=5000 # default value = 2000, increase if needed
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
        article_title = response.xpath(self.article_title_XPATH).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).get()
        # Extract 'author' 
        author = response.xpath(self.author_XPATH).get()
        if author: # Only cleans existing articles
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract 'article_categories' 
        article_categories = self.article_categories_XPATH
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.xpath(self.embedded_media_links_XPATH).getall()
        # Extract 'links_in_text' 
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
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