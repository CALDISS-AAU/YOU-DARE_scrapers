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
        scrapy crawl generation_zemmour_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter to limit the number of pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/France/generation_zemmour_SPIDER # If the folder does not yet exist
        nohup scrapy crawl generation_zemmour_SPIDER -a max_pages=1 > ./data/France/generation_zemmour_SPIDER/generation_zemmour_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider):
    name = 'generation_zemmour_SPIDER' # Spider name - must be unique within given project
    region = 'France' # Parent folder - used for folderstructure within the data folder
    source = 'Generation Zemmour' # The source of the articles - NOT the author!
    start_urls = ['https://www.generation-zemmour.fr/articles']

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
    article_CSS = '.news-box' # CSS for the entire article
    links_to_follow_CSS = 'a::attr(href)'
    publication_date_CSS = '.news-date::text'

    next_page_XPATH = '//a[normalize-space(text())="Suivant"]/@href'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1.arrow::text'
    author_XPATH = '//div[@id="content"]//h4//text()'
    article_categories_CSS = None
    article_text_XPATH = '//div[@id="content"]//h2//text() | (//div[@id="content"]//h3[not(preceding::h4)]//text() | //div[@id="content"]//p[not(preceding::h4)])//text()'
    image_links_XPATH = '//*[(@id = "content")]//img/@src'
    embedded_media_links_CSS = None
    links_in_text_XPATH = '//div[@id="content"]//h2//a/@href | (//div[@id="content"]//h3[not(preceding::h4)]//a/@href | //div[@id="content"]//p[not(preceding::h4)])//a/@href | //div[@id="content"]//h4/following-sibling::p//a/@href'
    other_items = None

    def __init__(self, max_pages=None):
        super().__init__()
        Static_Scrapy.initialize(self, max_pages)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(StaticSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_links = Static_Scrapy.load_existing_links(self.save_file)

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_front,
                meta={'current_page': 1}
            )

    def parse_front(self, response):
        current_page = response.meta['current_page']
        articles = response.css(self.article_CSS)

        for article in articles:
            link = article.css(self.links_to_follow_CSS).get()
            link = response.urljoin(link)
            pub_date = article.css(self.publication_date_CSS).get()

            if link in self.existing_links:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={
                    'article_link': link,
                    'publication_date': pub_date
                }
            )


        next_page = response.xpath(self.next_page_XPATH).get()
        next_page_url = Static_Scrapy.turn_page(self, response, next_page, self.parse_front) # Follows the next page - See doc string
        if next_page_url: # Only go to the next page if the page is not None
            yield next_page_url

    def parse_article(self, response):
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_link'
        article_link = response.meta['article_link']
        if article_link in self.existing_links: # If the article has already been scraped then exit this function - hence nothing is scraped
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
        author = response.xpath(self.author_XPATH).getall()
        author_clean = General_Functions.join_and_clean(author)
        # Extract 'article_categories' 
        article_categories = self.article_categories_CSS
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_XPATH).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits)
        # Extract 'image_links'
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Extract 'embedded_media_links'
        embedded_media_links = self.embedded_media_links_CSS
        # Extract 'links_in_text'
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
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