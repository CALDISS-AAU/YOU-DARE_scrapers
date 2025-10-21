# EXTERNAL IMPORTS
import scrapy
from scrapy.selector import Selector
from datetime import datetime
import json

# INTERNAL IMPORTS
from ...items import ScrapersItem
from ...functions.general_functions import General_Functions
from ...functions.scrapy_functions import Dynamic_Scrapy_Click

class NordfrontSMRSpider(scrapy.Spider):
    name = 'nordfront_SMR_SPIDER'
    region = 'Sweden'
    source = 'nordfront'
    original_data_path = '/work/YOU-DARE/scrapers/data/Sweden/nordfront_SWE_SPIDER/data_nordfront_SWE_SPIDER.jl'
    
    # SMR QUERIES
    smr_article_title_XPATH = '//article/header/h1/text()'
    smr_author_XPATH = '//article/header/section/section[2]/a[1]/text()'
    smr_publication_date_XPATH = '//article/span/ul[@class="info-tags"]/li/text()'
    smr_article_text_bits_CSS = '.post-content *::text'
    smr_article_categories_XPATH = '//ul[@class="info-tags"][span[contains(text(), "Kategoriserat som:")]]/li/a/text()'
    smr_image_links_XPATH = '//article/span/p/img/@src'
    smr_external_links_XPATH = '//article/span/p/a/@href'
    smr_article_HTML_bits_XPATH = '//article[@id="main-article"]'
    smr_youtube_XPATH = '//article//iframe[contains(@src, "youtube.com")]/@src'
    smr_other_items_XPATH = 'None'

    def start_requests(self):
        smr_links = self.extract_smr_links()
        for link in smr_links:
            yield scrapy.Request(url=link, callback=self.parse_article)

    def extract_smr_links(self):
        smr_links = []
        try:
            with open(self.original_data_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        article = json.loads(line.strip())
                        link = article.get('article_link', '')
                        if link.endswith('.smr'):
                            smr_links.append(link)
                    except json.JSONDecodeError:
                        self.logger.warning("Invalid JSON line encountered.")
        except FileNotFoundError:
            self.logger.error(f"Original dataset not found at: {self.original_data_path}")
        return smr_links

    def parse_article(self, response):
        item = ScrapersItem()
        timestamp = datetime.now().strftime('%Y-%m-%d')

        # Extract fields
        item['scrape_date'] = timestamp
        item['publication_date'] = response.xpath(self.smr_publication_date_XPATH).get(default='').strip()
        item['source'] = self.source
        item['article_link'] = response.url

        title = response.xpath(self.smr_article_title_XPATH).get()
        item['article_title'] = General_Functions.clean_text(title) if title else None

        author = response.xpath(self.smr_author_XPATH).get()
        item['author'] = General_Functions.clean_text(author) if author else None

        text_bits = response.css(self.smr_article_text_bits_CSS).getall()
        item['article_text'] = General_Functions.join_and_clean(text_bits)

        item['article_categories'] = response.xpath(self.smr_article_categories_XPATH).getall()
        item['image_links'] = response.xpath(self.smr_image_links_XPATH).getall()
        item['links_in_text'] = response.xpath(self.smr_external_links_XPATH).getall()
        item['embedded_media_links'] = response.xpath(self.smr_youtube_XPATH).getall()

        html_bits = response.xpath(self.smr_article_HTML_bits_XPATH).getall()
        item['article_HTML'] = ' '.join(html_bits).strip()

        item['other_items'] = self.smr_other_items_XPATH

        self.logger.info(f"Scraped SMR article: {item['article_title']} ({response.url})")
        yield item
