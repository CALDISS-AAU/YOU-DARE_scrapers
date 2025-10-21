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
        scrapy crawl legio_hungaria_static_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'legio_hungaria_static_SPIDER' # Spider name - must be unique within given project
    region = 'Hungary' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source_base = 'Legio Hungaria' # The base source name - each keyword will be appended to this
    search_template = 'https://legiohungaria.org/'  # Template for keyword search URLs
    #keywords = []   # List of search keywords - customize this as needed

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

    #FROM FRONT PAGE
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    links_to_follow_CSS = '.title.is-3::attr(href)'
    next_page_CSS = '.pagination-next::attr(href)'
    publication_date_CSS = '.media .media-content time::text'

    #FROM ARTICLE PAGE
    article_title_CSS =  '.title.is-1::text'
    author_CSS = 'Légió Hungária'
    article_text_bits_CSS = '.content.postcontent p *::text'
    image_links_CSS = '.content.postcontent figure img::attr(src), .content.postcontent img::attr(src)'    #https://legiohungaria.org/ as its PREFIX
    links_in_text_CSS = '.content.postcontent p a::attr(href)'
    article_HTML_bits_CSS = '.content.postcontent'
    embedded_media_links_CSS = 'iframe::attr(src)'
    article_tags_CSS = '.tags a::text'
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
        self.existing_links = Static_Scrapy.load_existing_links(self.save_file, self.logger) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def start_requests(self): # Can't be renamed
        """Generates requests for all keywords and sends them to parse_front."""
        yield scrapy.Request(
            url=self.search_template,
            callback=self.parse_front, # Calls parse_front on each keyword search URL
            meta={'current_page': 1, 'keyword': ''} # Sends both page and keyword info forward
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page = response.meta['current_page'] # Saves 'current_page' from start_request
        keyword = response.meta['keyword'] # Saves keyword used for this search page

        # Finds and follows article links 
        links = response.css(self.links_to_follow_CSS).getall() # Gets all article links 
        dates = response.css(self.publication_date_CSS).getall() # Get all dates

        if len(dates) != len(links):
            self.logger.info(f"Mismatch of number of articles {len(links)} vs number of publication dates {len(dates)}.")



        for link, pub_date in zip (links, dates):
            if link in self.existing_links: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article, # Calls parse_article on each link
                meta={
                    'article_link': link, # Sends the link to parse_article so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                    'keyword': keyword,  # Passes keyword through to be used for source naming
                    'publication_date' : pub_date
                }
            )

        # Goes to next page if possible
        next_page = response.css(self.next_page_CSS).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the next page if the page is not None
            next_page_url.meta['keyword'] = keyword  # Preserve keyword when paginating
            yield next_page_url

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = self.items # Makes the items from items.py accessable within this function - Use self.variable to access variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.css('meta[property="og:url"]::attr(content)').get() #response.meta['article_link'] 
        # Extract 'keyword' to use for source
        keyword = response.meta['keyword']
        source = f'{self.source_base} {keyword}'

        if article_link in self.existing_links: # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        # Extract 'publication_date' 
        #publication_date = response.css(self.publication_date_CSS).get()
        # Extract 'author' 
        #author = response.css(self.author_CSS).get()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        #embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text' 
        links_in_text = response.css(self.links_in_text_CSS).getall()
        # Extract 'article_categories' 
        #article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'other_items' 
        #other_items = self.other_items_CSS
        article_HTML = response.text
        article_categories = response.css(self.article_tags_CSS).getall()
        embedded_med = response.css(self.embedded_media_links_CSS).getall()
        publication_date = response.meta['publication_date']
        

        # Assign variables to items here - the items below are minumum requirenments! 
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = 'Legio Hungaria'
        items['article_link'] = article_link
        items['author'] = "No author"

        items['article_title'] = article_title_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['links_in_text'] = links_in_text
        items['article_categories'] = article_categories
        items['embedded_media_links'] = embedded_med
        items['article_HTML'] = article_HTML  # Raw HTML of the article
        items['other_items'] = 'None'


        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them
