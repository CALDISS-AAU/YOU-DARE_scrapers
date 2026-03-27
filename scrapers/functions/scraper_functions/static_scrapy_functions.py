import os
import json
from urllib.parse import urlparse
from scrapy import signals

class Static_Scrapy:
    ## SETUP FUNCTIONS ##
    @staticmethod
    def get_feed_output_path(settings, name, region):
        """
        Constructs the absolute output file path for the feed based on Scrapy settings.

        Args:
            settings (dict): The Scrapy project settings.
            name (str): The name of the spider.
            region (str): The region for which the spider runs.

        Returns:
            str: Absolute file path or URI where the feed should be saved.

        Raises:
            ValueError: If no 'FEEDS' setting is found.
        """
        feeds = settings.get('FEEDS', {})
        if not feeds:
            raise ValueError("No FEEDS setting found in settings.py")
        uri_template = list(feeds.keys())[0]
        uri_filled = uri_template % {'name': name, 'region': region}
        parsed = urlparse(uri_filled)
        if parsed.scheme == 'file':
            return os.path.abspath(os.path.join(parsed.netloc, parsed.path))
        elif parsed.scheme == '':
            return os.path.abspath(uri_filled)
        else:
            return uri_filled

    @staticmethod
    def load_existing_links(save_path, column="article_link"):
        """
        Loads previously scraped article links from a JSON Lines (.jl) file.

        This helper reads the file line-by-line, parses each line as JSON, and
        collects values under the "article_link" key into a set. Invalid JSON
        lines are silently skipped. If the file does not exist, an empty set
        is returned.

        Args:
            save_path (str): Path to the JSON Lines file containing scraped items.
            column (str): The column containing the links of scraped items.

        Returns:
            set: A set of unique article links already present in the file.
        """
        existing_data = set()
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        if column in item:
                            existing_data.add(item[column])
                    except json.JSONDecodeError:
                        continue
        return existing_data

    @staticmethod
    def setup_from_crawler(spider, crawler):
        """
        Sets up the spider instance with required attributes and connects the open_spider signal.

        Args:
            spider (scrapy.Spider): The spider instance being set up.
            crawler (scrapy.Crawler): The Scrapy crawler instance.
        """
        spider.settings = crawler.settings
        spider.save_file = Static_Scrapy.get_feed_output_path(
            crawler.settings,
            name=spider.name,
            region=spider.region
        )
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)

    @staticmethod
    def initialize(spider, max_pages=None):
        """
        Initializes the spider with optional maximum page limit and default attributes.

        Args:
            spider (scrapy.Spider): The spider instance to initialize.
            max_pages (int, optional): Optional limit for the number of pages to scrape.
        """
        spider.MAX_PAGES = int(max_pages) if max_pages else None
        spider.existing_links = set()
        spider.scraped_data = []
        spider.save_file = None  # set later in from_crawler

    ## FUNCTIONALITY FUNCTIONS ##
    @staticmethod
    def turn_page(spider, response, next_page, callback):
        """
        Follows a pagination link to the next page if available and within the page limit.

        The current page number is read from `response.meta['current_page']` (defaulting to 1).
        If `next_page` is truthy and the spider has not reached `MAX_PAGES`, this method
        yields a new Request to the next page and increments the page counter in meta.

        Args:
            spider (scrapy.Spider): The active spider instance. Must have `MAX_PAGES` set
                (or None for no limit).
            response (scrapy.http.Response): The current response object containing meta.
            next_page (str | None): URL (absolute or relative) for the next page, or None
                if no next page exists.
            callback (callable): The callback function to handle the next page response.

        Returns:
            scrapy.Request | None: A Request to the next page when pagination should continue,
            otherwise None.
        """
        current_page = response.meta.get('current_page', 1)
        if next_page and (spider.MAX_PAGES is None or current_page < spider.MAX_PAGES):
            return response.follow(
                url=next_page,
                callback=callback,
                meta={'current_page': current_page + 1}
            )

