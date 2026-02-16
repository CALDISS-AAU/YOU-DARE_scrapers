# '''
# You first need to install:
# pip install scrapy-playwright
# playwright install chromium

# before calling:
# scrapy crawl fidesz_videos_SPIDER
# '''

# version: 2025-08-20
import os
import scrapy
from urllib.parse import urlparse
from scrapy_playwright.page import PageMethod

class fidesz_videos_SPIDER(scrapy.Spider):
    name = "fidesz_videos_SPIDER"
    allowed_domains = ["fidesz.hu"]
    region = "Hungary"
    TARGET_PATH = "/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_SPIDER/data_fidesz_videos_SPIDER.txt"

    custom_settings = {
        "FEEDS": {},  # we write our own txt
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 15000,
        "PLAYWRIGHT_DEFAULT_TIMEOUT": 10000,
        "DOWNLOAD_TIMEOUT": 30,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "Mozilla/5.0 (compatible; fidesz_videos_SPIDER/1.0; +https://example.com/bot)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 0.5,
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 2,
        "RETRY_ENABLED": False,
        "LOG_LEVEL": "INFO",
        "TELNETCONSOLE_ENABLED": False,
        # Optional: auto-stop if it idles too long
        # "CLOSESPIDER_TIMEOUT": 5400,
    }

    def _is_facebook(self, url: str) -> bool:
        h = urlparse(url).netloc.lower()
        blocked = ("facebook.com", "fbcdn.net", "connect.facebook.net", "staticxx.facebook.com")
        return any(h == d or h.endswith("." + d) for d in blocked)

    async def start(self):
        os.makedirs(os.path.dirname(self.TARGET_PATH), exist_ok=True)
        # line-buffered writes so tail -f sees updates immediately
        self.out = open(self.TARGET_PATH, "w", encoding="utf-8", buffering=1)
        self.seen = set()
        base = "https://fidesz.hu/videok?page="
        for i in range(20, 234):
            yield scrapy.Request(
                f"{base}{i}",
                callback=self.parse_list,
                meta={"playwright": True, "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod("wait_for_selector", ".video-item, .video-title", timeout=5000),
                ]},
            )

    async def parse_list(self, response):
        hrefs = response.css(".video-item .video-title a::attr(href)").getall()
        if not hrefs: hrefs = response.css('a[href^="/videok/"]::attr(href)').getall()
        seen_local = set()
        for h in hrefs:
            if h and h not in seen_local:
                seen_local.add(h)
                url = response.urljoin(h)
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [PageMethod("wait_for_load_state", "domcontentloaded")],
                        "download_timeout": 30,
                    },
                )

    async def parse_detail(self, response):
        page = response.meta["playwright_page"]
        try:
            await page.wait_for_timeout(300)
            try:
                await page.locator("div.video-wrapper").first.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
            clicked = False
            for sel in ("div.video--play button", ".video button", "div.video-wrapper button", ".video-item button", "button"):
                try:
                    loc = page.locator(sel).first
                    if await loc.count():
                        try: await loc.scroll_into_view_if_needed()
                        except Exception: pass
                        await loc.click(timeout=800)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                try:
                    await page.evaluate("""
                        () => {
                          for (const s of ['div.video--play button', '.video button', 'div.video-wrapper button', '.video-item button', 'button']) {
                            const el = document.querySelector(s);
                            if (el) { el.click(); return true; }
                          }
                          return false;
                        }
                    """)
                except Exception:
                    pass
            try:
                await page.wait_for_selector("iframe[src]", timeout=4000)
            except Exception:
                await page.wait_for_timeout(500)
            try:
                srcs = await page.eval_on_selector_all("iframe[src]", "els => els.map(e => e.src)")
            except Exception:
                srcs = []
        finally:
            try: await page.close()
            except Exception: pass

        wrote = 0
        for raw in srcs or []:
            if not raw: continue
            url = response.urljoin(raw.strip())
            if self._is_facebook(url): continue
            if url not in self.seen:
                self.seen.add(url)
                self.out.write(url + "\n")
                self.out.flush()  # make sure it hits disk
                wrote += 1
        if wrote:
            self.logger.info(f"Wrote {wrote} link(s) from {response.url}")

    def closed(self, reason):
        if hasattr(self, "out"): self.out.close()


