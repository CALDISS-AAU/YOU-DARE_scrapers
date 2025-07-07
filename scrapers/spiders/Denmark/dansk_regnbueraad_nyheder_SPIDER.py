### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl dansk_regnbueraad_nyheder_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'dansk_regnbueraad_nyheder_SPIDER' # Spider name - must be unique within given project
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Dansk Regnbueråd' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.danskregnbueraad.dk/nyt',
        ] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    items = ScrapersItem() # Makes the items from items.py accessable within this spider

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
    article_CSS = 'article'
    article_links_CSS = 'h1 a::attr(href)'
    article_title_CSS = 'h1 a::text'
    author_CSS = '.entry-header-author a::text'
    publication_date_CSS = 'time a::text'
    article_text_bits_XPATH = ".//div[contains(@class, 'sqs-block-content')]//*[not(self::figcaption or ancestor::figcaption)]/text()"
    figure_block_CSS = 'figure'
    image_links_CSS = 'img::attr(src)'
    image_captions_html_CSS = 'figcaption'
    image_captions_CSS = 'figcaption *::text'
    youtube_CSS = 'iframe::attr(src)'
    external_links_CSS = '.sqs-block-content a::attr(href)'
    article_HTML_bits_XPATH = ".//div[contains(@class, 'sqs-block-content')]//*[not(self::figcaption or ancestor::figcaption)]"
    next_page_CSS = '.older a::attr(href)'

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
        self.existing_data = Static_Scrapy.load_existing_links(self.save_file, self.logger) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def start_requests(self): # Can't be renamed
        """ Parses all urls from start_url to the parse_front function. """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse, # Calls parse on each url
                meta={'current_page': 1} # Information sent to parse
            )

    def parse(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request

        items = self.items # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract articles
        articles = response.css(self.article_CSS)

        for article in articles:
            # Extract 'article_link'
            article_link = article.css(self.article_links_CSS).get()
            article_link = response.urljoin(article_link)
            
            if article_link in self.existing_data: # If the article has already been scraped then exit this function - hence nothing is scraped
                self.logger.info(f"Skipping duplicate article: {article_link}")
                continue

            # Extract 'article_title'
            article_title = article.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
            # Extract author
            author = article.css(self.author_CSS).get()
            # Extract 'publication_date' 
            publication_date = article.css(self.publication_date_CSS).get()
            # Extract 'article_text'
            article_text_bits = article.xpath(self.article_text_bits_XPATH).getall() 
            article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
            # Extract 'image_links' and 'image_captions' 
            image_links_raw = article.css(self.image_links_CSS).getall()
            image_links = [response.urljoin(src) for src in image_links_raw]
            # Find which images are wrapped in captioned divs
            image_captions = Static_Scrapy.extract_captions_from_figures(
                article=article,
                image_links=image_links,
                figure_selector=self.figure_block_CSS,
                image_selector=self.image_links_CSS,
                caption_selector=self.image_captions_html_CSS
            )

            # Extract 'youtube_links' 
            youtube_links = article.css(self.youtube_CSS).getall()
            # Extract 'external_links' 
            external_links_raw = article.css(self.external_links_CSS).getall()
            external_links = [response.urljoin(link) for link in external_links_raw]
            # Extract 'article_HTML' 
            article_HTML_bits = article.xpath(self.article_HTML_bits_XPATH).getall()
            article_HTML = ' '.join(article_HTML_bits).strip()

            # Assign variables to items here - the items below are minumum requirenments! 
            # items['item_within_items.py']
            items['scrape_date'] = timestamp # Works
            items['publication_date'] = publication_date # Works
            items['source'] = self.source # Works
            items['author'] = author # Works
            items['article_link'] = article_link # Works
            items['article_title'] = article_title_clean # Works
            items['article_text'] = article_text_clean # Works
            items['image_links'] = image_links # Works
            items['image_captions'] = image_captions # Works
            items['youtube_links'] = youtube_links # Works
            items['external_links'] = external_links # Works
            items['article_HTML'] = article_HTML # Retract and assign the full HTML including image placements, image captions, links etc.

            self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

            yield items # Writes the items to the FEEDS function in the settings.py file hence saving them

        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse) # Follows the next page - See doc string
        if next_page_url: # Only go to the nex page if the page is not None
            yield next_page_url