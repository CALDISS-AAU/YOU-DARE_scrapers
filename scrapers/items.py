# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ScrapersItem(scrapy.Item):
    # define the fields for your item here like:
    scrape_date = scrapy.Field()
    article_link = scrapy.Field()
    article_title = scrapy.Field()
    article_sub_title = scrapy.Field()
    publication_date = scrapy.Field()
    author = scrapy.Field()
    image_links = scrapy.Field()
    image_captions = scrapy.Field()
    youtube_links = scrapy.Field()
    embedded_media_links = scrapy.Field()
    article_categories = scrapy.Field()
    article_text = scrapy.Field()
    external_links = scrapy.Field()
    links_in_text = scrapy.Field()
    article_HTML = scrapy.Field()
    themes_text = scrapy.Field()
    categories = scrapy.Field()
    references_text = scrapy.Field()
    references_links = scrapy.Field()
    source = scrapy.Field()
    other_items = scrapy.Field()
    keyword = scrapy.Field()
    post_link = scrapy.Field()
    post_title = scrapy.Field()
    post_author = scrapy.Field()
    thread_text = scrapy.Field()
    post_HTML = scrapy.Field()
    pass
