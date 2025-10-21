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

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl template_dynamic_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''
 
### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'cultura_vietii_SPIDER' # Spider name - must be unique within given project
    region = 'Romania' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Cultura Vietii' # The source of the articles - NOT the author!
    start_urls = ['https://www.culturavietii.ro/?s={}'] # The url where the content to be scraped is found - can be multiple urls IF THE xpath/XPATH IS IDENTICAL!
    keyword = [
    'sexualitate','demografie',
    'esential','bunastarea-familiei',
    'educatie','politica-legislatie',
    '/tag/video','/tag/restabilirea-ordinii-naturale/',
    '/tag/demografia-este-destin/',
    '/tag/casatoria/','/tag/Mituri-despre-avort/',
    'bioetica','reproducere-asistata',
    'stiinte-juridice-si-filosofie','religie',
    '/tag/noua-era-intunecata/','/tag/bazele-conceptiei-sociale-ale-bisericii-ortodoxe/',
    '/tag/omul-viitorului/','/tag/probleme-fundamentale-de-bioetica/',
    '/tag/bioethica-militans/','/tag/medicina-si-crestinism/'
    ]  # List of search keywords

    ## HTML directions ##
    ''' These can be both xpath and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_xpath' must use response.xpath('some_xpath') and 'some_xpath' must use response.xpath('some_xpath')
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' xpath or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            links_to_follow # The links to the individual articles
            next_page # The links to the next page
        How to pass information from the parse_front function to the parse_article function will be described in greater detail later on.
    '''
    links_to_follow_XPATH = '//div[contains(@class,"tdb-category-loop-posts")]//h3/a[@href]'
    click_button_selector_XPATH = '//a[contains(@class, "td_ajax_load_more")]' # xpath selector for the "Load more" button
    click_button_selector_STOP_xpath = None # xpath for last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
                                                # If this is not relevant, delete this query and delete the argument stop_when_button_has_class in the 
                                                # Dynamic_Scrapy_Click.fetch_links_with_clicking function (inside parse), or set it to it's default value - None
    # FROM THE ARTICLE PAGE!!!
    ''' xpath or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_XPATH = '//h1/text()'
    author_XPATH = '//article//a[contains(@class, "tdb-author-name")]/text()'
    publication_date_XPATH = '//time/text()'
    article_text_bits_XPATH = '//article//div[contains(@class, "tdb-block-inner")]//p//text()'
    article_header_bits_XPATH = '//div[contains(@class, "su-heading-inner")]/text()'
    image_links_XPATH = '//article//img/@src'
    external_links_XPATH = '//article//a[starts-with(@href, "http") and not(contains(@href, "culturavietii.ro")) and not(descendant::img)]/@href'
    article_HTML_bits_XPATH = '//article/div/div/div/div/div/div/div/div'
    embedded_media_links_XPATH = '//a[contains(@href, "youtube.com")]/@href'
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
    
    def start_requests(self):
        for keyword in self.keyword:
            if keyword.startswith("/tag/"):
                url = f"https://www.culturavietii.ro{keyword}"
            else:
                url = self.start_urls[0].format(keyword)
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'keyword': keyword,
                'max_clicks': self.max_pages or 999}
            )

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response):
        """Handles dynamic scraping after keyword/tag URL loads."""
        url = response.url
        keyword = response.meta.get("keyword", "<unknown>")

        links = yield deferToThread(
            asyncio.run,
            Dynamic_Scrapy_Click.fetch_links_with_clicking_xpath(
                url,
                click_button_selector=self.click_button_selector_XPATH,
                links_selector=self.links_to_follow_XPATH.replace('::attr(href)', ''),
                max_clicks = response.meta.get('max_clicks', 9999),
                wait_time=5000,
                stop_when_button_has_class=self.click_button_selector_STOP_xpath
            )
        )
        links = [urljoin(url, l) for l in links if l]

        self.logger.info(f"[{keyword}] Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"[{keyword}] Article link: {link}")

        collected_items = []
        for link in links:
            if link in self.existing_data:
                self.logger.info(f"[{keyword}] Skipping duplicate: {link}")
                continue

            article_page = yield deferToThread(asyncio.run, Dynamic_Scrapy_Click.fetch_page_with_playwright(link))
            article_sel = Selector(text=article_page)

            item = self.parse_article(article_sel, link, keyword)
            if item:
                collected_items.append(item)

        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

    def parse_article(self, response, article_link, keyword): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        items = ScrapersItem() # Makes the items from items.py accessable within this function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_title'
        article_title = response.xpath(self.article_title_XPATH).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'author' 
        author = response.xpath(self.author_XPATH).get()
        if author: # Only cleans existing articles
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).get()
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        article_header_bits = response.xpath(self.article_header_bits_XPATH).getall()
        article_header_clean = General_Functions.join_and_clean(article_header_bits)
        article_text_clean = ' '.join([article_header_clean, article_text_clean]).strip()
        # Extract 'image_links' 
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Match images with their relevant caption
        # Extract 'external_links' 
        external_links = response.xpath(self.external_links_XPATH).getall()
        # Extract 'youtube_links' 
        embedded_media_links = response.xpath(self.embedded_media_links_XPATH).getall()
        # Extract 'article_HTML'
        article_HTML = response.get()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['keyword'] = keyword
        items['source'] = f"{self.source} — {keyword}"
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_media_links
        items['external_links'] = external_links
        items['article_HTML'] = article_HTML

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse