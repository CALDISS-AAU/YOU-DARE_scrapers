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
        scrapy crawl la_cocarde_etudiante_wayback_SPIDER # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/France/la_cocarde_etudiante_wayback_SPIDER # If the folder does not yet exist
        nohup scrapy crawl la_cocarde_etudiante_wayback_SPIDER > ./data/France/la_cocarde_etudiante_wayback_SPIDER/la_cocarde_etudiante_wayback_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'la_cocarde_etudiante_wayback_SPIDER'
    region = 'France'
    source = 'La Cocarde Etudiante'
    start_urls = [
        'https://cocardeetudiante.com/articles/',
        'https://cocardeetudiante.com/articles/page/2/',
        'https://cocardeetudiante.com/articles/page/3/',
        'https://cocardeetudiante.com/articles/page/4/',
        'https://cocardeetudiante.com/articles/page/5/',
        'https://cocardeetudiante.com/communiques/'
    ]
    wayback_timestamp = '20240101000000'

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
    article_CSS = 'article.elementor-post'
    links_to_follow_CSS = 'a.elementor-post__thumbnail__link::attr(href)'
    publication_date_CSS = '.elementor-post-date::text'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1.elementor-heading-title.elementor-size-default::text'
    author_CSS = 'p.has-text-align-right *::text'
    article_categories_CSS = '.elementor-post-info__terms-list a.elementor-post-info__terms-list-item::text'
    article_text_CSS = '.elementor-widget-container p ::text'
    image_links_CSS = '.attachment-large.size-large.wp-image-7186.lazyloading img::attr(src)'
    embedded_media_links_CSS = None
    links_in_text_CSS = 'ul.wp-block-list li.has-small-font-size, .elementor-post-info__terms-list a.elementor-post-info__terms-list-item::attr(href)'
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_pages=None):
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Static_Scrapy.initialize(self, max_pages) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(StaticSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Static_Scrapy.load_existing_links(self.save_file) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    async def start(self):
        for url in self.start_urls:
            wayback_url = f'https://web.archive.org/web/{self.wayback_timestamp}/{url}'
            self.logger.info(f"Generating request for: {wayback_url}")

            yield scrapy.Request(
                url=wayback_url,
                callback=self.parse_front
            )

    def parse_front(self, response):
        articles = response.css(self.article_CSS)
        for article in articles:
            link = article.css(self.links_to_follow_CSS).get()
            link = response.urljoin(link)
            publication_date = article.css(self.publication_date_CSS).get()

            if link in self.existing_links:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={
                    'article_link': link, 
                    'publication_date': publication_date
                }
            )

    def parse_article(self, response):
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_link'
        article_link = response.meta['article_link']
        if article_link in self.existing_links:
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return
        # Extract 'article_title' 
        article_title = response.css(self.article_title_CSS).get()
        if article_title:
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else: 
            article_title_clean = article_title
        # Extract 'publication_date' 
        publication_date = response.meta['publication_date']
        # Extract 'author' 
        author_clean = response.css(self.author_CSS).getall()
        # Extract 'article_categories' 
        article_categories = response.css(self.article_categories_CSS).getall()
        # Extract 'article_text'
        article_text_bits = response.css(self.article_text_CSS).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links'
        embedded_media_links = self.embedded_media_links_CSS
        # Extract 'links_in_text'
        links_in_text = response.css(self.links_in_text_CSS).getall()
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