### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl homeland_party_news_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'homeland_party_news_SPIDER' # Spider name - must be unique within given project
    region = 'United_Kingdom' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Homeland party - news' # The source of the articles - NOT the author!
    start_urls = ['https://homelandparty.org/news/category/news/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    article_CSS = '.post-content'
    links_to_follow_CSS = '.read-more a::attr(href)'
    author_CSS = '.posted-by *::text'
    publication_date_CSS = '.posted-on *::text'
    article_categories_CSS = '.tags-links a::text'

    next_page_CSS = 'a.next.page-numbers::attr(href)'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_CSS = 'h1.entry-title::text'
    article_text_bits_CSS = '.entry-content h2 *::text, .entry-content p *::text'
    image_links_CSS = '.entry-content img::attr(src)'
    external_links_CSS = '.entry-content h5 a::attr(href), .entry-content p a::attr(href)'
    embedded_media_CSS = '.entry-content iframe::attr(src)'
    # ... other queries

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
                callback=self.parse_front, # Calls parse_front on each url
                meta={'current_page': 1} # Information sent to parse_front
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request
        articles = response.css(self.article_CSS)

        # Finds and follows article links, while extracting additional information
        for article in articles:
            link = article.css(self.links_to_follow_CSS).get()
            authors = article.css(self.author_CSS).getall()
            pub_date = article.css(self.publication_date_CSS).get()
            categories = article.css(self.article_categories_CSS).getall()

            if link in self.existing_data: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article, # Calls parse_article on each link
                meta={
                    'article_link': link, # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                    'authors': authors,
                    'publication_date': pub_date,
                    'article_categories': categories
                }
            )

        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the nex page if the page is not None
            yield next_page_url

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = ScrapersItem() # Makes the items from items.py accessable within this function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link']
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).getall() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.join_and_clean(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # # Extract 'author' 
        authors = response.meta['authors']
        if authors:
            author_clean = General_Functions.join_and_clean(authors)
        else:
            author_clean = authors
        # Extract 'publication_date' 
        publication_date = response.meta['publication_date']
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string

        # Extract article_categories
        article_categories = response.meta['article_categories']
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        
        # Extract 'external_links' 
        external_links = response.css(self.external_links_CSS).getall()

        # Extract 'embedded media' 
        embedded_med = response.css(self.embedded_media_CSS).getall()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['author'] = author_clean
        items['article_categories'] = article_categories
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_med
        items['external_links'] = external_links
        items['other_items'] = 'None'
        items['article_HTML'] = response.text

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them
