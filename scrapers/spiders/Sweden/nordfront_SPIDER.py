### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from datetime import datetime
from urllib.parse import urljoin
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Dynamic_Scrapy_Click  # Custom shared click functions
from ...functions.scrapy_functions import DynamicClickAndWait # Custom click with wait
from ...functions.general_functions import General_Functions  # Custom shared functions

''' THIS SPIDER IS NOT ABLE TO RUN!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl template_dynamic_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'nordfront_SWE_SPIDER' # Spider name - must be unique within given project
    region = 'Sweden' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'nordfront' # The source of the articles - NOT the author!
    start_urls = ['https://nordfront.se/'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

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
    links_to_follow_XPATH = '//*[@id="post-collections"]//a[contains(@class, "item") and @data-status="publish" and .//h1]'
    click_button_selector_XPATH = "//button[@id='load-more-articles']" # CSS selector for the "Load more" button
    # click_button_selector_STOP_XPATH = '//button[@id="load-more-articles" and @current-page="269"]' # CSS for last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
                                                # If this is not relevant, delete this query and delete the argument stop_when_button_has_class in the 
                                                # Dynamic_Scrapy_Click.fetch_links_with_clicking function (inside parse), or set it to it's default value - None
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
        These can obviously be omittet if all relevant information can be scraped from the front page, in which case parse_article should be disabled.
    '''
    article_title_XPATH = '//h1[@id="article-h1"]/span[@class="fontmagic-inner"]/text()'
    author_XPATH = '//li[@class="author"]/text()[2]'
    publication_date_XPATH = '//li[@class="published"]/text()[2]'
    article_text_bits_XPATH = '//div[@class="text"]//text()'
    article_categories_XPATH = '//footer[@class="info-tags"]//li//a/text()'
    image_links_XPATH = '//figure[@class="complex-media"]//img/@mcpp_source_src'
    external_links_XPATH = '//article[@id="main-article"]//div[@class="text"]//a[@href]/@href'
    article_HTML_bits_XPATH = '//article[@id="main-article"]'
    youtube_XPATH = '//article//iframe[contains(@src, "youtube.com")]/@src'
    other_items_XPATH = 'None'

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None, max_pages=None):
        """Initializes the spider and sets optional max_scrolls and max_pages limit."""
        super().__init__()
        Dynamic_Scrapy_Click.initialize(self, max_pages) # Initializes clicking setup

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy_Click.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy_Click.load_existing_links(self.save_path) # See doc string

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response): # Can't be renamed
        # Collects all article links dynamically using Playwright by clicking "Load more" button cumulatively
        url = response.url
        links = yield deferToThread(
            asyncio.run,
            DynamicClickAndWait.click_and_collect_links(
                url,
                click_button_selector=self.click_button_selector_XPATH,
                links_selector=self.links_to_follow_XPATH.replace('::attr(href)', ''), # Adjusts selector for link elements
                max_clicks=self.max_pages,
                wait_time=5000,
                stop_when_button_has_class=None
            )
        )
        links = [urljoin(url, l) for l in links if l] # Ensures proper joining and non-None links

        self.logger.info(f"Found {len(links)} article links on {url}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        collected_items = []
        
        for link in links:
            if link in self.existing_data: # Only scrapes information for articles that have not yet been scraped
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            # Fetch each article manually
            article_page = yield deferToThread(asyncio.run, Dynamic_Scrapy_Click.fetch_page_with_playwright(link))
            article_sel = Selector(text=article_page)

            # Parse and yield the article
            items = self.parse_article(article_sel, link) # Goes to each article and scrapes relevant information
            if items: # If any information has been scraped the data is added to 'collected_items'
                collected_items.append(item)
        
        returnValue(collected_items) # MUST!!! be 'returnValue' since scrapy can't catch data from '@inlineCallbacks' using 'yield'!!!

    def parse_article(self, response, article_link): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE!
        items = ScrapersItem() # Makes the items from items.py accessable within this function
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_title'
        article_title = response.xpath(self.article_title_XPATH).get() # .get() returns only the first element. Use .getall() to return a list of all elements if more than one element is expected
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'author' 
        author = response.xpath(self.author_XPATH).get()
        if author: # Only cleans existing articles
            author_clean = General_Functions.clean_text(author) # Cleans the text - See doc string
        else:
            author_clean = author
        # Extract 'publication_date'
        publication_date = response.xpath(self.publication_date_XPATH).get()
        publication_date_clean = publication_date.strip() if publication_date else None
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall() 
        article_text_clean = General_Functions.join_and_clean(article_text_bits) # Joins and cleans all text elements - See doc string
        article_categories = response.xpath(self.article_categories_XPATH).getall()
        # Extract 'image_links' 
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Extratc 'image_captions' 
        # image_captions = response.xpath(self.image_captions_XPATH).getall()
        # Match images with their relevant caption
        # fixed_captions = Dynamic_Scrapy_Click.match_images_with_captions(
        #     image_links=image_links,
        #     captioned_image_srcs=image_links
        # )
        # Extract 'external_links' 
        external_links = response.xpath(self.smr_external_links_XPATH).getall()
        # Extract 'youtube_links' 
        youtube_links = response.xpath(self.smr_youtube_XPATH).getall()
        # Extract 'article_HTML'
        article_HTML = response.get()
        article_HTML_bits = response.xpath(self.article_HTML_bits_XPATH).getall()
        article_HTML = ' '.join(article_HTML_bits).strip()

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date_clean
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['article_categories'] = article_categories
        items['author'] = author_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = youtube_links
        items['links_in_text'] = external_links
        items['article_HTML'] = article_HTML
        items['other_items'] = self.other_items_XPATH

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_data.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse