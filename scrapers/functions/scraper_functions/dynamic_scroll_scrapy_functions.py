import os
import json
from urllib.parse import urlparse
from scrapy import signals
from playwright.async_api import async_playwright
import logging
import inspect

class Dynamic_Scroll_Scrapy:
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
    def load_existing_links(save_path):
        """
        Loads previously scraped article links from a JSON Lines (.jl) file.

        This helper reads the file line-by-line, parses each line as JSON, and
        collects values under the "article_link" key into a set. Invalid JSON
        lines are silently skipped. If the file does not exist, an empty set
        is returned.

        Args:
            save_path (str): Path to the JSON Lines file containing scraped items.

        Returns:
            set: A set of unique article links already present in the file.
        """
        existing_data = set()
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        if "article_link" in item:
                            existing_data.add(item["article_link"])
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
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        spider.settings = crawler.settings
        spider.save_path = Dynamic_Scroll_Scrapy.get_feed_output_path(
            settings=crawler.settings,
            name=spider.name,
            region=spider.region
        )

    @staticmethod
    def initialize(spider, max_scrolls=None):
        """
        Initializes the spider with optional maximum scroll limit and default attributes.

        Args:
            spider (scrapy.Spider): The spider instance to initialize.
            max_scrolls (int, optional): Optional limit for the number of scrolls to scrape.
        """
        spider.max_scrolls = int(max_scrolls) if max_scrolls else None
        spider.existing_data = set()
        spider.save_path = f"./data/{spider.name}/data_{spider.name}.jl"

    ## FUNCTIONALITY FUNCTIONS ##
    @staticmethod
    async def scroll_adaptive(page, article_selector, max_scrolls=None, start_wait=1000, max_wait=60000, growth_factor=2.0, plateau_checks=2, post_scroll_pause=1500):
        """
        Scrolls a Playwright page adaptively until no new content loads or a scroll limit is reached.

        The function scrolls to the bottom repeatedly, checking for growth in either:
        - total document height, or
        - number of elements matching `article_selector`.

        If no growth is detected, the wait time is increased (up to `max_wait`) for a few
        "plateau" checks before concluding the page is fully loaded.

        Args:
            page (playwright.async_api.Page): The Playwright page instance to scroll.
            article_selector (str): CSS selector for items expected to load dynamically
                (e.g., article cards). Used to detect new content.
            max_scrolls (int, optional): Maximum number of scrolls to perform. None for unlimited.
            start_wait (int, optional): Initial wait time after a scroll in milliseconds.
            max_wait (int, optional): Maximum wait time between checks in milliseconds.
            growth_factor (float, optional): Multiplier for increasing wait time when no change is detected.
            plateau_checks (int, optional): Number of consecutive "no change" checks allowed per scroll
                before stopping.
            post_scroll_pause (int, optional): Extra pause after detecting growth, in milliseconds.

        Returns:
            str: The final rendered HTML content after adaptive scrolling.
        """
        print("[scroller file]", inspect.getsourcefile(Dynamic_Scroll_Scrapy))
        last_height=await page.evaluate("document.body.scrollHeight")
        last_count=await page.eval_on_selector_all(article_selector,"els=>els.length")
        wait_time=start_wait
        scrolls=0
        while (max_scrolls is None or scrolls<max_scrolls):
            scrolls+=1
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            attempts=0
            changed=False
            while attempts<=plateau_checks:
                await page.wait_for_timeout(int(wait_time))
                try:
                    await page.wait_for_load_state("networkidle",timeout=3000)
                except:
                    pass
                new_height=await page.evaluate("document.body.scrollHeight")
                new_count=await page.eval_on_selector_all(article_selector,"els=>els.length")
                if new_height>last_height or new_count>last_count:
                    last_height=new_height
                    last_count=new_count
                    changed=True
                    if attempts==0 and wait_time>start_wait:
                        wait_time=max(start_wait,int(wait_time/1.25))
                    break
                attempts+=1
                if attempts<=plateau_checks and wait_time<max_wait:
                    wait_time=min(int(wait_time*growth_factor),max_wait)
                    print(f"[adaptive+pause] no change; increasing wait to {wait_time}ms")
            if not changed:
                break
            await page.wait_for_timeout(int(post_scroll_pause))
        return await page.content()

    @staticmethod
    async def fetch_with_playwright_adaptive(
        url, 
        article_selector, 
        max_scrolls=None, 
        start_wait=1000, 
        max_wait=60000, 
        growth_factor=2.0, 
        plateau_checks=2, 
        post_scroll_pause=1500
    ):
        """
        Fetches a fully rendered page using Playwright with adaptive scrolling.

        This is a convenience wrapper around `scroll_adaptive`. It:
        1) launches a headless Chromium browser,
        2) navigates to `url`,
        3) adaptively scrolls until content stops growing (or max scrolls reached),
        4) returns the final HTML.

        Args:
            url (str): The target page URL.
            article_selector (str): CSS selector for dynamically loaded items used for growth detection.
            max_scrolls (int, optional): Maximum number of scrolls to perform. None for unlimited.
            start_wait (int, optional): Initial wait time after a scroll in milliseconds.
            max_wait (int, optional): Maximum wait time between checks in milliseconds.
            growth_factor (float, optional): Multiplier for increasing wait time when no change is detected.
            plateau_checks (int, optional): Number of consecutive "no change" checks allowed per scroll.
            post_scroll_pause (int, optional): Extra pause after detecting growth, in milliseconds.

        Returns:
            str: The final rendered HTML content after adaptive scrolling.
        """
        print("[wrapper file]", inspect.getsourcefile(Dynamic_Scroll_Scrapy))
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            page=await browser.new_page()
            await page.goto(url, timeout=60000)
            content=await Dynamic_Scroll_Scrapy.scroll_adaptive(
                page,
                article_selector,
                max_scrolls,
                start_wait,
                max_wait,
                growth_factor,
                plateau_checks,
                post_scroll_pause
            )
            await browser.close()
            return content

    @staticmethod
    async def scroll(page, max_scrolls=None, wait_time=2000):
        """
        Scrolls the page to the bottom up to max_scrolls times or until no more new content is loaded.

        Args:
            page (playwright.async_api.Page): The Playwright page instance.
            max_scrolls (int, optional): Maximum number of scrolls. None for unlimited.
            wait_time (int, optional): Milliseconds to wait after each scroll (default: 2000).

        Returns:
            str: The final page content after scrolling.
        """
        last_height = await page.evaluate("document.body.scrollHeight")
        scroll_count = 0

        while max_scrolls is None or scroll_count < max_scrolls:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(wait_time)
            new_height = await page.evaluate("document.body.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height
            scroll_count += 1

        return await page.content()

    @staticmethod
    async def fetch_with_playwright(url, max_scrolls=None, wait_time=2000):
        """
        Uses Playwright to fetch fully rendered page content with optional scrolling.

        Args:
            url (str): The target page URL.
            max_scrolls (int, optional): Number of scrolls to simulate (None for infinite).
            wait_time (int, optional): Wait time between scrolls in ms.

        Returns:
            str: Final HTML content after scrolling.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            content = await Dynamic_Scroll_Scrapy.scroll(page, max_scrolls, wait_time)
            await browser.close()
            return content