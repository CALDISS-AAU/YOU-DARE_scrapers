### IMPORTS ###
# External imports #
import scrapy
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re, gzip, io, xml.etree.ElementTree as ET
import httpx
from playwright.async_api import async_playwright
from playwright.async_api import Error as PWError
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.dynamic_scroll_scrapy_functions import Dynamic_Scroll_Scrapy  # Custom shared functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers-folder
        scrapy crawl gb_news_SPIDER -a max_scrolls=x # MUST MATCH SPIDER NAME!
    where -a max_scrolls=x is an optional parameter to limit the number of scrolls to render more articles on the front page
    OR
        cd ./path/to/YOU-DARE_scrapers-folder
        mkdir -p ./data/United_Kingdom/gb_news_SPIDER # If the folder does not yet exist
        nohup scrapy crawl gb_news_SPIDER > ./data/United_Kingdom/gb_news_SPIDER/gb_news_SPIDER_$(date +%F).log
'''

### SPIDER ###
class DynamicSpider(scrapy.Spider):
    name = 'gb_news_SPIDER'
    region = 'United_Kingdom'
    source = 'GB news - opinion'
    start_urls = ['https://www.gbnews.com/opinion/']
    
    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_css') and 'some_xpath' must use response.xpath('some_xpath')
        For clarrification:
            Front page referes to the first site the spider encounters after following the start_urls
            Article page referes to the site of each individual article
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            articles_CSS # The outer container of each article used to determine when to stop scrolling (when no more articles are rendered after as scroll -> stop)
            links_to_follow # The links to the individual articles
    '''
    links_to_follow_CSS = 'a[href*="/opinion/"]::attr(href)'
    articles_CSS = 'article .widget__head>a'
    # FROM THE ARTICLE PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual article pages.
    '''
    article_title_CSS = 'h1 *::text'
    publication_date_XPATH = 'normalize-space(substring-after(string(//*[contains(@class,"custom-dates")]//p[contains(@class,"created-date")]), "Published: "))'
    author_CSS = '.custom-author__name-desc a::text'
    article_categories_CSS = None
    article_text_XPATH = (
        '//div[contains(@class, "body-description")]//p['
        'not(ancestor::*[contains(@class, "image-media") or '
        'contains(@class, "conversation-starter-wrapper") or '
        'contains(@class, "media-caption") or '
        'contains(@class, "trending-item")])]/text()[normalize-space()!="GB NEWS"]'
        ' | //h2[contains(concat(" ", normalize-space(@class), " "), " widget__subheadline-text ")]//text()[normalize-space()!="GB NEWS"]'
        ' | //h2[contains(concat(" ", normalize-space(@class), " "), " widget__subheadline-text ")]/following-sibling::*[1][self::p]//text()[normalize-space()!="GB NEWS"]'
    )
    image_links_CSS = []
    embedded_media_links_CSS = '.body-description iframe::attr(src)'
    links_in_text_XPATH = '//div[contains(@class, "body-description")]//p[' \
        'not(ancestor::*[contains(@class, "image-media") or ' \
        'contains(@class, "conversation-starter-wrapper") or ' \
        'contains(@class, "media-caption") or ' \
        'contains(@class, "trending-item") or ' \
        'contains(@class, "posts-wrapper")])]' \
        '//a/@href'
    other_items = None

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_scrolls=None):
        super().__init__()
        Dynamic_Scroll_Scrapy.initialize(self, max_scrolls)
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scroll_Scrapy.setup_from_crawler(spider, crawler)
        return spider
    
    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_links = Dynamic_Scroll_Scrapy.load_existing_links(self.save_path)

    # ---------- tiny, focused helpers (added) ----------
    def _clean_url(self, s: str) -> str:
        return (s or '').strip().rstrip('"\'),.>} ')
    async def _goto_with_dns_retries(self, page, url, attempts=4, base_delay=1.0):
        url = (url or '').strip()
        last_exc = None
        for i in range(attempts):
            try:
                return await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except PWError as e:
                msg = str(e)
                last_exc = e
                if ("ERR_NAME_NOT_RESOLVED" in msg) or ("ERR_INTERNET_DISCONNECTED" in msg):
                    if i < attempts - 1:
                        await asyncio.sleep(base_delay * (2 ** i))
                        continue
                break
        raise last_exc

    # ---------- site/url helpers ----------
    def _is_opinion_url(self, s: str) -> bool:
        if not s:
            return False
        s = s.strip().rstrip('"\'),.>} ')
        if "/opinion/" not in s:
            return False
        if s.endswith('/opinion') or s.endswith('/opinion/'):
            return False
        if s.startswith("https://www.gbnews.com/opinion/"):
            return True
        if s.startswith("/opinion/"):
            return True
        return False
    def _abs(self, base: str, s: str) -> str:
        s = (s or '').strip().rstrip('"\'),.>} ')
        return s if s.startswith('http') else urljoin(base, s)
    def _harvest_json_links(self, base_url: str, data, out_set: set):
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
            elif isinstance(cur, str) and self._is_opinion_url(cur):
                out_set.add(self._abs(base_url, cur))

    async def _sitemap_sweep(self, page, base_url: str, max_docs: int = 3000) -> set:
        host = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        seen_docs = set()
        found = set()
        async def fetch_bytes(u):
            try:
                r = await page.request.get(u, timeout=25000)
                if not r.ok: return None, {}
                body = await r.body()
                return body, {k.lower(): v for k, v in r.headers.items()}
            except:
                return None, {}
        def maybe_decompress(content: bytes, hdrs: dict, url: str) -> bytes:
            try:
                ct = hdrs.get('content-type', '')
                if 'gzip' in ct or url.endswith('.gz'):
                    return gzip.decompress(content)
            except:
                pass
            return content
        robots = f"{host}/robots.txt"
        sitemap_candidates = set()
        body, _ = await fetch_bytes(robots)
        if body:
            txt = body.decode('utf-8', 'ignore')
            for line in txt.splitlines():
                if line.lower().startswith('sitemap:'):
                    sm = line.split(':', 1)[1].strip()
                    if sm:
                        sitemap_candidates.add(sm)
        sitemap_candidates.update({
            f"{host}/sitemap.xml",
            f"{host}/sitemap_index.xml",
            f"{host}/sitemap.xml.gz",
            f"{host}/sitemap-index.xml",
            f"{host}/sitemaps/sitemap.xml",
            f"{host}/news-sitemap.xml",
        })
        queue = list(sitemap_candidates)
        while queue and len(seen_docs) < max_docs:
            sm_url = queue.pop(0)
            if sm_url in seen_docs:
                continue
            seen_docs.add(sm_url)
            body, hdrs = await fetch_bytes(sm_url)
            if not body:
                continue
            body = maybe_decompress(body, hdrs, sm_url)
            try:
                it = ET.iterparse(io.BytesIO(body))
                for _, el in it:
                    if '}' in el.tag:
                        el.tag = el.tag.split('}', 1)[1]
                root = it.root
            except:
                txt = body.decode('utf-8', 'ignore')
                for m in re.findall(r'https?://www\.gbnews\.com/opinion/[^\s<>"\']+', txt, flags=re.I):
                    found.add(m.rstrip('"\'),.>} '))
                continue
            tag = (root.tag or '').lower()
            if tag == 'sitemapindex':
                for sm in root.findall('.//sitemap'):
                    loc_el = sm.find('loc')
                    if loc_el is not None and loc_el.text:
                        queue.append(loc_el.text.strip())
            elif tag == 'urlset':
                for u in root.findall('.//url'):
                    loc_el = u.find('loc')
                    if loc_el is None or not loc_el.text:
                        continue
                    loc = loc_el.text.strip()
                    if self._is_opinion_url(loc):
                        found.add(self._abs(base_url, loc))
            else:
                txt = body.decode('utf-8', 'ignore')
                for m in re.findall(r'https?://www\.gbnews\.com/opinion/[^\s<>"\']+', txt, flags=re.I):
                    found.add(m.rstrip('"\'),.>} '))
        return found

    async def _fetch_all_listing_links(self, url: str, plateau_loops: int = 16) -> list[str]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 2400},
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36")
            )
            page = await context.new_page()
            net_seen = set()
            async def process_response(resp):
                try:
                    if resp.status != 200:
                        return
                    ctype = (resp.headers.get("content-type") or "").lower()
                    req_url = resp.url
                    if "json" in ctype:
                        try:
                            data = await resp.json()
                        except:
                            data = None
                        if data is not None:
                            self._harvest_json_links(req_url, data, net_seen)
                            return
                    if ("html" in ctype) or ("text/" in ctype):
                        try:
                            body = await resp.text()
                        except:
                            body = ""
                        if body:
                            for m in re.findall(r'https?://www\.gbnews\.com/opinion/[a-z0-9/_\-]+', body, flags=re.I):
                                if self._is_opinion_url(m):
                                    net_seen.add(m.rstrip('"\'),.>} '))
                            for m in re.findall(r'"/opinion/[a-z0-9/_\-]+"', body, flags=re.I):
                                m = m.strip('"')
                                if self._is_opinion_url(m):
                                    net_seen.add(self._abs(req_url, m))
                except:
                    pass
            page.on("response", lambda r: asyncio.create_task(process_response(r)))
            await self._goto_with_dns_retries(page, url)
            try:
                for sel in [
                    '#onetrust-accept-btn-handler',
                    'button:has-text("Accept All")',
                    '.ot-sdk-container button:has-text("Accept")',
                    'button:has-text("I Accept")',
                    'button:has-text("Agree")'
                ]:
                    try:
                        await page.locator(sel).click(timeout=1200); break
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
            await page.evaluate("""
                () => {
                  const toAbs = (a) => new URL(a.getAttribute('href'), location.href).href;
                  const good = (href) => {
                    if (!href) return false;
                    if (!href.includes('/opinion/')) return false;
                    const clean = href.replace(location.origin, '');
                    if (clean === '/opinion' || clean === '/opinion/') return false;
                    return true;
                  };
                  window.__SEEN_HREFS = new Set();
                  const anchors = Array.from(document.querySelectorAll('a[href*="/opinion/"]'));
                  for (const a of anchors) {
                    const href = a.getAttribute('href') || '';
                    if (good(href)) window.__SEEN_HREFS.add(toAbs(a));
                  }
                }
            """)
            async def collect_dom_hrefs():
                try:
                    await page.evaluate("""
                        () => {
                          const toAbs = (a) => new URL(a.getAttribute('href'), location.href).href;
                          const good = (href) => {
                            if (!href) return false;
                            if (!href.includes('/opinion/')) return false;
                            const clean = href.replace(location.origin, '');
                            if (clean === '/opinion' || clean === '/opinion/') return false;
                            return true;
                          };
                          const anchors = Array.from(document.querySelectorAll('a[href*="/opinion/"]'));
                          for (const a of anchors) {
                            const href = a.getAttribute('href') || '';
                            if (good(href)) window.__SEEN_HREFS.add(toAbs(a));
                          }
                        }
                    """)
                    return await page.evaluate("Array.from(window.__SEEN_HREFS || [])")
                except:
                    return []
            async def nudge_last():
                try:
                    loc = page.locator('a[href*="/opinion/"]').last
                    await loc.scroll_into_view_if_needed()
                    await page.wait_for_timeout(120)
                except:
                    pass
            last_total = 0
            plateau = 0
            i = 0
            maxs = 1800
            while i < maxs:
                i += 1
                try:
                    await page.evaluate("""
                        () => {
                          const el = document.scrollingElement || document.documentElement || document.body;
                          el.scrollTop = el.scrollHeight;
                          window.scrollTo(0, document.body.scrollHeight);
                          window.dispatchEvent(new Event('scroll'));
                          window.dispatchEvent(new Event('resize'));
                          el.dispatchEvent(new Event('scroll', {bubbles:true}));
                        }
                    """)
                except:
                    pass
                await page.mouse.wheel(0, 1800)
                await page.keyboard.press("End")
                await nudge_last()
                for btn_sel in [
                    'button:has-text("Load more")','button:has-text("Show more")','button:has-text("More stories")',
                    'a:has-text("Load more")','a:has-text("Show more")','a:has-text("More stories")',
                    '[aria-label="Load more"]','[data-test="load-more"]','[data-testid="load-more"]'
                ]:
                    try:
                        btn = page.locator(btn_sel)
                        if await btn.is_visible():
                            await btn.click(); await page.wait_for_timeout(800)
                    except:
                        pass
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)
                except:
                    pass
                await page.wait_for_timeout(250)
                dom_links = await collect_dom_hrefs()
                total_now = len(net_seen | set(dom_links))
                if total_now <= last_total:
                    plateau += 1
                    if plateau >= plateau_loops:
                        break
                else:
                    plateau = 0
                    last_total = total_now
            dom_links = await collect_dom_hrefs()
            scrolled = set(dom_links) | net_seen
            try:
                sitemap_links = await self._sitemap_sweep(page, url, max_docs=5000)
            except Exception:
                sitemap_links = set()
            union_links = sorted({
                u for u in (scrolled | sitemap_links)
                if u.startswith('https://www.gbnews.com/opinion/')
            })
            await context.close()
            await browser.close()
            return union_links

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    @inlineCallbacks
    def parse(self, response):
        url = response.url
        # 1) Get all opinion article URLs (Playwright + sitemap)
        links = yield deferToThread(
            asyncio.run,
            self._fetch_all_listing_links(url, plateau_loops=16)
        )

        self.logger.info(f"Found {len(links)} article links on {url}")

        collected_items = []

        # 2) For each article URL: fetch page and parse
        for link in links:
            if link in self.existing_links:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue

            article_page = yield deferToThread(
                asyncio.run,
                Dynamic_Scroll_Scrapy.fetch_with_playwright(
                    link, 
                    # max_scrolls=10, # default value = None, set to value if the scrolls on each article should be limited
                    wait_time=5000 # default value = 2000, increase if needed
                )
            )
            article_sel = Selector(text=article_page)

            item = self.parse_article(article_sel, link)
            if item:
                collected_items.append(item)

        returnValue(collected_items)

    def parse_article(self, response, article_link):
        # Extract 'timestamp' 
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'article_title' 
        article_title = response.css(self.article_title_CSS).get()
        article_title_clean = General_Functions.clean_text(article_title) if article_title else None
        # Extract 'publication_date'
        publication_date = response.xpath(self.publication_date_XPATH).re_first(r'(\d{2}/\d{2}/\d{4})')
        # Extract 'author' 
        author = response.css(self.author_CSS).get()
        author_clean = General_Functions.clean_text(author) if author else None
        # Extract 'article_categories' 
        article_categories = self.article_categories_CSS
        # Extract 'article_text' 
        article_text_bits = response.xpath(self.article_text_XPATH).getall()
        article_text_clean = General_Functions.join_and_clean(article_text_bits)
        # Extract 'image_links'
        image_links = self.image_links_CSS
        # Extract 'embedded_media_links'
        embedded_media_links = response.css(self.embedded_media_links_CSS).getall()
        # Extract 'links_in_text'
        links_in_text = response.xpath(self.links_in_text_XPATH).getall()
        # Extract 'other_items' 
        other_items = self.other_items
        #Extract 'article HTML'
        article_HTML = response.get()
        
        items = ScrapersItem() # Makes the items from items.py accessable within this spider for every single article

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['source'] = source
        items['article_link'] = article_link
        items['article_title'] = article_title_clean
        items['publication_date'] = publication_date
        items['author'] = author_clean
        items['article_categories'] = article_categories
        items['article_text'] = article_text_clean
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_media_links
        items['links_in_text'] = links_in_text
        items['other_items'] = other_items
        items['article_HTML'] = article_HTML
        
        self.logger.info(f"Scraped article: {article_title} ({article_link})") # Logs successful scrape
        
        self.existing_links.add(article_link) # Adds article to list of scraped articles just in case multiple links from the front page directs to this article

        return items # returns the items to parse