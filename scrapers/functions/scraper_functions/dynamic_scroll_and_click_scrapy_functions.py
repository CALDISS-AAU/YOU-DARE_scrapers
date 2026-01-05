import os
import json
from urllib.parse import urlparse
from scrapy import signals
from playwright.async_api import async_playwright
import contextlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Dynamic_Scroll_And_Click:
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
        spider.save_path = Dynamic_Scroll_And_Click.get_feed_output_path(
            settings=crawler.settings,
            name=spider.name,
            region=spider.region
        )

    @staticmethod
    def initialize(spider, max_loads=None):
        """
        Initializes the spider with optional maximum load limit and default attributes.

        Args:
            spider (scrapy.Spider): The spider instance to initialize.
            max_loads (int, optional): Optional limit for the number of loads to scrape.
        """
        spider.max_loads = int(max_loads) if max_loads else None
        spider.existing_data = set()
        spider.save_path = f"./data/{spider.name}/data_{spider.name}.jl"

    ## FUNCTIONALITY FUNCTIONS ##
    @staticmethod
    async def load_and_collect_links(
        url: str,
        article_selector: str,
        load_more_selector: str,
        max_loads: int | None = None,          # number of scroll/click loads
        wait_after_click: int = 1200,
        stop_when_button_has_class: str | list[str] | None = None,
    ) -> str:
        """
        Loads a listing page with Playwright and incrementally reveals more items
        by combining scroll and "load more" button clicks.

        One "load" is counted when the number of elements matching `article_selector`
        increases due to either:
            * a scroll step, or
            * a click on the load-more button (`load_more_selector`).

        The behavior of `max_loads` is:
            * 0        → only the initial content is loaded (no scrolls or clicks),
            * N > 0    → perform at most N successful loads,
            * None     → keep loading until scrolling/clicking no longer increases
                          the article count or no button is available.

        The function:
            1. Opens `url` in a headless Chromium context (with a tall viewport).
            2. Best-effort dismisses common cookie/consent banners.
            3. Repeatedly:
                - performs a small scroll and checks for new articles;
                - optionally clicks a "load more" button if present, waiting for
                  additional items to render;
                - stops when no further progress is made or `max_loads` is reached.
            4. Returns the final rendered HTML as a string.

        Args:
            url (str): The URL of the listing page to load.
            article_selector (str): CSS selector for article/card elements to count.
            load_more_selector (str): CSS selector for a "load more" button used to
                reveal additional items, if present.
            max_loads (int | None, optional): Maximum number of successful loads
                (scroll/click that increases article count). If None, load until no
                new items appear.
            wait_after_click (int, optional): Base wait time (in milliseconds) after
                scrolls or clicks before re-counting articles (default: 1200).
            stop_when_button_has_class (str | list[str] | None, optional): One or more
                class-name fragments; if any are found in the button's `class`
                attribute, loading stops (useful for disabled or "end of feed" states).

        Returns:
            str: The final HTML content of the page after all loads are completed.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 2200},
            )
            page = await ctx.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # best-effort cookie banner clear
            for sel in [
                '#onetrust-accept-btn-handler',
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("I agree")'
            ]:
                with contextlib.suppress(Exception):
                    btn = page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click()
                        break

            with contextlib.suppress(Exception):
                await page.wait_for_selector(article_selector, timeout=15000)

            current_count = await page.locator(article_selector).count()
            loads = 0
            logger.info(f"[load_and_collect_links] Initial cards on {url}: {current_count}, max_loads={max_loads}")

            while True:
                # If we've hit the requested number of loads, stop immediately.
                if max_loads is not None and loads >= int(max_loads):
                    break

                made_progress = False

                # ---- STEP 1: try ONE scroll load ----
                before = current_count
                # single scroll step (not full plateau scroll)
                await page.evaluate(
                    "()=>{const el=document.scrollingElement||"
                    "document.documentElement||document.body;"
                    "el.scrollBy(0, window.innerHeight*0.9);"
                    "window.dispatchEvent(new Event('scroll'));}"
                )
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(wait_after_click)
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=2500)

                current_count = await page.locator(article_selector).count()
                if current_count > before:
                    loads += 1
                    made_progress = True
                    logger.debug(f"[load_and_collect_links] Scroll load #{loads}: {current_count} cards")

                # If we've now reached the limit after the scroll, stop.
                if max_loads is not None and loads >= int(max_loads):
                    break

                # ---- STEP 2: try ONE click load (if button exists) ----
                buttons = page.locator(load_more_selector)
                if await buttons.count():
                    btn = buttons.last

                    if stop_when_button_has_class:
                        classes = await btn.get_attribute("class") or ""
                        stop_list = (
                            [stop_when_button_has_class]
                            if isinstance(stop_when_button_has_class, str)
                            else stop_when_button_has_class
                        )
                        if any(s in classes for s in stop_list):
                            logger.info("[load_and_collect_links] Stop class found on button; stopping.")
                            break

                    with contextlib.suppress(Exception):
                        await btn.scroll_into_view_if_needed(timeout=1000)

                    clicked = False
                    try:
                        await btn.click(timeout=5000)
                        clicked = True
                    except Exception:
                        with contextlib.suppress(Exception):
                            await btn.click(timeout=5000, force=True)
                            clicked = True
                        if not clicked:
                            with contextlib.suppress(Exception):
                                handle = await btn.element_handle()
                                if handle:
                                    await page.evaluate("(el)=>el.click()", handle)
                                    clicked = True

                    if not clicked:
                        logger.info("[load_and_collect_links] Could not click load-more button; stopping.")
                        break

                    # wait for new cards after click
                    before = current_count
                    grew = False
                    for i in range(6):
                        await page.wait_for_timeout(wait_after_click * (i + 1))
                        with contextlib.suppress(Exception):
                            await page.wait_for_load_state("networkidle", timeout=2500)
                        cnt = await page.locator(article_selector).count()
                        if cnt > before:
                            current_count = cnt
                            loads += 1
                            grew = True
                            made_progress = True
                            logger.debug(f"[load_and_collect_links] Click load #{loads}: {current_count} cards")
                            break

                    if not grew:
                        # optional tiny nudge scroll after click
                        await page.evaluate(
                            "()=>{const el=document.scrollingElement||"
                            "document.documentElement||document.body;"
                            "el.scrollBy(0, window.innerHeight*0.9);"
                            "window.dispatchEvent(new Event('scroll'));}"
                        )
                        await page.mouse.wheel(0, 1200)
                        await page.wait_for_timeout(wait_after_click)
                        with contextlib.suppress(Exception):
                            await page.wait_for_load_state("networkidle", timeout=2500)
                        cnt = await page.locator(article_selector).count()
                        if cnt > before:
                            current_count = cnt
                            loads += 1
                            made_progress = True
                            logger.debug(f"[load_and_collect_links] Post-click scroll load #{loads}: {current_count} cards")

                    if max_loads is not None and loads >= int(max_loads):
                        break
                else:
                    # no button present
                    if not made_progress:
                        # no scroll progress + no button = plateau
                        break

                # If neither scroll nor click produced new cards, we’re done.
                if not made_progress:
                    break

            content = await page.content()
            await ctx.close()
            await browser.close()
            logger.info(f"[load_and_collect_links] Finished {url} with {current_count} cards and {loads} loads.")
            return content


    @staticmethod
    async def fetch_page_with_playwright(url, timeout_time=60000, wait_time=2000):
        """
        Uses Playwright to fetch a single fully rendered page without any
        scrolling or pagination interaction.

        The function:
            1. Launches a headless Chromium browser.
            2. Navigates to `url` with a configurable timeout.
            3. Waits for `domcontentloaded` and then an extra fixed delay
               (`wait_time`) to allow client-side JavaScript to finish.
            4. Returns the final HTML markup of the page.

        If navigation fails (e.g., timeout, network error), a warning is logged and
        an empty string is returned instead of raising an exception.

        Args:
            url (str): The URL of the page to fetch.
            timeout_time (int, optional): Maximum time in milliseconds to wait for
                the initial navigation to complete (default: 60000).
            wait_time (int, optional): Additional wait time in milliseconds after
                `domcontentloaded` before capturing the page content (default: 2000).

        Returns:
            str: The HTML content of the page after load and wait. If the page cannot
            be loaded, an empty string is returned.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout_time, wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"Failed to load {url}: {e}")
                await browser.close()
                return ""
            await page.wait_for_timeout(wait_time)
            content = await page.content()
            await browser.close()
            return content

