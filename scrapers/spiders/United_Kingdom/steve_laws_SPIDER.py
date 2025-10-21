### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from datetime import datetime
from urllib.parse import urljoin 
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions


''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl mallard_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class WaybacksteveSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'steve_laws_SPIDER' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Steve Laws Report' # The source of the articles - NOT the author!
    start_urls = ['https://stevelawsreport.co.uk/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    items = ScrapersItem() # Makes the items from items.py accessable within this spider
    save_path = f"./data/{region}/{name}/data_{name}.jl"

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
    links_to_follow_XPATH = '/html/body//div/h2/a/@href'
    next_page_XPATH = '//section/div/div[2]/a[2]/@href'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_XPATH = '//h1[contains(@class, "entry-title")]/text()'
    # '//div/h1[@class="entry-title fusion-responsive-typography-calculated"]/text()'
    article_text_XPATH = '//div[contains(@class, "post-content")]//p//text()'
    publication_date_XPATH = '//article/div[3]/div/span[3]/text()'
    image_links_XPATH = '//article/div[1]/ul/li/a/img/@src'
    external_links_XPATH = '//article/div[2]/p/a/@href'
    article_categories_XPATH = '//article/div[3]/div/span[6]/a/text()'
    embedded_media_links_XPATH = '//iframe[contains(@src, "youtube.com") or contains(@src, "vimeo.com")]/@src'
    # ... other queries

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_pages=None):
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Static_Scrapy.initialize(self, max_pages) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WaybacksteveSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Static_Scrapy.load_existing_links(self.save_file, self.logger) # See doc string
        

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def start_requests(self):
        timestamp = '20250803092414'
        self.logger.info("Starting requests from Wayback Machine")

        for url in self.start_urls:
            wayback_url = f'https://web.archive.org/web/{timestamp}/{url}'
            self.logger.info(f"Generating request for: {wayback_url}")

            yield scrapy.Request(
                url=wayback_url,
                callback=self.parse_front,
                meta={'current_page': 1}
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request

        # Finds and follows article links 
        links = response.xpath(self.links_to_follow_XPATH).getall() # Gets all article links 
        for link in links:
            if link in self.existing_links: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article, # Calls parse_article on each link
                meta={
                    'article_link': link, # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                }
            )

        # Goes to next page if possible
        next_page = response.xpath(self.next_page_XPATH).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the nex page if the page is not None
            yield next_page_url

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = self.items # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link']
        
        if article_link in self.existing_links: # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        # Extract 'article_title'
        article_title = response.xpath(self.article_title_XPATH).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).get()
        # Extract 'image_links' 
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Extract 'article_HTML'
        article_HTML = response.text
        article_categories = response.xpath(self.article_categories_XPATH).getall()
        # Extract "embedded_media_links"
        embedded_media_links = response.xpath(self.embedded_media_links_XPATH).getall()
        # Extract "external_links"
        external_links = response.xpath(self.external_links_XPATH).getall()

        # Assign variables to items here - the items below are minumum requirenments! 
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title
        items['article_text'] = article_text_clean
        items['article_HTML'] = article_HTML # Retract and assign the full HTML (often article_title where not only text is retracted)
        items['categories'] = article_categories
        items['embedded_media_links'] = embedded_media_links
        items['image_links'] = image_links
        items['external_links'] = external_links

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them