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
        scrapy crawl generation_zemmour_SPIDER -a max_pages=x
    where -a max_pages=x is an optional parameter
'''

### CREATING THE SPIDER ###
class GenerationZemmourSpider(scrapy.Spider):
    name = 'generation_zemmour_SPIDER' # Spider name - must be unique within given project
    region = 'France' # Parent folder - used for folderstructure within the data folder
    source = 'Generation Zemmour' # The source of the articles - NOT the author!
    start_urls = ['https://www.generation-zemmour.fr/articles']

    items = ScrapersItem()

    ### HTML directions ###
    ''' All of these should be in CSS
        If some are changed to xpath, this also needs to be changed in the relevant function!
    '''
    # FROM THE FRONT PAGE!!!
    article_CSS = '.news-box' # CSS for the entire article
    links_to_follow_CSS = 'a::attr(href)'
    publication_date_CSS = '.news-date::text'
    next_page_XPATH = '//a[normalize-space(text())="Suivant"]/@href'
    # FROM THE ARTICLE PAGE!!!
    title_CSS = 'h1.arrow::text'
    sub_title_XPATH = '//div[@id="content"]//h2//text()'
    article_content_XPATH = (
        '(//div[@id="content"]//h3[not(preceding::h4)] | //div[@id="content"]//p[not(preceding::h4)])'
    )
    article_text_bits_XPATH = article_content_XPATH + '//text()' # All text bits from the article - these will be combined in parse_article
    article_text_HTML_bits_XPATH = article_content_XPATH # All text bits from the article - these will be combined in parse_article
    image_links_XPATH = '//*[(@id = "content")]//img/@src'
    external_links_XPATH = article_content_XPATH + '//a/@href'
    article_references_bits_XPATH = '//div[@id="content"]//h4/following-sibling::p'
    author_XPATH = '//div[@id="content"]//h4//text()'

    def __init__(self, max_pages=None):
        super().__init__()
        Static_Scrapy.initialize(self, max_pages)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(GenerationZemmourSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_data = Static_Scrapy.load_existing_links(self.save_file, self.logger)

    def start_requests(self):
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
            pub_date = article.css(self.publication_date_CSS).get()

            if link in self.existing_data:
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
        if next_page and (self.MAX_PAGES is None or current_page < self.MAX_PAGES):
            yield response.follow(
                url=next_page,
                callback=self.parse_front,
                meta={'current_page': current_page + 1}
            )

    def parse_article(self, response):
        items = self.items
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'article_link'
        article_link = response.meta['article_link']
        # Extract 'publication_date'
        publication_date = response.meta['publication_date']

        if article_link in self.existing_data:
            self.logger.info(f"Skipping duplicate article: {article_link}")
            return

        # Extract 'article_title'
        article_title = response.css(self.title_CSS).get()
        article_title_clean = General_Functions.clean_text(article_title)
        # Extract 'article_sub_title'
        article_sub_title_bits = response.xpath(self.sub_title_XPATH).getall()
        article_sub_title_clean = General_Functions.join_and_clean(article_sub_title_bits)
        # Extract 'article_text'
        article_text_bits = response.xpath(self.article_text_bits_XPATH).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits)
        # Extract 'article_HTML'
        article_text_HTML_bits = response.xpath(self.article_text_HTML_bits_XPATH).getall()
        article_text_HTML = ' '.join(article_text_HTML_bits).strip()
        # Extract 'article_references'
        article_references_bits = response.xpath(self.article_references_bits_XPATH)
        article_references = []
        for p in article_references_bits:
            text_parts = p.xpath('.//text()').getall()
            hrefs = p.xpath('.//a/@href').getall()
            combined_text = ''.join(part.strip() for part in text_parts if part.strip())

            # If there are hrefs, join them to the end of the text
            if hrefs:
                combined = combined_text + ' ' + ' '.join(response.urljoin(href) for href in hrefs)
            else:
                combined = combined_text

            if combined:  # optional: filter out empty paragraphs
                article_references.append(combined)
        # Extract 'image_links'
        image_links = response.xpath(self.image_links_XPATH).getall()
        # Extract 'external_links'
        external_links = response.xpath(self.external_links_XPATH).getall()
        # Extract 'author'
        author_raw = response.xpath(self.author_XPATH).getall()
        author = General_Functions.join_and_clean(author_raw)


        items['scrape_date'] = timestamp
        items['publication_date'] = publication_date
        items['source'] = self.source
        items['article_title'] = article_title_clean
        items['article_sub_title'] = article_sub_title_clean
        items['article_text'] = article_text_clean
        items['author'] = author
        items['references_text'] = article_references
        items['image_links'] = image_links
        items['external_links'] = external_links
        items['article_HTML'] = article_text_HTML
        items['article_link'] = article_link

        self.existing_links.add(article_link)

        yield items
