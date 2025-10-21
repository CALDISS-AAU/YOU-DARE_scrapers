### IMPORTS ###
# External imports #
import scrapy
import re
from scrapy import signals
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl dansk_regnbueraad_artikler_SPIDER # MUST MATCH SPIDER NAME!
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'dansk_regnbueraad_artikler_SPIDER' # Spider name - must be unique within given project
    region = 'Denmark' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Dansk Regnbueråd' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.danskregnbueraad.dk/artikler',
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
    links_to_follow_XPATH = '//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ", "abcdefghijklmnopqrstuvwxyzæøå"), "læs")]/@href' # Captuers all a blocks contianing the text 'læs artiklen' regardless of capitalisation
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_CSS = 'main.content'
    title_CSS = 'h1 *::text'
    article_text_bits_CSS = '.sqs-block-content > .sqs-html-content *::text' # All text bits from the article - these will be combined in parse_article
    article_HTML_bits_CSS = '.sqs-block-content > .sqs-html-content' # All HTML bits from the article text - these will be combined in parse_article
    image_links_CSS = 'img::attr(src)'
    image_captions_CSS = 'figcaption *::text'
    # youtube_CSS = 'span.post-content iframe::attr(src)'
    external_links_CSS = 'a::attr(href)'

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
            )

    def parse_front(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!

        # Extract article links
        raw_links = response.xpath(self.links_to_follow_XPATH).getall()
        links_to_follow = [response.urljoin(link) for link in raw_links] # Converts the relative URL's to absolute URL's
        print(f'These are the links to follow: {links_to_follow}')

        # Finds and follows article links 
        for link in links_to_follow:
            if link in self.existing_data: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
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
        items = self.items # Makes the items from items.py accessable within this function - Use self.variable to acces variables defined within this spider class but outside the function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link' from parse_front
        article_link = response.meta['article_link'] 
        
        if article_link in self.existing_data: # If the article has already been scraped then exit this function - hence nothing is scraped
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        article = response.css(self.article_CSS)
        # Extract 'article_title'
        article_title = article.css(self.title_CSS).getall() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        article_title_clean = General_Functions.join_and_clean(article_title) # Joins and cleans the text bits - See doc string
        # Extract 'article_text'
        article_text_bits = article.css(self.article_text_bits_CSS).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'article_HTML'
        article_HTML_bits = article.css(self.article_HTML_bits_CSS).getall()
        article_HTML = ' '.join(article_HTML_bits).strip()
        # # Extract 'youtube_links'
        # youtube_links = response.css(self.youtube_CSS).getall()
        
        # Extract images and captions
        image_links = []
        image_captions_html = []
        captioned_image_srcs = []

        figures = article.css('figure')
        for figure in figures:
            img = figure.css(self.image_links_CSS).get()
            caption_bits = figure.css(self.image_captions_CSS).getall()
            caption = ' '.join([bit.strip() for bit in caption_bits if bit.strip()])
            if img:
                image_links.append(img)
                captioned_image_srcs.append(img)
                image_captions_html.append(caption)

        image_captions = Static_Scrapy.match_images_with_captions(
            image_links=image_links,
            image_captions_html=image_captions_html,
            captioned_image_srcs=captioned_image_srcs
        )


        # Extract and filter external hyperlinks
        all_links = response.css(self.external_links_CSS).getall()
        base_url = self.start_urls[0].split('/')[2]  # Extract 'www.danskregnbueraad.dk'
        excluded_domains = [
            'https://www.facebook.com/DanskRegnbueraad',
            'https://twitter.com/regnbueraad',
            'https://www.instagram.com/dansk_regnbueraad/',
            'https://www.youtube.com/@danskregnbuerad-danishrain4275'
        ]
        external_links = [
            link for link in all_links
            if link.startswith('http') and base_url not in link and link not in excluded_domains
        ]

        # Assign variables to items here
        # items['item_within_items.py']
        items['scrape_date'] = timestamp
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['image_captions'] = image_captions
        # items['youtube_links'] = youtube_links
        items['external_links'] = external_links
        items['article_HTML'] = article_HTML








        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them
