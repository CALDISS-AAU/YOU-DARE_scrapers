import os
import json
from urllib.parse import urlparse
from urllib.parse import urljoin
from scrapy import signals
from w3lib.html import remove_tags
from playwright.async_api import async_playwright
from .general_functions import General_Functions
from typing import Union, List
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Static_Scrapy:
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
    def load_existing_links(save_file, logger):
        """
        Loads previously scraped article links from a file to avoid duplicates.

        Args:
            save_file (str): Path to the file storing previously scraped items.
            logger (logging.Logger): Logger to report warnings or info.

        Returns:
            set: A set of article links previously scraped.
        """
        existing = set()
        if os.path.exists(save_file):
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            item = json.loads(line.strip())
                            if "article_link" in item:
                                existing.add(item["article_link"])
                        except json.JSONDecodeError:
                            logger.warning("Skipping invalid JSON line.")
                logger.info(f"Loaded {len(existing)} existing articles.")
            except Exception as e:
                logger.warning(f"Error reading existing data: {e}, starting fresh.")
        return existing

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

    @staticmethod
    def turn_page(spider, response, next_page, callback):
        """Follows the next page if it exists and page limit hasn't been reached."""
        current_page = response.meta.get('current_page', 1)
        if next_page and (spider.MAX_PAGES is None or current_page < spider.MAX_PAGES):
            return response.follow(
                url=next_page,
                callback=callback,
                meta={'current_page': current_page + 1}
            )

    @staticmethod
    def match_images_with_captions(image_links: list, image_captions_html: list, captioned_image_srcs: list) -> list:
        """
        Aligns image captions with corresponding image links based on which images are wrapped in caption containers.

        Args:
            image_links (list): All image URLs found in the article.
            image_captions_html (list): Raw HTML strings of the captions (to be stripped).
            captioned_image_srcs (list): URLs of images known to be wrapped in caption containers (like <div class="wp-caption">).

        Returns:
            list: A list of captions aligned to image_links. Empty string for images without captions.
        """
        image_captions = [remove_tags(caption, keep=("a",)).strip() for caption in image_captions_html]

        fixed_captions = []
        caption_index = 0

        for img in image_links:
            if img in captioned_image_srcs:
                fixed_captions.append(image_captions[caption_index] if caption_index < len(image_captions) else "")
                caption_index += 1
            else:
                fixed_captions.append("")

        return fixed_captions

    @staticmethod
    def extract_captions_from_figures(article, image_links, figure_selector, image_selector, caption_selector):
        """
        Matches images with their captions based on figure-wrapped image blocks.

        Args:
            article (Selector): The article selector object from the spider.
            image_links (list): List of all image sources found in the article.
            figure_selector (str): CSS selector for <figure> tags or similar containers.
            image_selector (str): CSS selector for extracting image src from the figure block.
            caption_selector (str): CSS selector for extracting caption text from the figure block.

        Returns:
            list: A list of captions aligned with the image_links list. Empty strings for unmatched.
        """
        caption_map = {}
        for fig in article.css(figure_selector):
            img_src = fig.css(image_selector).get()
            caption_text_bits = fig.css(f"{caption_selector} *::text").getall()
            caption_text = General_Functions.clean_text(' '.join(caption_text_bits).strip())
            if img_src:
                caption_map[img_src] = caption_text

        return [caption_map.get(img, '') for img in image_links]

class Dynamic_Scrapy:
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
    def initialize(spider, max_scrolls=None):
        """
        Initializes the dynamic spider with scroll limit and placeholders.
        """
        spider.max_scrolls = int(max_scrolls) if max_scrolls else None
        spider.existing_data = set()
        spider.save_path = f"./data/{spider.name}/data_{spider.name}.jl"

    @staticmethod
    def setup_from_crawler(spider, crawler):
        """
        Connects the spider to crawler signals and sets save path.
        """
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        spider.settings = crawler.settings
        spider.save_path = Dynamic_Scrapy.get_feed_output_path(
            settings=crawler.settings,
            name=spider.name,
            region=spider.region
        )

    @staticmethod
    def load_existing_links(save_path):
        """
        Loads already scraped article links from a .jl file.
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
    def match_images_with_captions(image_links: list, image_captions_html: list, captioned_image_srcs: list) -> list:
        """
        Matches each image link with its correct caption text if available.

        This function loops through all given image links and tries to align 
        each link to a corresponding caption. 
        If an image has a matching caption (based on being present in `captioned_image_srcs`), 
        the caption is added; otherwise, an empty string is added.

        Args:
            image_links (list): 
                A list of all image URLs extracted from the article (e.g., all <img> src attributes).
            image_captions_html (list): 
                A list of all raw HTML or text snippets extracted for captions (e.g., <figcaption> text).
            captioned_image_srcs (list): 
                A subset of image_links — containing only those images that are actually captioned.

        Returns:
            list: 
                A list of captions, aligned in order to the image_links list. 
                Non-captioned images get an empty string ("").

        Example usage inside parse_article:
            image_links = response.css('figure img::attr(src)').getall()
            image_captions_html = response.css('figcaption::text').getall()
            captioned_image_srcs = image_links # Assuming all images are captioned
            image_captions = Dynamic_Scrapy_Click.match_images_with_captions(
                image_links=image_links,
                image_captions_html=image_captions_html,
                captioned_image_srcs=captioned_image_srcs
            )
        """
        image_captions = [remove_tags(caption, keep=("a",)).strip() for caption in image_captions_html]
        fixed_captions = []
        caption_index = 0

        for img in image_links:
            if img in captioned_image_srcs:
                fixed_captions.append(image_captions[caption_index] if caption_index < len(image_captions) else "")
                caption_index += 1
            else:
                fixed_captions.append("")

        return fixed_captions

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
            content = await Dynamic_Scrapy.scroll(page, max_scrolls, wait_time)
            await browser.close()
            return content

class Dynamic_Scrapy_Click:
    @staticmethod
    def get_feed_output_path(settings, name, region):
        """
        Constructs the absolute output file path for the feed based on Scrapy settings.
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
    def initialize(spider, max_pages=None):
        """
        Initializes the dynamic click spider with click limit and placeholders.
        """
        spider.max_pages = int(max_pages) if max_pages else None
        spider.existing_data = set()
        spider.save_path = f"./data/{spider.name}/data_{spider.name}.jl"

    @staticmethod
    def setup_from_crawler(spider, crawler):
        """
        Connects the spider to crawler signals and sets save path.
        """
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        spider.settings = crawler.settings
        spider.save_path = Dynamic_Scrapy_Click.get_feed_output_path( # FIXED THIS LINE
            settings=crawler.settings,
            name=spider.name,
            region=spider.region
        )

    @staticmethod
    def load_existing_links(save_path):
        """
        Loads already scraped article links from a .jl file.
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
    def match_images_with_captions(image_links: list, image_captions_html: list, captioned_image_srcs: list) -> list:
        """
        Matches each image link with its correct caption text if available.

        This function loops through all given image links and tries to align 
        each link to a corresponding caption. 
        If an image has a matching caption (based on being present in `captioned_image_srcs`), 
        the caption is added; otherwise, an empty string is added.

        Args:
            image_links (list): 
                A list of all image URLs extracted from the article (e.g., all <img> src attributes).
            image_captions_html (list): 
                A list of all raw HTML or text snippets extracted for captions (e.g., <figcaption> text).
            captioned_image_srcs (list): 
                A subset of image_links — containing only those images that are actually captioned.

        Returns:
            list: 
                A list of captions, aligned in order to the image_links list. 
                Non-captioned images get an empty string ("").

        Example usage inside parse_article:
            image_links = response.css('figure img::attr(src)').getall()
            image_captions_html = response.css('figcaption::text').getall()
            captioned_image_srcs = image_links # Assuming all images are captioned
            image_captions = Dynamic_Scrapy_Click.match_images_with_captions(
                image_links=image_links,
                image_captions_html=image_captions_html,
                captioned_image_srcs=captioned_image_srcs
            )
        """
        image_captions = [remove_tags(caption, keep=("a",)).strip() for caption in image_captions_html]
        fixed_captions = []
        caption_index = 0

        for img in image_links:
            if img in captioned_image_srcs:
                fixed_captions.append(image_captions[caption_index] if caption_index < len(image_captions) else "")
                caption_index += 1
            else:
                fixed_captions.append("")

        return fixed_captions

    @staticmethod
    async def fetch_links_with_clicking(
        url,
        click_button_selector,
        links_selector,
        max_clicks=None,
        wait_time=2000,
        stop_when_button_has_class: Union[str, List[str]] = None
    ):
        """
        Repeatedly clicks a button to load more content and scrapes links.
        Stops if max_clicks is reached or the button gets a 'disabled' class.
        """
        all_links = []

        async with async_playwright() as p:
            logger.info(f"Launching browser to scrape from {url}")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            logger.info("Initial page loaded.")

            # Initial links
            elements = await page.query_selector_all(links_selector)
            links = [await el.get_attribute('href') for el in elements]
            all_links.extend(links)
            logger.info(f"Collected {len(links)} initial links.")

            if max_clicks == 0:
                logger.info("Max clicks is 0. Exiting early.")
                await browser.close()
                return all_links

            click_count = 0
            while True:
                try:
                    await page.wait_for_selector(click_button_selector, timeout=3000)
                    button = await page.query_selector(click_button_selector)
                    if button is None:
                        logger.info("No button found.")
                        break

                    # Stop if button has a disabled class (optional)
                    if stop_when_button_has_class:
                        class_attr = await button.get_attribute("class") or ""
                        stop_classes = (
                            [stop_when_button_has_class]
                            if isinstance(stop_when_button_has_class, str)
                            else stop_when_button_has_class
                        )
                        for stop_class in stop_classes:
                            if stop_class in class_attr:
                                logger.info(f"Button has class '{stop_class}' — stopping.")
                                await browser.close()
                                return all_links

                    await button.click()
                    await page.wait_for_timeout(wait_time)

                    elements = await page.query_selector_all(links_selector)
                    links = [await el.get_attribute('href') for el in elements]
                    all_links.extend(links)

                    click_count += 1
                    logger.info(f"Click {click_count}: Collected {len(links)} links (Total: {len(all_links)}).")

                    if max_clicks is not None and click_count >= max_clicks:
                        logger.info("Reached max_clicks.")
                        break

                except Exception as e:
                    logger.warning(f"Error during clicking loop: {e}")
                    break

            await browser.close()
            logger.info(f"Scraping complete. Total links collected: {len(all_links)}.")
            return all_links

    @staticmethod
    async def extract_entries_from_links(page, container_selector, link_selector, publication_date_selector):
        """
        Extracts article links and publication dates by evaluating each container individually.
        Uses scrollIntoView to ensure lazy-rendered content like publication dates is hydrated.
        """
        entries = []
        containers = await page.query_selector_all(f"xpath={container_selector}")
        print(f"extract_entries_from_links: Found {len(containers)} containers.")

        for i, container in enumerate(containers):
            try:
                # 👇 Force scroll into view to trigger lazy rendering
                await container.evaluate("node => node.scrollIntoView({behavior: 'instant', block: 'center'})")
                await page.wait_for_timeout(100)  # Allow rendering to complete

                # Extract link (XPath relative to container)
                link_el = await container.query_selector(f"xpath={link_selector}")
                link = await link_el.get_attribute("href") if link_el else None

                # Extract date (XPath relative to container)
                date_el = await container.query_selector(f"xpath={publication_date_selector}")
                publication_date = await date_el.inner_text() if date_el else None

                if link:
                    entries.append({
                        "link": urljoin(page.url, link),
                        "publication_date": publication_date.strip() if publication_date else None
                    })

            except Exception as e:
                print(f"Error extracting container {i+1}: {e}")
                continue

        return entries

    @staticmethod
    async def fetch_links_and_publication_date_with_clicking(
        url: str,
        container_selector: str,
        link_selector: str,
        publication_date_selector: str,
        click_button_selector: str,
        max_clicks: int = None,
        wait_time: int = 1000,
        stop_when_button_has_class: Union[str, List[str]] = None
    ):
        all_entries = []
        delay_after_render = 1000  # milliseconds

        async with async_playwright() as p:
            logger.info(f"Launching browser to scrape from {url}")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000, wait_until="networkidle")

            logger.info("Initial page loaded. Waiting extra time for rendering...")
            await page.wait_for_timeout(wait_time + delay_after_render)

            all_entries.extend(
                await Dynamic_Scrapy_Click.extract_entries_from_links(
                    page, container_selector, link_selector, publication_date_selector
                )
            )

            if max_clicks == 0:
                await browser.close()
                return all_entries

            click_count = 0
            while True:
                try:
                    await page.wait_for_selector(click_button_selector, timeout=3000)
                    button = await page.query_selector(click_button_selector)
                    if not button:
                        logger.info("No button found.")
                        break

                    if stop_when_button_has_class:
                        class_attr = await button.get_attribute("class") or ""
                        stop_classes = [stop_when_button_has_class] if isinstance(stop_when_button_has_class, str) else stop_when_button_has_class
                        if any(cls in class_attr for cls in stop_classes):
                            logger.info("Button has stop class. Exiting.")
                            break

                    await button.click()
                    await page.wait_for_load_state("networkidle")
                    logger.info("Clicked pagination. Waiting for content to render...")
                    await page.wait_for_timeout(wait_time + delay_after_render)
                    await page.evaluate("""
                        () => {
                            window.scrollTo(0, 0);
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    """)
                    await page.wait_for_function(
                        "document.querySelectorAll('p.post-date, p.full-width-post-date, p.three-column-post-date').length >= 10",
                        timeout=5000
                    )
                    count = await page.evaluate("() => document.querySelectorAll('p.post-date, p.full-width-post-date, p.three-column-post-date').length")
                    logger.info(f"Detected {count} date elements before extraction")

                    new_entries = await Dynamic_Scrapy_Click.extract_entries_from_links(
                        page, container_selector, link_selector, publication_date_selector
                    )
                    all_entries.extend(new_entries)

                    click_count += 1
                    logger.info(f"Click {click_count}: Found {len(new_entries)} new entries (Total: {len(all_entries)}).")

                    if max_clicks and click_count >= max_clicks:
                        logger.info("Reached max_clicks limit.")
                        break

                except Exception as e:
                    logger.warning(f"Error during clicking: {e}")
                    break

            await browser.close()
            logger.info(f"Scraping complete. Total entries collected: {len(all_entries)}.")
            return all_entries

    @staticmethod
    async def fetch_page_with_playwright(url, wait_time=2000):
        """
        Uses Playwright to fetch a fully rendered page without any scrolling or clicking.
        
        Args:
            url (str): The URL of the page to fetch.
            wait_time (int, optional): Wait time after page load in ms (default: 2000).
        
        Returns:
            str: Final HTML content after page load.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"Failed to load {url}: {e}")
                await browser.close()
                return ""
            await page.wait_for_timeout(wait_time) # Just a basic wait to ensure JS finishes
            content = await page.content()
            await browser.close()
            return content

    # Continue from here..

class DynamicClickAndWait:

    @staticmethod
    async def click_and_collect_links(
        url,
        click_button_selector,
        links_selector,
        max_clicks=200,
        wait_time=3000,
        stop_when_button_has_class=None
    ):
        print(f"Opening browser to fetch links from {url}")
        links = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until='domcontentloaded')

            for click_num in range(max_clicks):
                button = await page.query_selector(click_button_selector)
                if not button:
                    print("No 'Load more' button found.")
                    break

                if stop_when_button_has_class:
                    stop_button = await page.query_selector(stop_when_button_has_class)
                    if stop_button:
                        print("Stop condition matched.")
                        break

                prev_count = await page.locator(links_selector).count()

                print(f"[Click #{click_num + 1}] Articles before click: {prev_count}")
                await page.wait_for_timeout(2000)
                await button.scroll_into_view_if_needed()
                await button.click(timeout=20000, no_wait_after=True)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                

                # Try 3 times to detect new content
                new_count = prev_count
                for retry in range(6):
                    wait = wait_time * (retry + 1)
                    print(f"[Retry {retry+1}] Waiting {wait}ms...")
                    await page.wait_for_timeout(wait)
                    new_count = await page.locator(links_selector).count()
                    print(f"[Retry {retry+1}] Article count: {new_count}")
                    if new_count > prev_count:
                        break

                if new_count == prev_count:
                    print("No new articles detected after click. Exiting.")
                    break

            print("Finished clicking. Collecting links...")

            article_elements = await page.query_selector_all(links_selector)
            for el in article_elements:
                href = await el.get_attribute('href')
                if href:
                    links.add(href)

            await browser.close()

        print(f"Final total article links collected: {len(links)}")
        return list(links)

