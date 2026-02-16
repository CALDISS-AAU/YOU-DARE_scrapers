### IMPORTS ###
# External imports #
import scrapy
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from datetime import datetime
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.dynamic_click_scrapy_functions import Dynamic_Click_Scrapy  # Custom shared click functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl pro_vita_e_famiglia_SPIDER -a max_clicks=x # MUST MATCH SPIDER NAME!
    where -a max_clicks=x is an optional parameter to limit the number of clicks to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/Italy/pro_vita_e_famiglia_SPIDER # If the folder does not yet exist
        nohup scrapy crawl pro_vita_e_famiglia_SPIDER -a max_clicks=0 > ./data/Italy/pro_vita_e_famiglia_SPIDER/pro_vita_e_famiglia_SPIDER_$(date +%F).log
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider):  # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'pro_vita_e_famiglia_SPIDER'  # Spider name - must be unique within given project
    region = 'Italy'  # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Pro vita e famiglia'  # The source of the articles - NOT the author!
    start_urls = ['https://www.provitaefamiglia.it/petizione']  # The url where the content to be scraped is found

    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_css') and 'some_xpath' must use response.xpath('some_xpath')
        For clarrification:
            Front page referes to the first site the spider encounters after following the start_urls
            Article page referes to the site of each individual article
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            links_to_follow # The links to the individual articles
            click_button_selector # The links to the button rendering more articles
            click_button_selector_STOP # The indicator-class of the last "next page"-button (it still has a link but is disabled so it would keep loading the same articles on the last page indefinitely)
    '''
    container_XPATH = "//section[contains(@class, 'full-width-post')] | //div[starts-with(@class, 'col-lg-4') and contains(@class, 'wow') and not(ancestor::section[contains(@class, 'related-articles')])]"
    links_to_follow_XPATH = ".//a"
    publication_date_XPATH = ".//p[contains(@class, 'post-date') or contains(@class, 'three-column-post-date') or contains(@class, 'full-width-post-date')]"
    click_button_selector_XPATH = "//a[contains(@class, 'page-link') and contains(normalize-space(.), 'Succ')]" # XPath selector for the "Load more" or next page button
    click_button_selector_STOP_XPATH = "//li[contains(@class, 'disabled')]/a[contains(@class, 'page-link') and contains(normalize-space(.), 'Succ')]" # Selector that indicates no further pages to load
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1.petition-infos--title *::text'
    author_CSS = None
    article_categories_CSS = None
    article_text_XPATH = '''
        //section[contains(@class, "petition-infos")]//text()[
        not(ancestor::*[@id="firmaPetizione"])
        and not(ancestor::*[@class="contact"])
        and not(ancestor::*[@id="message_thanks"])
        and not(ancestor::*[@id="message_gia_firmata"])
        and not(ancestor::*[contains(@class, "form_message_thanks")])
        and not(ancestor::li[@class="list-inline-item"])
        ]
    '''
    image_links_CSS = '.petition-infos--image img::attr(src)'
    embedded_media_links_CSS = None
    links_in_text_XPATH = '''
        //section[contains(@class, "petition-infos")]//a/@href[
        not(ancestor::*[@id="firmaPetizione"])
        and not(ancestor::*[@class="contact"])
        and not(ancestor::*[@id="message_thanks"])
        and not(ancestor::*[@id="message_gia_firmata"])
        and not(ancestor::*[contains(@class, "form_message_thanks")])
        and not(ancestor::li[@class="list-inline-item"])
        ]
    '''
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_clicks=None):
        """Initializes the spider and sets optional max_clicks limit."""
        super().__init__()
        Dynamic_Click_Scrapy.initialize(self, max_clicks)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Click_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_links = Dynamic_Click_Scrapy.load_existing_links(self.save_path)

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response):  # Can't be renamed
        # Collects all article links dynamically using Playwright by clicking "Load more" or next button cumulatively
        url = response.url
        article_meta = yield deferToThread(
            asyncio.run,
            Dynamic_Click_Scrapy.click_and_collect_links_and_publication_dates(
                url,
                click_button_selector=self.click_button_selector_XPATH,
                container_selector=self.container_XPATH,
                link_selector=self.links_to_follow_XPATH,
                publication_date_selector=self.publication_date_XPATH,
                max_clicks=self.max_clicks,
                # wait_time=5000, # default value = 2000, increase if needed
                stop_when_button_has_class=self.click_button_selector_STOP_XPATH,
                pagination_navigates=True, # default value = False, set to true if new articles "overwrite" older ones in the DOM
                # incremental_retries=3  # or bump this if pages are really heavy
            )
        )
        self.logger.info(f"Found {len(article_meta)} article entries on {url}")

        for entry in article_meta:
            self.logger.debug(f"Article link: {entry['link']} | Date: {entry['publication_date']}")

        collected_items = []

        for entry in article_meta:
            link = response.urljoin(entry.get("link", "") or "")
            publication_date = entry["publication_date"]
            if link in self.existing_links:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue
            article_page = yield deferToThread(
                asyncio.run, 
                Dynamic_Click_Scrapy.fetch_page_with_playwright(
                    link,
                    # timeout_time=90000, # default value = 60000, increase if needed
                    # wait_time=5000 # default value = 2000, increase if needed
                )
            )
            article_sel = Selector(text=article_page)
            
            # Parse and yield the article
            item = self.parse_article(article_sel, link, publication_date)  
            if item:
                collected_items.append(item)
        returnValue(collected_items)

    def parse_article(self, response, article_link, publication_date):
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source'
        source = self.source    
        # Extract 'article_title'
        article_title = response.css(self.article_title_CSS).get()
        if article_title: # Only cleans existing articles
            article_title_clean = General_Functions.clean_text(article_title) # Cleans the text - See doc string
        else:
            article_title_clean = article_title
        # Extract 'author' 
        author_clean = self.author_CSS
        # Extract 'article_categories' 
        article_categories = self.article_categories_CSS
        # Extract 'article_text' 
        article_text_bits = response.xpath(self.article_text_XPATH).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits)
        # Extract 'image_links' 
        image_links = response.css(self.image_links_CSS).getall()
        # Extract 'embedded_media_links' 
        embedded_media_links = self.embedded_media_links_CSS
        # Extract 'links_in_text' 
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
        # Extract 'other_items' 
        other_items = self.other_items
        # Extract 'article_HTML' 
        article_HTML = response.get()

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

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})") # Logs successful scrape

        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse