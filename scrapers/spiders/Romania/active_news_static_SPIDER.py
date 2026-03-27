### IMPORTS ###
# External imports #
import scrapy
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.static_scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl active_news_static_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./path/to/spider-data/Romania/active_news_static_SPIDER # If the folder does not yet exist
        nohup scrapy crawl active_news_static_SPIDER -a max_pages=1 > ./path/to/spider-data/Romania/active_news_static_SPIDER/active_news_static_SPIDER_$(date +%F).log
'''
''' REMOVE BEFORE PUSHING TO GIT!!
cd ./YOU-DARE/scrapers
mkdir -p ./data/Romania/active_news_static_SPIDER # If the folder does not yet exist
nohup scrapy crawl active_news_static_SPIDER -a max_pages=1 > ./data/Romania/active_news_static_SPIDER/active_news_static_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): 
    name = 'active_news_static_SPIDER' # Spider name - used when calling the spider - must be unique within given project (for uniformity use {source}_static_SPIDER)
    region = 'Romania' # Parent folder - used for folderstructure within the data folder - must be the country of the source
    source = 'Active news' # The source name - must be the actor of the website(s)
    start_urls = ['https://www.activenews.ro/stiri',
                  'https://www.activenews.ro/opinii',
                  'https://www.activenews.ro/externe',
                  'https://www.activenews.ro/ucraina',
                  'https://www.activenews.ro/razboi-in-orient',
                  'https://www.activenews.ro/alegeri-2024',
                  'https://www.activenews.ro/cultura',
                  'https://www.activenews.ro/covid',
                  'https://www.activenews.ro/covid-era-covid-si-marea-resetare-the-great-reset',
                  'https://www.activenews.ro/economie'
                ] # List of all start_urls for the spider 

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
    links_to_follow_CSS = 'article.preview a::attr(href)'
    next_page_CSS = '.paginatie a.align-right::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1.article-title *::text'
    publication_date_XPATH = "normalize-space(substring-before(substring-after(//div[@class='article-meta']//span[contains(., 'Publicat:')], ', '), ','))"
    author_CSS = '.article-meta .author a::text'
    article_categories_CSS = '.article-meta .category::text'
    article_text_CSS = '#article-read *::text'
    image_links_CSS = '#article-read img::attr(src)'
    embedded_media_links_CSS = '#article-read iframe::attr(src)'
    links_in_text_CSS = '#article-read a::attr(href)'
    other_items = None

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
        # Article counter
        self.article_count = 0

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front,
                meta={'current_page': 1}
            )

    def parse_front(self, response):  # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page']  # Saves 'current_page' from start_request
        
        # Finds and follows article links
        links = response.css(self.links_to_follow_CSS).getall()  # Gets all article links
        links = [response.urljoin(l) for l in links if l]

        seen_links = set()  # Track duplicates within this page

        for link in links:
            # Detect duplicates within the same page extraction
            if link in seen_links:
                self.logger.info(f"Duplicate link found on page {current_page}: {link}")
                continue
            seen_links.add(link)

            # Detect duplicates from previous runs / earlier crawled articles
            if link in self.existing_links:
                self.logger.info(f"Skipping previously scraped article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={
                    'article_link': link,
                }
            )

        self.logger.info(f"Page {current_page} extracted {len(links)} links ({len(seen_links)} unique)")
        
        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front)

        if next_page_url:  # Only go to the next page if the page is not None
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
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title:
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else: 
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.xpath(self.publication_date_XPATH).get()
        # Extract 'author' 
        author_clean = response.css(self.author_CSS).get()
        # Extract 'article_categories' 
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        raw_links = response.css(self.links_in_text_CSS).getall()
        links_in_text = [response.urljoin(link) for link in raw_links if link]
        # Extract 'other_items' 
        other_items = self.other_items
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
        items['article_HTML'] = None # article_HTML - removed due to the size of the scraper

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article
        # Count scraped articles
        self.article_count += 1
        self.logger.info(f"Articles scraped so far: {self.article_count}")

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them