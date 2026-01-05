import os
import json
from urllib.parse import urlparse 
from scrapy import signals
from playwright.async_api import async_playwright
import asyncio
from typing import Union, List, Dict, Optional, Any, Set, Tuple
import logging
import contextlib

logger = logging.getLogger(__name__)

class Dynamic_Click_Scrapy:
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
        spider.save_path = Dynamic_Click_Scrapy.get_feed_output_path(
            settings=crawler.settings,
            name=spider.name,
            region=spider.region
        )

    @staticmethod
    def initialize(spider, max_clicks=None):
        """
        Initializes the spider with optional maximum click limit and default attributes.

        Args:
            spider (scrapy.Spider): The spider instance to initialize.
            max_clicks (int, optional): Optional limit for the number of clicks to scrape.
        """
        spider.max_clicks = int(max_clicks) if max_clicks else None
        spider.existing_data = set()
        spider.save_path = f"./data/{spider.name}/data_{spider.name}.jl"

    ## FUNCTIONALITY FUNCTIONS ##
    @staticmethod
    async def click_and_collect_links(
        url: str,
        click_button_selector: str,
        links_selector: Optional[str] = None,
        max_clicks: Optional[int] = None,
        wait_time: int = 2000,
        timeout_time: int = 30000,
        stop_when_button_has_class: Optional[str] = None,
        *,
        stop_when_button_has_class_attr: Union[str, List[str], None] = None,
        consent_selectors: Optional[List[str]] = None,
        pagination_navigates: bool = False,
        incremental_retries: int = 5
    ):
        """
        Clicks a "load more" / pagination button repeatedly and collects unique links from the page.

        The function opens `url` in headless Chromium, optionally dismisses cookie/consent popups,
        then performs a click loop:
        - After each click, it waits incrementally (`wait_time` * retry_index) up to
          `incremental_retries` times to allow JS-rendered content to appear.
        - Links are extracted via `links_selector` and normalized to absolute URLs.
        - The loop stops when:
            * `max_clicks` is reached,
            * no button is found or the button becomes hidden,
            * a stop selector is matched (`stop_when_button_has_class`),
            * the button's class attribute contains a stop class
              (`stop_when_button_has_class_attr`),
            * or a click produces no new links after retries.

        Selectors may be CSS or raw XPath. Raw XPath is auto-detected and routed through
        Playwright's XPath locator.

        Args:
            url (str): The starting page URL to open.
            click_button_selector (str): CSS or XPath selector for the "load more" button.
                If multiple match, the last match is used.
            links_selector (str, optional): CSS or XPath selector for link elements to collect.
                Must be provided for this links-only variant.
            max_clicks (int, optional): Maximum number of clicks to perform. None for unlimited.
            wait_time (int, optional): Base wait time (ms) between click and extraction retries.
            timeout_time (int, optional): Navigation timeout for the initial page load, in ms.
            stop_when_button_has_class (str, optional): Selector whose presence indicates the
                pagination should stop (e.g., a disabled button state element).
            stop_when_button_has_class_attr (str | list[str], optional): One or more class-name
                fragments that, if found on the button itself, will stop pagination.
            consent_selectors (list[str], optional): Custom selectors for cookie/consent buttons.
                If None, a small default list is used.
            pagination_navigates (bool, optional): If True, treat each click as a navigation
                and wait for DOMContentLoaded after click.
            incremental_retries (int, optional): Number of incremental waits after each click
                before deciding that no new links appeared.

        Returns:
            list[str]: A list of unique absolute URLs collected across all clicks.

        Raises:
            ValueError: If `links_selector` is not provided.
        """
        if not links_selector:
            raise ValueError("links_selector is required for this links-only version.")
        cookie_selectors = consent_selectors or [
            "#onetrust-accept-btn-handler",
            "button:has-text('Elfogad')",
            "button:has-text('elfogad')",
            "button:has-text('Accept')",
            "button:has-text('Rendben')",
            ".cm-btn-accept",
        ]
        from urllib.parse import urljoin
        def _loc(page_or_locator, sel: str):
            s = sel.strip()
            if s.startswith("//") or s.startswith("(//") or s.startswith(".//"):
                return page_or_locator.locator(f"xpath={s}")
            return page_or_locator.locator(s)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=timeout_time, wait_until="domcontentloaded")
            logger.info(f"Opened {url}")
            for sel in cookie_selectors:
                with contextlib.suppress(Exception):
                    btn = page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click()
                        logger.info(f"Dismissed consent via selector: {sel}")
                        break
            hrefs_seen: Set[str] = set()
            async def collect_links_into_seen() -> int:
                raw = await _loc(page, links_selector).evaluate_all(
                    "els => els.map(el => el.href || el.getAttribute('href'))"
                )
                added = 0
                for h in raw:
                    if not h:
                        continue
                    abs_h = urljoin(page.url, h)
                    if abs_h not in hrefs_seen:
                        hrefs_seen.add(abs_h)
                        added += 1
                return added
            await collect_links_into_seen()
            click_num = 0
            while True:
                if max_clicks is not None and click_num >= int(max_clicks):
                    logger.info("Reached max_clicks limit.")
                    break
                buttons = _loc(page, click_button_selector)
                if await buttons.count() == 0:
                    logger.info("No 'Load more' button found.")
                    break
                button_loc = buttons.last
                if stop_when_button_has_class and await _loc(page, stop_when_button_has_class).count() > 0:
                    logger.info("Stop selector matched; stopping.")
                    break
                if stop_when_button_has_class_attr:
                    with contextlib.suppress(Exception):
                        handle = await button_loc.element_handle()
                        if handle:
                            cls = (await handle.get_attribute("class")) or ""
                            stop_classes = (
                                [stop_when_button_has_class_attr]
                                if isinstance(stop_when_button_has_class_attr, str)
                                else stop_when_button_has_class_attr
                            )
                            if any(s in cls for s in stop_classes):
                                logger.info(f"Button has stop class in {stop_classes}; stopping.")
                                break
                with contextlib.suppress(Exception):
                    await button_loc.scroll_into_view_if_needed(timeout=1000)
                try:
                    visible = await button_loc.is_visible()
                except Exception:
                    visible = False
                if not visible:
                    logger.info("Load more button present but hidden; assuming end of feed.")
                    break
                clicked = False
                try:
                    if pagination_navigates:
                        await asyncio.gather(
                            button_loc.click(timeout=5000),
                            page.wait_for_load_state("domcontentloaded"),
                        )
                    else:
                        await button_loc.click(timeout=5000)
                    clicked = True
                except Exception as e1:
                    logger.info(f"Normal click failed ({e1}). Trying force/JS fallback.")
                    try:
                        if pagination_navigates:
                            await asyncio.gather(
                                button_loc.click(timeout=5000, force=True),
                                page.wait_for_load_state("domcontentloaded"),
                            )
                        else:
                            await button_loc.click(timeout=5000, force=True)
                        clicked = True
                    except Exception:
                        with contextlib.suppress(Exception):
                            handle = await button_loc.element_handle()
                            if handle:
                                if pagination_navigates:
                                    await asyncio.gather(
                                        page.evaluate("(el)=>el.click()", handle),
                                        page.wait_for_load_state("domcontentloaded"),
                                    )
                                else:
                                    await page.evaluate("(el)=>el.click()", handle)
                                clicked = True
                if not clicked:
                    break
                before = len(hrefs_seen)
                retries = max(1, int(incremental_retries))
                new_links_total = 0
                total_wait_ms = 0

                for r in range(retries):
                    delay = wait_time * (r + 1)
                    total_wait_ms += delay
                    await page.wait_for_timeout(delay)

                    added_now = await collect_links_into_seen()
                    new_links_total += added_now

                    if added_now > 0:
                        logger.info(
                            f"[Click #{click_num + 1}] New links after retry {r + 1}: "
                            f"{added_now} (total {len(hrefs_seen)}; waited {total_wait_ms/1000:.1f}s)"
                        )
                        break
                    else:
                        logger.info(
                            f"[Click #{click_num + 1}] No new links after retry {r + 1}/{retries} "
                            f"(total wait {total_wait_ms/1000:.1f}s)."
                        )

                after = len(hrefs_seen)
                if not pagination_navigates and after == before:
                    logger.info("No new items detected after click (after retries). Exiting.")
                    break

                click_num += 1
            await browser.close()
            logger.info(f"Total unique links: {len(hrefs_seen)}")
            return list(hrefs_seen)

    @staticmethod
    async def click_and_collect_links_and_publication_dates(
        url: str,
        click_button_selector: str,
        container_selector: str,
        link_selector: str,
        publication_date_selector: str,
        max_clicks: Optional[int] = None,
        wait_time: int = 2000,
        stop_when_button_has_class: Optional[str] = None,
        *,
        stop_when_button_has_class_attr: Union[str, List[str], None] = None,
        consent_selectors: Optional[List[str]] = None,
        pagination_navigates: bool = False,
        incremental_retries: int = 3
    ):
        """
        Clicks a "load more" / pagination button repeatedly and collects links with publication dates.

        This helper opens `url` in headless Chromium, optionally dismisses cookie/consent popups,
        then runs a click loop:
        - After each click, it waits incrementally to allow JS-rendered content to appear.
        - For every element matching `container_selector`, it extracts:
            * a link from `link_selector` (href normalized to an absolute URL),
            * a publication date from `publication_date_selector` (text, stripped).
        - Results are deduplicated by link.
        - The loop stops when:
            * `max_clicks` is reached,
            * no button is found or the button becomes hidden,
            * a stop selector is matched (`stop_when_button_has_class`),
            * the button's class attribute contains a stop class
              (`stop_when_button_has_class_attr`),
            * or a click produces no new links.

        Selectors may be CSS or raw XPath. Raw XPath is auto-detected and routed through
        Playwright's XPath locator.

        Args:
            url (str): The starting page URL to open.
            click_button_selector (str): CSS or XPath selector for the "load more" button.
                If multiple match, the last match is used.
            container_selector (str): Selector for the outer container holding an item
                (e.g., an article card).
            link_selector (str): Selector (relative to each container) for the link element.
            publication_date_selector (str): Selector (relative to each container) for the
                publication date element.
            max_clicks (int, optional): Maximum number of clicks to perform. None for unlimited.
            wait_time (int, optional): Base wait time (ms) between click and extraction retries.
            stop_when_button_has_class (str, optional): Selector whose presence indicates
                pagination should stop (e.g., a disabled-state element).
            stop_when_button_has_class_attr (str | list[str], optional): One or more class-name
                fragments that, if found on the button itself, will stop pagination.
            consent_selectors (list[str], optional): Custom selectors for cookie/consent buttons.
                If None, a small default list is used.
            pagination_navigates (bool, optional): If True, treat each click as a navigation
                and wait for DOMContentLoaded after click.
            incremental_retries (int, optional): Number of incremental waits after each click
                before collecting containers again.

        Returns:
            list[dict]: A list of dictionaries with keys:
                - "link" (str): Absolute URL of the item.
                - "publication_date" (str | None): Extracted date text, if found.
        """
        if not container_selector or not link_selector or not publication_date_selector:
            raise ValueError("container_selector, link_selector and publication_date_selector are all required.")

        cookie_selectors = consent_selectors or [
            "#onetrust-accept-btn-handler",
            "button:has-text('Elfogad')",
            "button:has-text('elfogad')",
            "button:has-text('Accept')",
            "button:has-text('Rendben')",
            ".cm-btn-accept",
        ]

        from urllib.parse import urljoin

        def _loc(page_or_locator, sel: str):
            """
            Accept CSS or XPath. If it looks like XPath, prefix for Playwright.
            Examples:
              - "//div[@class='card']"
              - ".//a"
              - "a.card-link"
            """
            s = sel.strip()
            if s.startswith("//") or s.startswith("(//") or s.startswith(".//"):
                return page_or_locator.locator(f"xpath={s}")
            return page_or_locator.locator(s)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            logger.info(f"Opened {url}")

            # Dismiss consent if present
            for sel in cookie_selectors:
                with contextlib.suppress(Exception):
                    btn = page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click()
                        logger.info(f"Dismissed consent via selector: {sel}")
                        break

            entries: List[Dict[str, Any]] = []
            links_seen: Set[str] = set()  # dedupe by link

            async def collect_entries_into_list() -> int:
                containers = _loc(page, container_selector)
                n = await containers.count()
                added = 0
                logger.info(f"Collecting from {n} containers on {page.url}")

                for i in range(n):
                    c = containers.nth(i)
                    try:
                        # Help lazy-rendered content (like dates)
                        with contextlib.suppress(Exception):
                            await c.evaluate(
                                "node => node.scrollIntoView({behavior: 'instant', block: 'center'})"
                            )
                            await page.wait_for_timeout(100)

                        # Link
                        link_loc = _loc(c, link_selector).first
                        if await link_loc.count() == 0:
                            continue
                        href = await link_loc.get_attribute("href")
                        if not href:
                            continue
                        abs_link = urljoin(page.url, href)

                        # Publication date
                        date_loc = _loc(c, publication_date_selector).first
                        publication_date = None
                        if await date_loc.count() > 0:
                            try:
                                txt = await date_loc.inner_text()
                                publication_date = txt.strip() if txt is not None else None
                            except Exception:
                                publication_date = None

                        if abs_link not in links_seen:
                            links_seen.add(abs_link)
                            entries.append(
                                {
                                    "link": abs_link,
                                    "publication_date": publication_date,
                                }
                            )
                            added += 1
                    except Exception as e:
                        logger.warning(f"Error extracting container #{i+1}: {e}")
                        continue

                return added

            # Initial collection
            await collect_entries_into_list()

            click_num = 0
            while True:
                if max_clicks is not None and click_num >= int(max_clicks):
                    logger.info("Reached max_clicks limit.")
                    break

                buttons = page.locator(click_button_selector)
                if await buttons.count() == 0:
                    logger.info("No 'Load more' button found.")
                    break
                button_loc = buttons.last

                # Old-style stop selector (presence in DOM)
                if stop_when_button_has_class and await page.locator(stop_when_button_has_class).count() > 0:
                    logger.info("Stop selector matched; stopping.")
                    break

                # Stop if button itself has any of the given class names
                if stop_when_button_has_class_attr:
                    with contextlib.suppress(Exception):
                        handle = await button_loc.element_handle()
                        if handle:
                            cls = (await handle.get_attribute("class")) or ""
                            stop_classes = (
                                [stop_when_button_has_class_attr]
                                if isinstance(stop_when_button_has_class_attr, str)
                                else stop_when_button_has_class_attr
                            )
                            if any(s in cls for s in stop_classes):
                                logger.info(f"Button has stop class in {stop_classes}; stopping.")
                                break

                # Ensure button is interactable
                with contextlib.suppress(Exception):
                    await button_loc.scroll_into_view_if_needed(timeout=1000)
                try:
                    visible = await button_loc.is_visible()
                except Exception:
                    visible = False
                if not visible:
                    logger.info("Load more button present but hidden; assuming end of feed.")
                    break

                # Click (and handle navigation if needed)
                clicked = False
                try:
                    if pagination_navigates:
                        await asyncio.gather(
                            button_loc.click(timeout=5000),
                            page.wait_for_load_state("domcontentloaded"),
                        )
                    else:
                        await button_loc.click(timeout=5000)
                    clicked = True
                except Exception as e1:
                    logger.info(f"Normal click failed ({e1}). Trying force/JS fallback.")
                    try:
                        if pagination_navigates:
                            await asyncio.gather(
                                button_loc.click(timeout=5000, force=True),
                                page.wait_for_load_state("domcontentloaded"),
                            )
                        else:
                            await button_loc.click(timeout=5000, force=True)
                        clicked = True
                    except Exception:
                        with contextlib.suppress(Exception):
                            handle = await button_loc.element_handle()
                            if handle:
                                if pagination_navigates:
                                    await asyncio.gather(
                                        page.evaluate("(el)=>el.click()", handle),
                                        page.wait_for_load_state("domcontentloaded"),
                                    )
                                else:
                                    await page.evaluate("(el)=>el.click()", handle)
                                clicked = True

                if not clicked:
                    break

                # Let content render – incremental wait
                retries = max(1, int(incremental_retries))
                for retry in range(retries):
                    await page.wait_for_timeout(wait_time * (retry + 1))

                before = len(links_seen)
                added_now = await collect_entries_into_list()
                after = len(links_seen)
                logger.info(
                    f"[Click #{click_num + 1}] New entries added: {added_now} (total {after})"
                )

                if not pagination_navigates and after == before:
                    logger.info("No new items detected after click. Exiting.")
                    break

                click_num += 1

            await browser.close()
            logger.info(f"Scraping complete. Total entries collected: {len(entries)}.")
            return entries

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
            await page.wait_for_timeout(wait_time) # Just a basic wait to ensure JS finishes
            content = await page.content()
            await browser.close()
            return content
