### IMPORTS ###
# External imports #
import scrapy
from datetime import datetime
from urllib.parse import urljoin
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.static_scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl samnytt_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/Sweden/samnytt_SPIDER # If the folder does not yet exist
        nohup scrapy crawl samnytt_SPIDER -a max_pages=1 > ./data/Sweden/samnytt_SPIDER/samnytt_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'samnytt_SPIDER' # Spider name - must be unique within given project
    region = 'Sweden' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Samnytt' # The base source name - each keyword will be appended to this
    start_urls = [
        'https://samnytt.se/category/ledare',
        'https://samnytt.se/category/debatt',
        'https://samnytt.se/category/kronikor'
    ]  

    custom_settings = {
        'ROBOTSTXT_OBEY': False
    }

    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_CSS') and 'some_xpath' must use response.xpath('some_XPATH')
        For clarrification:
            Front page referes to the first site the spider encounters after following the start_urls
            Article page referes to the site of each individual article
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            links_to_follow # The links to the individual articles
            next_page # The links to the next page (if the next page is fetchable)
    '''
    links_to_follow_XPATH = '//section/a/@href'
    next_page_XPATH = '//a[not(contains(@class, "pointer-events-none")) and button[normalize-space(text())="Äldre"]]/@href'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1::text'
    article_title_backup_CSS = 'div.text-3xl.font-extrabold::text'
    publication_date_XPATH = '//span[contains(text(), "Publicerad")]/text()'
    author_XPATH = '//div[contains(@class, "items-center")]//span[contains(@class, "ml-4") and contains(@class, "text-lg")]/text()'
    article_categories_CSS = '.mb-3\.5 a::text'
    article_text_bits_XPATH = '''
        //div[contains(@class, "post-content")]//*[self::p or self::h2 or self::h3 or self::blockquote]
        [not(.//strong[starts-with(normalize-space(), "LÄS ÄVEN:")])]
        //text()
        '''.strip()
    image_links_CSS = 'figure img::attr(src)'
    embedded_media_links_CSS = 'figure iframe::attr(src)'
    links_in_text_XPATH = '''
        //div[contains(@class, "post-content")]//*[self::p or self::h2 or self::h3 or self::blockquote]
        [not(.//strong[starts-with(normalize-space(), "LÄS ÄVEN:")])]
        //a/@href
        '''.strip()
    other_items_CSS = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_pages=None):
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Static_Scrapy.initialize(self, max_pages) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(StaticSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Static_Scrapy.load_existing_links(self.save_file) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front, # Calls parse_front on each url
                meta={'current_page': 1} # Information sent to parse_front
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request
        ''' Some articke_links (or links_to_follow) on this website differs in domain so that some links can only be found on the '.se' domain (https://samnytt.se/artikel/foo),
            while some links can be found on both the '.se' and the '.nu' domain (https://samnytt.se/artikel/foo and https://samnytt.nu/artikel/foo').
            Some extra functionality where all links are 'forced' to be on the '.se' domain
            has therefore been implemented in order to standardise article_links and avoid unintended duplicate scrapes.
        '''
        # Finds and follows article links 
        raw_links = response.xpath(self.links_to_follow_XPATH).getall()

        # Deduplicate based on relative path and generate .se-based full URLs
        def normalize_href(href):
            """Returns clean relative path for deduplication"""
            if href.startswith('http'):
                return urlparse(href).path
            return href

        # Build unique set of paths and map them to samnytt.se
        path_seen = set()
        article_links = []
        for href in raw_links:
            path = normalize_href(href)
            if path not in path_seen:
                path_seen.add(path)
                full_url = urljoin('https://samnytt.se', path) 
                article_links.append(full_url)
        
        for link in article_links:
            if link in self.existing_links: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article, # Calls parse_article on each link
                meta={
                    'article_link': link, # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                },
                dont_filter=True  # Prevents Scrapy from skipping duplicates between .se/.nu
            )

        # Goes to next page if possible
        next_page = response.xpath(self.next_page_XPATH).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the next page if the page is not None
            yield next_page_url

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link'] 
        if article_link in self.existing_links: # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get()
        # Fallback for articles without <h1>, using div with typical title classes
        if not article_title:
            article_title = response.css(self.article_title_backup_CSS).get()
        # Clean if found
        if article_title:
            article_title_clean = General_Functions.clean_text(article_title)
        else:
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).getall()[1]
        # Extract 'author' 
        author = response.xpath(self.author_XPATH).get()
        if author:
            author_clean = General_Functions.clean_text(author)
        else:
            author_clean = author
        # Extract 'article_categories' 
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
        # Extract 'other_items' 
        other_items = self.other_items_CSS
        # Extract 'article_HTML'
        article_HTML = response.text

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

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them
