### IMPORTS ###
import scrapy
from scrapy.selector import Selector
import asyncio
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
import re, gzip, io, xml.etree.ElementTree as ET

from ...items import ScrapersItem
from ...functions.scrapy_functions import Dynamic_Scrapy
from playwright.async_api import async_playwright

class DynamicSpider(scrapy.Spider):
    name = 'gb_news_TEST_SPIDER'
    region = 'United_Kingdom'
    source = 'GB news - opinion'
    start_urls = ['https://www.gbnews.com/opinion/']

    # fallback DOM selector (we never block on this)
    links_to_follow_CSS = 'a[href*="/opinion/"]::attr(href)'

    # ---------- small helpers ----------
    def _is_opinion_url(self, s: str) -> bool:
        if not s: return False
        s = s.strip().rstrip('"\'),.>} ')
        if "/opinion/" not in s: return False
        if s.startswith("https://www.gbnews.com/opinion/"): return True
        if s.startswith("/opinion/"): return True
        return False

    def _abs(self, base: str, s: str) -> str:
        s = s.strip().rstrip('"\'),.>} ')
        return s if s.startswith("http") else urljoin(base, s)

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

    # ---------- sitemap sweep (robots.txt → sitemaps → urlsets) ----------
    async def _sitemap_sweep(self, page, base_url: str, max_docs: int = 500) -> set:
        host = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        seen_docs = set()
        found = set()

        async def fetch_bytes(u):
            try:
                r = await page.request.get(u, timeout=20000)
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

        # 1) robots.txt → collect Sitemap: lines
        robots_urls = [f"{host}/robots.txt"]
        sitemap_candidates = set()
        for ru in robots_urls:
            body, hdrs = await fetch_bytes(ru)
            if not body: continue
            txt = body.decode('utf-8', 'ignore')
            for line in txt.splitlines():
                if line.lower().startswith('sitemap:'):
                    sm = line.split(':', 1)[1].strip()
                    if sm:
                        sitemap_candidates.add(sm)

        # 2) add common sitemap locations
        sitemap_candidates.update({
            f"{host}/sitemap.xml",
            f"{host}/sitemap_index.xml",
            f"{host}/sitemap.xml.gz",
            f"{host}/sitemap-index.xml",
            f"{host}/sitemaps/sitemap.xml",
            f"{host}/news-sitemap.xml",
        })

        # 3) BFS through sitemap indexes/urlsets
        queue = list(sitemap_candidates)
        while queue and len(seen_docs) < max_docs:
            sm_url = queue.pop(0)
            if sm_url in seen_docs: continue
            seen_docs.add(sm_url)

            body, hdrs = await fetch_bytes(sm_url)
            if not body: continue
            body = maybe_decompress(body, hdrs, sm_url)

            try:
                # strip namespaces for simpler XPath
                it = ET.iterparse(io.BytesIO(body))
                for _, el in it:
                    if '}' in el.tag:
                        el.tag = el.tag.split('}', 1)[1]
                root = it.root
            except:
                # some sitemaps are text lists; fallback regex harvest
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
                    if loc_el is not None and loc_el.text:
                        loc = loc_el.text.strip()
                        if self._is_opinion_url(loc):
                            found.add(self._abs(base_url, loc))
            else:
                # unknown type; regex fallback
                txt = body.decode('utf-8', 'ignore')
                for m in re.findall(r'https?://www\.gbnews\.com/opinion/[^\s<>"\']+', txt, flags=re.I):
                    found.add(m.rstrip('"\'),.>} '))

        return found

    # ---------- main listing fetch (scroll + sniff + sitemap fallback) ----------
    async def _gbnews_fetch_listing(self, url, plateau_loops=14):
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
            captured_json = []

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
                            captured_json.append((req_url, data))
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

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # cookie/modal cleanup (best-effort)
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
                    except: pass
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

            # DOM ever-seen
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

            # ---- scroll pass (discover + sniff) ----
            last_total = 0
            plateau = 0
            i = 0
            maxs = 1800  # generous, no need to pass -a max_scrolls

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

                # tap common load-more controls
                for btn_sel in [
                    'button:has-text("Load more")','button:has-text("Show more")','button:has-text("More stories")',
                    'a:has-text("Load more")','a:has-text("Show more")','a:has-text("More stories")',
                    '[aria-label="Load more"]','[data-test="load-more"]','[data-testid="load-more"]'
                ]:
                    try:
                        btn = page.locator(btn_sel)
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(800)
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

            html = await page.content()
            dom_links = await collect_dom_hrefs()
            scrolled_links = set(dom_links) | net_seen

            # ---- sitemap fallback (to break past virtualization caps) ----
            try:
                sitemap_links = await self._sitemap_sweep(page, url, max_docs=600)
            except Exception:
                sitemap_links = set()

            union_links = sorted({u for u in (scrolled_links | sitemap_links) if u.startswith('https://www.gbnews.com/opinion/')})

            await context.close()
            await browser.close()
            return html, union_links

    def __init__(self, max_scrolls=None):
        super().__init__()
        Dynamic_Scrapy.initialize(self, max_scrolls)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DynamicSpider, cls).from_crawler(crawler, *args, **kwargs)
        Dynamic_Scrapy.setup_from_crawler(spider, crawler)
        return spider

    def open_spider(self, spider):
        self.logger.info("open_spider() is running!")
        self.existing_data = Dynamic_Scrapy.load_existing_links(self.save_path)

    @inlineCallbacks
    def parse(self, response):
        url = response.url
        rendered_page, discovered_links = yield deferToThread(
            asyncio.run,
            self._gbnews_fetch_listing(url, plateau_loops=16)
        )

        links = list(dict.fromkeys(discovered_links or []))
        self.logger.info(f"final_link_count={len(links)}")
        for link in links:
            self.logger.debug(f"Article link: {link}")

        # Emit links as items (test mode)
        items = []
        for link in links:
            if link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {link}")
                continue
            it = ScrapersItem()
            it['article_link'] = link
            items.append(it)
            self.existing_data.add(link)

        returnValue(items)
