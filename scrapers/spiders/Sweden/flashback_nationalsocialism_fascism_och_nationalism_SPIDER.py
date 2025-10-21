### IMPORTS ###
# External imports #
import scrapy
import re
from scrapy import signals
from datetime import datetime
import time
import random
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.general_functions import General_Functions  # Custom shared functions
from scrapy.downloadermiddlewares.retry import RetryMiddleware

''' To run this spider pass the following to the terminal:
        cd ./YOU-DARE/scrapers
        scrapy crawl flashback_nationalsocialism_fascism_och_nationalism_SPIDER -a max_pages_posts=x # MUST MATCH SPIDER NAME!
    where -a max_pages=x is an optional parameter
    OR
        cd ./YOU-DARE/scrapers
        mkdir -p /work/YOU-DARE/scrapers/data/Sweden/flashback_nationalsocialism_fascism_och_nationalism_SPIDER # If the folder does not yet exist
        nohup scrapy crawl flashback_nationalsocialism_fascism_och_nationalism_SPIDER > /work/YOU-DARE/scrapers/data/Sweden/flashback_nationalsocialism_fascism_och_nationalism_SPIDER/flashback_nationalsocialism_fascism_och_nationalism_SPIDER_2025-10-10_SPIDER.log
'''

class ExponentialBackoffRetryMiddleware(RetryMiddleware):
    """
    Exponential backoff on retries (blocking sleep).
    - Delay = min(BASE * 2^(retries-1), MAX) with ±JITTER
    - 'retries' is 1-based for the first retry.
    - Lifts the retry cap by inflating max_retry_times unless you set your own.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.base = settings.getint('RETRY_BACKOFF_BASE', 30)  # seconds
        self.max_delay = settings.getint('RETRY_BACKOFF_MAX', 900)  # seconds (15 min)
        self.jitter = float(settings.get('RETRY_BACKOFF_JITTER', 0.3))  # 0..1 (±30%)
        self.retry_forever = settings.getbool('RETRY_FOREVER', True)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def _retry(self, request, reason, spider):
        retries = request.meta.get('retry_times', 0)  # 0 before first retry
        # ensure we don't “run out” of retries if RETRY_FOREVER=True
        if self.retry_forever:
            request.meta['max_retry_times'] = 10**9

        if retries > 0:
            # exponential delay for this retry attempt (1 => base)
            delay = min(self.base * (2 ** (retries - 1)), self.max_delay)
            if self.jitter:
                # apply ±jitter%
                factor = 1 + random.uniform(-self.jitter, self.jitter)
                delay = max(1, int(delay * factor))
            spider.logger.info(f"[{spider.name}] Backing off {delay}s before retry {retries+1} due to {reason}")
            time.sleep(delay)  # blocks this process — simple and robust

        return super()._retry(request, reason, spider)

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'flashback_nationalsocialism_fascism_och_nationalism_SPIDER' # Spider name - must be unique within given project
    region = 'Sweden' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Flashback - nationalsocialism fascism och nationalism' # The source of the articles - NOT the author!
    start_urls = ['https://www.flashback.org/f34-nationalsocialism-fascism-och-nationalism-51006'] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    items = ScrapersItem() # Makes the items from items.py accessable within this spider

    custom_settings = {
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 3,
        'AUTOTHROTTLE_MAX_DELAY': 60,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': True,

        # Let it retry for a long time (you can lower this if you want a hard cap)
        'RETRY_TIMES': 999999,

        # Backoff tuning (adjust to taste)
        'RETRY_BACKOFF_BASE': 30,    # first retry waits ~30s
        'RETRY_BACKOFF_MAX': 900,    # cap wait at 15 min
        'RETRY_BACKOFF_JITTER': 0.3, # ±30% randomness
        'RETRY_FOREVER': True,       # ignore the cap above unless you set it lower

        # Make this middleware active ONLY for this spider:
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            __name__ + '.ExponentialBackoffRetryMiddleware': 550,
        },

        # Ensure 429 is considered retryable (most Scrapy versions already do)
        'RETRY_HTTP_CODES': [500,502,503,504,522,524,408,429],
    }

    ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_css') and 'some_xpath' must use response.xpath('some_xpath')
    '''
    # QUERIES FROM THE POST PAGE!!!
    links_to_follow_posts_XPATH = '//table[@id="threadslist"]//td[contains(@class,"td_title")]/div[1]/a[1]/@href'
    next_page_posts_CSS = 'li.next a::attr(href)'
    # QUERIES FROM THE COMMENT PAGE!!!
    next_page_comments_CSS = 'li.next a::attr(href)'
    post_title_CSS = 'h1 a::text'
    post_publication_date_XPATH = "//*[@id='posts']/*[@class='post'][1]/*[@class='post-heading']/text()" 
    post_author_CSS = '#posts .post .post-user .dropdown strong::text, #posts .post a.post-user-username::text, '
    post_categories_CSS = '.breadcrumb *::text'
    # QUERIES FROM EACH COMMENT!!!
    # comment_publication_date_first_page_XPATH = "//*[@id='posts']/*[@class='post'][position() > 1]/*[@class='post-heading']/text()"
    comments_CSS = '#posts .post'
    comment_publication_date_XPATH = ".//*[@class='post-heading']/text()"
    comment_author_CSS = '.post-user .dropdown strong::text, a.post-user-username::text'
    comment_text_XPATH = ".//div[contains(@class,'post_message')]//text()[not(ancestor::div[contains(@class,'post-bbcode-quote-wrapper')])]"
    comment_external_links_XPATH = ".//div[contains(@class,'post_message')]//a[not(ancestor::div[contains(@class,'post-bbcode-quote-wrapper')])]/@href"
    comment_tag_CSS = 'a.jumptarget::attr(name)'
    comment_cited_tag_CSS = '.post-bbcode-quote-wrapper a[href*="#p"]::attr(href)'
    comment_cited_tag_RE = r'#(p\d+)'
    comment_quote_XPATH = ".//div[contains(@class,'post-bbcode-quote-wrapper')]//text()"

    ### TEST 
    comment_content_nodes_XPATH = ".//div[contains(@class,'post_message')]/node()"
    ###

    # ... other queries

    ### IMPORTANT FUNCTIONS FOR SETUP THAT CANNOT BE OMITTED AND PARAMETERS SHOULD NOT BE CHANGED! ###
    def __init__(self, max_pages_posts=None): # Maybe extend this to mag pages on comments
        """Initializes the spider and sets optional max_pages limit."""
        super().__init__()
        Static_Scrapy.initialize(self, max_pages_posts) # See doc string

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs): 
        """Creates the spider instance from crawler and sets it up."""
        spider = super(StaticSpider, cls).from_crawler(crawler, *args, **kwargs)
        Static_Scrapy.setup_from_crawler(spider, crawler) # See doc string
        return spider

    def open_spider(self, spider):
        """Executes setup actions when the spider is opened."""
        self.logger.info("open_spider() is running!")
        self.seen_links = Static_Scrapy.load_existing_links(self.save_file, self.logger, column='post_link') # See doc string

    def generate_YAML(self, comment_author, comment_date, comment_tag, comment_text, post=False):
        label = 'POST' if post else 'COMMENT'
        return f'\n\n\n---\n{label}: \nAuthor: {comment_author}\nDate: {comment_date}\nTag: {comment_tag}\n---\n{comment_text}'

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    def start_requests(self): # Can't be renamed
        """ Parses all urls from start_url to the parse_post function. """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_posts, # Calls parse_post on each url
                meta={'current_page': 1} # Information sent to parse_post
            )

    def parse_posts(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page_post = response.meta['current_page'] # Saves 'current_page_post' from start_request
        # Finds and follows article links 
        post_links = response.xpath(self.links_to_follow_posts_XPATH).getall() # Gets all article links 
        for partial_link in post_links:
            link = response.urljoin(partial_link)
            if link in self.seen_links: # Only scrapes information from the front page for articles that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate post: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_comments, # Calls parse_comments on each link
                meta={
                    'post_link': link, # Sends the link to parse_comment so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                    'current_page': 1
                }
            )

        # Goes to next page if possible
        next_page_post = response.css(self.next_page_posts_CSS).get()
        next_page_post_url = Static_Scrapy.turn_page(self, response, next_page_post, self.parse_posts) # Follows the next page - See doc string
        if next_page_post_url: # Only go to the next page if the page is not None
            yield next_page_post_url

    def parse_comments(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        items = self.items # Makes the items from items.py accessable within this function
        current_page_comment = response.meta['current_page']
        combined_text = response.meta.get('combined_text', '') # Carries forward accumulated text if we’re on page > 1
        combined_external_links = response.meta.get('combined_external_links', [])
        post_author_clean = response.meta.get('post_author_clean')
        publication_date_clean = response.meta.get('publication_date_clean')

        ### EXTRACT COMMENTS FROM THIS PAGE ###
        comments = response.css(self.comments_CSS)
        for i, comment in enumerate(comments):
            # Extract 'comment_author'
            comment_author = comment.css(self.comment_author_CSS).get()
            if comment_author:
                comment_author_clean = General_Functions.clean_text(comment_author)
            else:
                comment_author_clean = comment_author

            # Extract 'comment_publication_date'
            comment_publication_date = comment.xpath(self.comment_publication_date_XPATH).getall()
            if comment_publication_date:
                comment_publication_date_clean = General_Functions.join_and_clean(comment_publication_date)
            else:
                comment_publication_date_clean = comment_publication_date

            # Extract 'comment_tag' 
            comment_tag = comment.css(self.comment_tag_CSS).get()

            # # Extract 'comment_text'
            # comment_text = comment.xpath(self.comment_text_XPATH).getall()
            # comment_text_clean = General_Functions.join_and_clean(comment_text)

            # comment_cited_tag = comment.css(self.comment_cited_tag_CSS).re_first(self.comment_cited_tag_RE)
           
            # if comment_cited_tag:
            #     comment_text_clean = f"Citing comment {comment_cited_tag}\n{comment_text_clean}"
            # else:
            #     # Case 2: no comment reference → check for quote blocks
            #     quote_text = comment.xpath(self.comment_quote_XPATH).getall()
            #     if quote_text:
            #         quote_clean = General_Functions.join_and_clean(quote_text)
            #         # Prepend the quote to the comment text, formatted as blockquote
            #         comment_text_clean = f"> {quote_clean.replace('\n', '\n> ')}\n\n{comment_text_clean} <"

            ### TEST
            # Is this comment citing another comment? (then we skip inline quotes and show the reference)
            comment_cited_tag = comment.css(self.comment_cited_tag_CSS).re_first(self.comment_cited_tag_RE)

            # Build the comment text in ORIGINAL order by walking child nodes of .post_message
            parts = []
            for node in comment.xpath(self.comment_content_nodes_XPATH):
                root = getattr(node, "root", None)
                is_element = hasattr(root, "tag")  # lxml element = True; text node = False

                if is_element:
                    # 1) Quote wrapper (include only if NO cited comment)
                    if node.xpath("self::div[contains(@class,'post-bbcode-quote-wrapper')]"):
                        if not comment_cited_tag:
                            qt = node.xpath(".//text()").getall()  # includes 'Citat:' and its content
                            qclean = General_Functions.join_and_clean(qt)
                            if qclean:
                                parts.append("> " + qclean.replace("\n", "\n> "))
                        continue

                    # 2) Links (keep in text flow; external_links are still collected by your existing block below)
                    if node.xpath("self::a"):
                        href = node.xpath("@href").get()
                        if href:
                            full_link = response.urljoin(href)
                            parts.append(full_link)
                        continue

                    # 3) Other elements: visible text excluding nested quotes
                    vals = node.xpath(".//text()[not(ancestor::div[contains(@class,'post-bbcode-quote-wrapper')])]").getall()
                    tclean = General_Functions.join_and_clean(vals)
                    if tclean:
                        parts.append(tclean)
                else:
                    # TEXT NODE
                    txt = node.get()
                    if txt:
                        tclean = General_Functions.clean_text(txt)
                        if tclean:
                            parts.append(tclean)

            parts = [p + " <" if p.lstrip().startswith("> ") and not p.rstrip().endswith("<") else p for p in parts]
            comment_text_clean = " ".join(p for p in parts if p).strip()

            # If citing a specific earlier comment, prepend the notice (quotes were skipped above)
            if comment_cited_tag:
                comment_text_clean = f"Citing comment {comment_cited_tag}\n{comment_text_clean}"
            ###

            # Distinguish the very first post from later comments
            if current_page_comment == 1 and i == 0:
                text_bit = self.generate_YAML(comment_author_clean, comment_publication_date_clean, comment_tag, comment_text_clean, post=True)
                if not post_author_clean:
                    post_author_clean = comment_author_clean
                if not publication_date_clean:
                    publication_date_clean = comment_publication_date_clean
            else:
                text_bit = self.generate_YAML(comment_author_clean, comment_publication_date_clean, comment_tag, comment_text_clean)

            combined_text = combined_text + text_bit # Append this comment to accumulated text

            # Extract 'comment_external_links' 
            comment_external_links_partial = comment.xpath(self.comment_external_links_XPATH).getall()
            full_links = [response.urljoin(link) for link in comment_external_links_partial]
            combined_external_links.extend(full_links)

        ### HANDLE PAGINATION ###
        next_page_comment = response.css(self.next_page_comments_CSS).get()
        if next_page_comment: # If there is a next page of comments, follow it
            yield response.follow(
                url=response.urljoin(next_page_comment),
                callback=self.parse_comments,
                meta={
                    'post_link': response.meta['post_link'],
                    'current_page': current_page_comment + 1,
                    'combined_text': combined_text, # Pass along accumulated text
                    'combined_external_links': combined_external_links,
                    'post_author_clean': post_author_clean,
                    'publication_date_clean': publication_date_clean
                }
            )
            return # Don’t yield items yet, wait until the last page is reached

        ### FINALIZE AND YIELD ITEM (ONLY ON LAST PAGE) ###
        timestamp = datetime.now().strftime('%Y-%m-%d') # Extract 'scrape_date'
        post_link = response.meta['post_link'] # Extract 'post_link'

        # Extract 'post_title'
        post_title = response.css(self.post_title_CSS).get()
        if post_title:
            post_title_clean = General_Functions.clean_text(post_title)
        else:
            post_title_clean = post_title

        # Extract 'post_author'
        # post_author = response.css(self.post_author_CSS).get()
        # if current_page_comment == 1:
        #     if post_author:
        #         post_author_clean = General_Functions.clean_text(post_author)
        #     else:
        #         post_author_clean = post_author
        # post_author_clean = response.meta['post_author']

        # Extract 'categories'
        post_categories = response.css(self.post_categories_CSS).getall()
        if post_categories:
            post_categories_clean = General_Functions.join_and_clean(post_categories, join_character=', ')
        else:
            post_categories_clean = post_categories

        # Extract 'publication_date'
        # publication_date = response.xpath(self.post_publication_date_XPATH).getall()
        # if current_page_comment == 1:
        #     if publication_date:
        #         publication_date_clean = General_Functions.join_and_clean(publication_date)
        #     else:
        #         publication_date_clean = publication_date
        # publication_date_clean = response.meta['publication_date_clean']

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['source'] = self.source
        items['publication_date'] = publication_date_clean
        items['post_link'] = post_link
        items['post_title'] = post_title_clean
        items['post_author'] = post_author_clean
        items['categories'] = post_categories_clean
        items['thread_text'] = combined_text
        items['external_links'] = combined_external_links
        items['image_links'] = 'None'
        items['embedded_media_links'] = 'None'
        items['other_items'] = 'None'
        items['post_HTML'] = ''  # Not full HTML but HTML for all post/comments boxes

        self.seen_links.add(post_link) # Adds article to list of scraped articles

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them

