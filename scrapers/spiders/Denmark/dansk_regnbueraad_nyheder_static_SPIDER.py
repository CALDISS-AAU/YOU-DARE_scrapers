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
        scrapy crawl dansk_regnbueraad_nyheder_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/Denmark/dansk_regnbueraad_nyheder_SPIDER # If the folder does not yet exist
        nohup scrapy crawl dansk_regnbueraad_nyheder_SPIDER -a max_pages=1 > ./data/Denmark/dansk_regnbueraad_nyheder_SPIDER/dansk_regnbueraad_nyheder_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'dansk_regnbueraad_nyheder_SPIDER' # Spider name - must be unique within given project
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Dansk Regnbueråd' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.danskregnbueraad.dk/nyt',
        ] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    next_page_CSS = '.older a::attr(href)'
    
    article_block_CSS = 'article'
    article_links_CSS = 'h1 a::attr(href)'
    article_title_CSS = 'h1 a::text'
    publication_date_CSS = 'time a::text'
    author_CSS = '.entry-header-author a::text'
    article_categories_CSS = None
    article_text_XPATH = ".//div[contains(@class, 'sqs-block-content')]//*[not(self::figcaption or ancestor::figcaption)]/text()"
    image_links_CSS = 'img::attr(src)'
    embedded_media_links_CSS = 'iframe::attr(src)'
    links_in_text_CSS = '.sqs-block-content a::attr(href)'
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

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    async def start(self): # Can't be renamed
        """ Parses all urls from start_url to the parse_front function. """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse, # Calls parse on each url
                meta={'current_page': 1} # Information sent to parse
            )

    def parse(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request
        articles = response.css(self.article_block_CSS)
        
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source

        for article in articles:
            # Extract 'article_link'
            article_link = article.css(self.article_links_CSS).get()
            article_link = response.urljoin(article_link)
            if article_link in self.existing_links: # If the article has already been scraped then exit this function - hence nothing is scraped
                self.logger.info(f"Skipping duplicate article: {article_link}")
                continue

            # items = self.items # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function

            # Extract 'article_title'
            article_title = article.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
            # Extract 'publication_date' 
            publication_date = article.css(self.publication_date_CSS).get()
            # Extract author
            author_clean = article.css(self.author_CSS).get()
            # Extract 'article_categories' 
            article_categories = self.article_categories_CSS
            # Extract 'article_text'
            article_text_bits = article.xpath(self.article_text_XPATH).getall() 
            article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
            # Extract 'image_links' and 'image_captions' 
            image_links_raw = article.css(self.image_links_CSS).getall()
            image_links = [response.urljoin(src) for src in image_links_raw]
            # Extract 'embedded_media_links' 
            embedded_media_links = article.css(self.embedded_media_links_CSS).getall()
            # Extract 'links_in_text' 
            links_in_text_raw = article.css(self.links_in_text_CSS).getall()
            links_in_text = [response.urljoin(link) for link in links_in_text_raw]
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
            items['article_HTML'] = article_HTML

            self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

            yield items # Writes the items to the FEEDS function in the settings.py file hence saving them

        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse) # Follows the next page - See doc string
        if next_page_url: # Only go to the nex page if the page is not None
            yield next_page_url