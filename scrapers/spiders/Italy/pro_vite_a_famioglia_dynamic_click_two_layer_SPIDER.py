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
from ...functions.general_functions import General_Functions  # Custom shared functions

''' THIS SPIDER IS READY TO RUN USING PLAYWRIGHT!
    To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl pro_vita_e_famiglia_playwright_SPIDER -a max_pages=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class DynamicSpider(scrapy.Spider):  # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'pro_vita_e_famiglia_playwright_SPIDER'  # Spider name - must be unique within given project
    region = 'Italy'  # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'pro vita e famiglia'  # The source of the articles - NOT the author!
    start_urls = ['https://www.provitaefamiglia.it/petizione']  # The url where the content to be scraped is found

    ## HTML directions ##
    # QUERIES FROM THE FRONT PAGE!!!
    # A = 'full-width-post'
    # B = 'three-column-post'
    # links_to_follow_XPATH = f"//section[(contains(concat(' ', normalize-space(@class), ' '), ' {A} ') or normalize-space(@class) = '{B}')]//a[@href]"
    # publication_date_XPATH = f".//p[contains(@class, '{A}-date') or contains(@class, '{B}-date')]" # Relative to the links to follow, since the publication dates are nested within the <a>'s
    container_XPATH = "//section[contains(@class, 'full-width-post')] | //div[starts-with(@class, 'col-lg-4') and contains(@class, 'wow') and not(ancestor::section[contains(@class, 'related-articles')])]"
    links_to_follow_XPATH = ".//a"
    publication_date_XPATH = ".//p[contains(@class, 'post-date') or contains(@class, 'three-column-post-date') or contains(@class, 'full-width-post-date')]"
    click_button_XPATH = "//a[contains(@class, 'page-link') and contains(normalize-space(.), 'Succ')]" # XPath selector for the "Load more" or next page button
    stop_button_XPATH = "//li[contains(@class, 'disabled')]/a[contains(@class, 'page-link') and contains(normalize-space(.), 'Succ')]" # Selector that indicates no further pages to load

    # FROM THE ARTICLE PAGE!!!
    article_title_CSS = 'h1.petition-infos--title *::text'
    article_text_bits_XPATH = '''
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
    author_CSS = 'none availabe'
    # article_HTML_CSS = ''
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
    embedded_media_links_CSS = []
    article_categories_CSS = 'none available'
    other_items_CSS = 'nothing else'


    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2,
        "AUTOTHROTTLE_MAX_DELAY": 10,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }

    def __init__(self, max_pages=None):
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Dynamic_Scrapy_Click.initialize(self, max_pages)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Creates the spider instance from crawler and sets it up."""
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy_Click.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy_Click.load_existing_links(self.save_path)

    @inlineCallbacks
    def parse(self, response):  # Can't be renamed
        # Collects all article links dynamically using Playwright by clicking "Load more" or next button cumulatively
        url = response.url
        article_meta = yield deferToThread(
            asyncio.run,
            Dynamic_Scrapy_Click.fetch_links_and_publication_date_with_clicking(
                url=response.url,
                container_selector=self.container_XPATH,
                link_selector=self.links_to_follow_XPATH,
                publication_date_selector=self.publication_date_XPATH,
                click_button_selector=self.click_button_XPATH,
                max_clicks=self.max_pages,
                wait_time=2000,
                stop_when_button_has_class=self.stop_button_XPATH
            )
        )
        self.logger.info(f"Found {len(article_meta)} article entries on {url}")

        for entry in article_meta:
            self.logger.debug(f"Article link: {entry['link']} | Date: {entry['publication_date']}")

        collected_items = []
        for entry in article_meta:
            link = entry["link"]
            pub_date = entry["publication_date"]

            if link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            article_page = yield deferToThread(asyncio.run, Dynamic_Scrapy_Click.fetch_page_with_playwright(link))
            article_sel = Selector(text=article_page)
            item = self.parse_article(article_sel, link, pub_date)

            if item:
                item["publication_date"] = pub_date  # Inject frontpage pub date into item
                collected_items.append(item)

        returnValue(collected_items)

    def parse_article(self, response, article_link, publication_date):
        items = ScrapersItem()
        timestamp = datetime.now().strftime('%Y-%m-%d')
        article_title = response.css(self.article_title_CSS).get()
        article_title_clean = General_Functions.clean_text(article_title) if article_title else None
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits)
        image_links_raw = response.css(self.image_links_CSS).getall()
        image_links = [General_Functions.safe_urljoin(article_link, src) for src in image_links_raw]
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
        # embedded_media_links = response.css(self.embedded_media_links_CSS).getall()


        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['author'] = self.author_CSS
        items['links_in_text'] = links_in_text
        items['embedded_media_links'] = self.embedded_media_links_CSS
        items['article_categories'] = self.article_categories_CSS
        items['other_items'] = self.other_items_CSS
        items['article_HTML'] = response.get()  # Raw HTML of the article

        self.logger.info(f"Scraped article: {article_title_clean} ({article_link})")
        self.existing_data.add(article_link)

        return items
