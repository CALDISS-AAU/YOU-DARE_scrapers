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
        scrapy crawl dansk_regnbueraad_artikler_SPIDER # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/Denmark/dansk_regnbueraad_artikler_SPIDER # If the folder does not yet exist
        nohup scrapy crawl dansk_regnbueraad_artikler_SPIDER > ./data/Denmark/dansk_regnbueraad_artikler_SPIDER/dansk_regnbueraad_artikler_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'dansk_regnbueraad_artikler_SPIDER' # Spider name - must be unique within given project
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Dansk Regnbueråd' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.danskregnbueraad.dk/artikler',
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
    links_to_follow_XPATH = '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ", "abcdefghijklmnopqrstuvwxyzæøå"), "læs")]/@href' # Captuers all a blocks contianing the text 'læs artiklen' regardless of capitalisation
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_block_CSS = 'main.content'
    article_title_CSS = 'h1 *::text'
    publication_date_CSS = None 
    author_CSS = None 
    article_categories_CSS = None
    article_text_CSS = '.sqs-block-content > .sqs-html-content *::text' # All text bits from the article - these will be combined in parse_article
    image_links_CSS = 'figure img::attr(src)'
    embedded_media_links_CSS = 'span.post-content iframe::attr(src)'
    links_in_text_CSS = 'a::attr(href)'
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
    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front,
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        # Finds and follows article links 
        links = response.xpath(self.links_to_follow_XPATH).getall()
        links = [response.urljoin(l) for l in links if l] # Converts the relative URL's to absolute URL's

        # Finds and follows article links 
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

    def parse_article(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        article = response.css(self.article_block_CSS)
        
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
        article_title = article.css(self.article_title_CSS).getall() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.join_and_clean(article_title) # Joins and cleans the text bits - See doc string
        # Extract 'publication_date' 
        publication_date = self.publication_date_CSS
        # Extract 'author' 
        author_clean = self.author_CSS
        # Extract 'article_categories' 
        article_categories = self.article_categories_CSS
        # Extract 'article_text'
        article_text_bits = article.css(self.article_text_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links'
        image_links = article.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links'
        embedded_media_links = article.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text'
        all_links = response.css(self.links_in_text_CSS).getall()
        base_url = self.start_urls[0].split('/')[2]  # Extract 'www.danskregnbueraad.dk'
        excluded_domains = [
            'https://www.facebook.com/DanskRegnbueraad',
            'https://twitter.com/regnbueraad',
            'https://www.instagram.com/dansk_regnbueraad/',
            'https://www.youtube.com/@danskregnbuerad-danishrain4275'
        ]
        links_in_text = [
            link for link in all_links
            if link.startswith('http') and base_url not in link and link not in excluded_domains
        ]
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