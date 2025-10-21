import os
import re
import json
import time
from urllib.parse import urlparse
from urllib.parse import urljoin
from scrapy import signals
from w3lib.html import remove_tags
from playwright.async_api import async_playwright
import contextlib, time
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
    def load_existing_links(save_file, logger, column="article_link"):
        """
        Loads previously scraped article links from a file to avoid duplicates.

        Args:
            save_file (str): Path to the file storing previously scraped items.
            logger (logging.Logger): Logger to report warnings or info.
	        column (str, optional): The key name inside each JSON object that contains
            the link. Defaults to "article_link".

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
                            if column in item:
                                existing.add(item[column])
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
    ###
    @staticmethod
    async def fetch_article_with_wait(
        url: str,
        main_selector: str | None = None,
        img_selector: str = 'img, source, picture',
        settle_ms: int = 1200,
        max_total_ms: int = 45000,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    ) -> str:
        """
        Generic Playwright fetcher for article pages:
          - navigates to `url`
          - optionally waits for `main_selector`
          - scrolls until content & image count settle (or timeout)
          - resolves lazy images and srcsets -> sets data-resolved-src
          - returns fully-rendered HTML (page.content())
        All site-specific details should be passed via the spider.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 2200},
                user_agent=user_agent,
            )
            page = await context.new_page()

            # Navigate
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Try to clear common consent dialogs (best effort)
            try:
                for sel in [
                    '#onetrust-accept-btn-handler',
                    'button:has-text("Accept All")',
                    '.ot-sdk-container button:has-text("Accept")',
                    'button:has-text("I Accept")',
                    'button:has-text("Agree")'
                ]:
                    try:
                        await page.locator(sel).click(timeout=1200)
                        break
                    except:
                        pass
                await page.evaluate("""
                    (() => {
                        document.body.style.overflow = 'auto';
                        const killers = Array.from(document.querySelectorAll(
                          '[aria-modal="true"],[role="dialog"],#onetrust-consent-sdk,.ot-sdk-container,.cookie,.consent'
                        ));
                        killers.forEach(k => k.remove());
                    })();
                """)
            except:
                pass

            # Wait for the main content container if provided
            if main_selector:
                try:
                    await page.wait_for_selector(main_selector, timeout=15000, state="attached")
                except:
                    # don't fail the fetch if selector never appears; continue anyway
                    pass

            # JS helper: resolve best image URL and stamp on node as data-resolved-src
            resolve_imgs_js = """
                (sel) => {
                  const pickFromSrcset = (s) => {
                    try {
                      const parts = s.split(',').map(x => x.trim()).filter(Boolean);
                      if (parts.length === 0) return null;
                      // choose the last candidate (usually largest)
                      const last = parts[parts.length - 1].split(' ')[0];
                      return last || null;
                    } catch(e) { return null; }
                  };
                  const els = Array.from(document.querySelectorAll(sel));
                  for (const el of els) {
                    let url = null;
                    const tag = (el.tagName || '').toUpperCase();
                    if (tag === 'IMG') {
                      url = el.currentSrc || el.getAttribute('src') ||
                            el.getAttribute('data-src') || el.getAttribute('data-lazy-src') ||
                            el.getAttribute('data-original') || null;
                      if (!url) {
                        const ss = el.getAttribute('srcset') || el.getAttribute('data-srcset');
                        if (ss) url = pickFromSrcset(ss);
                      }
                    } else {
                      // <source> or others in <picture>
                      const ss = el.getAttribute('srcset') || el.getAttribute('data-srcset');
                      if (ss) url = pickFromSrcset(ss);
                    }
                    if (url) {
                      el.setAttribute('data-resolved-src', url);
                    }
                  }
                }
            """

            # Scroll/settle loop
            def monotonic_ms():
                return int(time.monotonic() * 1000)

            deadline = monotonic_ms() + max_total_ms
            last_h = await page.evaluate("() => (document.scrollingElement || document.documentElement || document.body).scrollHeight")
            try:
                last_img_count = await page.eval_on_selector_all(img_selector, "els => els.length")
            except:
                last_img_count = 0
            plateaus = 0

            while monotonic_ms() < deadline:
                # Scroll to bottom + poke events
                try:
                    await page.evaluate("""
                        () => {
                          const el = document.scrollingElement || document.documentElement || document.body;
                          el.scrollTop = el.scrollHeight;
                          window.scrollTo(0, el.scrollHeight);
                          window.dispatchEvent(new Event('scroll'));
                          window.dispatchEvent(new Event('resize'));
                          el.dispatchEvent(new Event('scroll', {bubbles:true}));
                        }
                    """)
                except:
                    pass
                await page.mouse.wheel(0, 1600)

                # Let things load a bit
                await page.wait_for_timeout(int(settle_ms * 0.5))
                try:
                    await page.wait_for_load_state("networkidle", timeout=2000)
                except:
                    pass

                # Resolve images on each pass
                try:
                    await page.evaluate(resolve_imgs_js, img_selector)
                except:
                    pass

                # Check progress
                new_h = await page.evaluate("() => (document.scrollingElement || document.documentElement || document.body).scrollHeight")
                try:
                    new_img_count = await page.eval_on_selector_all(img_selector, "els => els.length")
                except:
                    new_img_count = last_img_count

                if new_h <= last_h and new_img_count <= last_img_count:
                    plateaus += 1
                    if plateaus >= 3:
                        break
                else:
                    plateaus = 0
                    last_h = new_h
                    last_img_count = new_img_count

            # Final resolve before capture
            try:
                await page.evaluate(resolve_imgs_js, img_selector)
            except:
                pass

            html = await page.content()
            await context.close()
            await browser.close()
            return html
    ###
    # v4.0-min-pause — original adaptive scroller + post-scroll pause (new names)
    @staticmethod
    async def scroll_adaptive_pause_v1(page, article_selector, max_scrolls=None, start_wait=1000, max_wait=60000, growth_factor=2.0, plateau_checks=2, post_scroll_pause=1500):
        last_height=await page.evaluate("document.body.scrollHeight")
        last_count=await page.eval_on_selector_all(article_selector,"els=>els.length")
        wait_time=start_wait
        scrolls=0
        while (max_scrolls is None or scrolls<max_scrolls):
            scrolls+=1
            print(f"[adaptive+pause] scroll #{scrolls} | wait={wait_time}ms | items={last_count}")
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
                print("[adaptive+pause] no more new content; stopping")
                break
            await page.wait_for_timeout(int(post_scroll_pause))
        print(f"[adaptive+pause] done after {scrolls} scrolls | total items={last_count}")
        return await page.content()

    # v4.0-min-pause — fetch wrapper (new name)
    @staticmethod
    async def fetch_with_playwright_adaptive_pause_v1(url, article_selector, max_scrolls=None, start_wait=1000, max_wait=60000, growth_factor=2.0, plateau_checks=2, post_scroll_pause=1500):
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            page=await browser.new_page()
            await page.goto(url, timeout=60000)
            content=await Dynamic_Scrapy.scroll_adaptive_pause_v1(
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
    async def scroll_adaptive(page, article_selector, max_scrolls=None, start_wait=1000, max_wait=60000, growth_factor=2.0, plateau_checks=2):
        last_height=await page.evaluate("document.body.scrollHeight")
        last_count=await page.eval_on_selector_all(article_selector,"els=>els.length")
        wait_time=start_wait
        scrolls=0
        while (max_scrolls is None or scrolls<max_scrolls):
            scrolls+=1
            print(f"[adaptive] scroll #{scrolls} | wait={wait_time}ms | items={last_count}")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            attempts=0
            changed=False
            while attempts<=plateau_checks:
                await page.wait_for_timeout(int(wait_time))
                new_height=await page.evaluate("document.body.scrollHeight")
                new_count=await page.eval_on_selector_all(article_selector,"els=>els.length")
                if new_height>last_height or new_count>last_count:
                    last_height=new_height
                    last_count=new_count
                    changed=True
                    # if it took extra attempts to change, keep the longer wait; else gently decay
                    if attempts==0 and wait_time>start_wait:
                        wait_time=max(start_wait,int(wait_time/1.25))
                    break
                attempts+=1
                if attempts<=plateau_checks and wait_time<max_wait:
                    wait_time=min(int(wait_time*growth_factor),max_wait)
                    print(f"[adaptive] no change; increasing wait to {wait_time}ms")
            if not changed:
                print("[adaptive] no more new content; stopping")
                break
        print(f"[adaptive] done after {scrolls} scrolls | total items={last_count}")
        return await page.content()

    @staticmethod
    async def fetch_with_playwright_adaptive(url, article_selector, max_scrolls=None, start_wait=1000, max_wait=60000, growth_factor=2.0, plateau_checks=2):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            content = await Dynamic_Scrapy.scroll_adaptive(
                page,
                article_selector,          # <- selector goes here
                max_scrolls,
                start_wait,
                max_wait,
                growth_factor,
                plateau_checks
            )
            await browser.close()
            return content

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
        wait_time=3000,
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
                    await page.wait_for_selector(click_button_selector, timeout=15000, state='visible')
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
    async def fetch_links_with_clicking_xpath(
        url,
        click_button_selector,
        links_selector,
        max_clicks=None,
        wait_time=3000,
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
            elements = await page.query_selector_all(f"xpath={links_selector}")
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
                    await page.wait_for_selector(click_button_selector, timeout=15000, state='visible')
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

                    elements = await page.query_selector_all(f"xpath={links_selector}")
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
            
########################
    @staticmethod
    async def fetch_links_with_clicking_stop_at_certain_article(
        url,
        click_button_selector,
        links_selector,
        max_clicks=None,
        wait_time=2000,
        stop_when_button_has_class = None,
        stop_if_url_starts_with = None  # NEW
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
                    await page.wait_for_selector(click_button_selector, timeout=5000)
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
                    
                    # STOP IF AN ARTICLE STARTS with URL : https://xn--motstndsrrelsen-llb70a.se/2021/05/{whatever}
                    if stop_if_url_starts_with: 
                        for link in links:
                            match = re.search(r'/(\d{4}/\d{2}/\d{2})/', link)
                            if match:
                                link_date = match.group(1)
                                if link_date < stop_if_url_starts_with:
                                    logger.info(f"Found link the with {link_date} < {stop_if_url_starts_with} - stop.")
                                    await browser.close()
                                    return all_links

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

########################



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
                    await page.wait_for_selector(click_button_selector, timeout=5000)
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
        wait_time=5000,
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
                await page.evaluate("arguments[0].scrollIntoView()", button)
                # await page.evaluate("(element) => element.scrollIntoView()", button)

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_selector(click_button_selector, state='visible', timeout=30000)
                await button.click(timeout=10000, no_wait_after=True)

                

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

from playwright.async_api import async_playwright
import contextlib

import contextlib

class DynamicClickAndWait_2:
    @staticmethod
    async def click_and_collect_links(
        url,
        click_button_selector,
        links_selector,
        max_clicks=None,          # None = unlimited; 0 = no clicks; N = up to N clicks
        wait_time=5000,
        stop_when_button_has_class=None
    ):
        print(f"Opening browser to fetch links from {url}")
        links = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until='domcontentloaded')

            # Best-effort: dismiss common consent banners
            for sel in [
                "#onetrust-accept-btn-handler",
                "button:has-text('Elfogad')",
                "button:has-text('elfogad')",
                "button:has-text('Accept')",
                "button:has-text('Rendben')",
                ".cm-btn-accept",
            ]:
                with contextlib.suppress(Exception):
                    btn = page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click()
                        break

            click_num = 0
            while True:
                # Respect user-specified limit
                if max_clicks is not None and click_num >= int(max_clicks):
                    print("Reached max_clicks limit.")
                    break

                # Reveal lazy UI first
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(300)

                buttons = page.locator(click_button_selector)
                count = await buttons.count()
                if count == 0:
                    print("No 'Load more' button found.")
                    break

                # Prefer the bottom-most match
                button_loc = buttons.last

                # Optional external stop condition
                if stop_when_button_has_class and await page.locator(stop_when_button_has_class).count() > 0:
                    print("Stop condition matched.")
                    break

                prev_count = await page.locator(links_selector).count()
                print(f"[Click #{click_num + 1}] Articles before click: {prev_count}")

                # Try to make it visible, but don't block forever
                with contextlib.suppress(Exception):
                    await button_loc.scroll_into_view_if_needed(timeout=1000)

                # If it's hidden, assume end-of-feed and stop cleanly
                try:
                    visible = await button_loc.is_visible()
                except Exception:
                    visible = False

                if not visible:
                    print("Load more button present but hidden. Assuming no more items. Stopping.")
                    break

                # Click the button (normal -> force -> JS fallback) without crashing
                clicked = False
                try:
                    await button_loc.click(timeout=5000)
                    clicked = True
                except Exception as e1:
                    print(f"Normal click failed ({e1}). Trying force click.")
                    try:
                        await button_loc.click(timeout=5000, force=True)
                        clicked = True
                    except Exception as e2:
                        print(f"Force click failed ({e2}). Trying JS click fallback.")
                        try:
                            handle = await button_loc.element_handle()
                            if handle:
                                await page.evaluate("(el)=>el.click()", handle)
                                clicked = True
                        except Exception as e3:
                            print(f"JS click fallback failed ({e3}). Stopping.")
                            clicked = False

                if not clicked:
                    break

                # Incremental wait loop to detect newly loaded items
                new_count = prev_count
                for retry in range(6):
                    w = wait_time * (retry + 1)
                    print(f"[Retry {retry+1}] Waiting {w}ms...")
                    await page.wait_for_timeout(w)
                    new_count = await page.locator(links_selector).count()
                    print(f"[Retry {retry+1}] Article count: {new_count}")
                    if new_count > prev_count:
                        break

                if new_count == prev_count:
                    print("No new articles detected after click. Exiting.")
                    break

                click_num += 1

            print("Finished clicking. Collecting links...")

            # Works with CSS or XPath because we use a Locator
            hrefs = await page.locator(links_selector).evaluate_all(
                "els => els.map(el => el.href || el.getAttribute('href'))"
            )
            for href in hrefs:
                if href:
                    links.add(href)

            await browser.close()

        print(f"Final total article links collected: {len(links)}")
        return list(links)


class DynamicScrollAndClick:
    @staticmethod
    async def _scroll_pass(page, article_selector, start_wait=800, max_wait=8000, growth=1.6, plateau_checks=2):
        last_h=await page.evaluate("()=>(document.scrollingElement||document.documentElement||document.body).scrollHeight")
        last_n=await page.eval_on_selector_all(article_selector,"els=>els.length")
        wait=start_wait
        tries=0
        while tries<=plateau_checks:
            await page.evaluate("()=>{const el=document.scrollingElement||document.documentElement||document.body;el.scrollTop=el.scrollHeight;window.dispatchEvent(new Event('scroll'));}")
            await page.mouse.wheel(0,1600)
            await page.wait_for_timeout(wait)
            with contextlib.suppress(Exception):
                await page.wait_for_load_state("networkidle",timeout=2000)
            new_h=await page.evaluate("()=>(document.scrollingElement||document.documentElement||document.body).scrollHeight")
            new_n=await page.eval_on_selector_all(article_selector,"els=>els.length")
            if new_h>last_h or new_n>last_n:
                last_h, last_n=new_h, new_n
                if wait>start_wait: wait=max(start_wait,int(wait/1.25))
                tries=0
            else:
                tries+=1
                wait=min(int(wait*growth),max_wait)
        return last_n

    @staticmethod
    async def fetch_with_playwright_hybrid(
        url:str,
        article_selector:str,
        load_more_selector:str,
        max_cycles:int|None=None,          # max number of button clicks
        wait_after_click:int=1200,
        stop_when_button_has_class:str|list[str]|None=None,
        user_agent:str=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    )->str:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            ctx=await browser.new_context(viewport={"width":1280,"height":2200},user_agent=user_agent)
            page=await ctx.new_page()
            await page.goto(url,timeout=60000,wait_until="domcontentloaded")

            # best-effort cookie banner clear
            for sel in ['#onetrust-accept-btn-handler','button:has-text("Accept All")','button:has-text("Accept")','button:has-text("I agree")']:
                with contextlib.suppress(Exception):
                    btn=page.locator(sel).first
                    if await btn.count() and await btn.is_visible(): await btn.click(); break

            with contextlib.suppress(Exception):
                await page.wait_for_selector(article_selector,timeout=15000)

            clicks=0
            prev_total=await page.locator(article_selector).count()

            while True:
                # STEP 1: scroll to bottom until short plateau
                after_scroll=await DynamicScrollAndClick._scroll_pass(page, article_selector)

                # STEP 2: if there's a load-more button, click it; else STOP
                buttons=page.locator(load_more_selector)
                if not await buttons.count():
                    break
                btn=buttons.last

                if stop_when_button_has_class:
                    classes=await btn.get_attribute("class") or ""
                    stop_list=[stop_when_button_has_class] if isinstance(stop_when_button_has_class,str) else stop_when_button_has_class
                    if any(s in classes for s in stop_list):
                        break

                with contextlib.suppress(Exception):
                    await btn.scroll_into_view_if_needed(timeout=1000)

                clicked=False
                try:
                    await btn.click(timeout=5000); clicked=True
                except Exception:
                    with contextlib.suppress(Exception):
                        await btn.click(timeout=5000,force=True); clicked=True
                    if not clicked:
                        with contextlib.suppress(Exception):
                            handle=await btn.element_handle()
                            if handle: await page.evaluate("(el)=>el.click()",handle); clicked=True
                if not clicked:
                    break

                # wait for new cards to show up (backoff) — then loop back to Step 1
                grew=False
                for i in range(6):
                    await page.wait_for_timeout(wait_after_click*(i+1))
                    with contextlib.suppress(Exception):
                        await page.wait_for_load_state("networkidle",timeout=2500)
                    cnt=await page.locator(article_selector).count()
                    if cnt>after_scroll:
                        grew=True
                        prev_total=cnt
                        break

                if not grew:
                    # some sites need a nudge after clicking
                    cnt=await DynamicScrollAndClick._scroll_pass(page, article_selector)
                    if cnt<=after_scroll:
                        break
                    prev_total=cnt

                clicks+=1
                if max_cycles is not None and clicks>=int(max_cycles):
                    break

            html=await page.content()
            await ctx.close(); await browser.close()
            return html