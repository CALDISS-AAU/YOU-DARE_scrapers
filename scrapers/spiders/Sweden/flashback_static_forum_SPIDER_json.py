### IMPORTS ###
# External imports #
import scrapy
import re
from datetime import datetime, timedelta
import time
import random
# Internal imports #
from ...items import ScrapersItem  # Imports the items from the items.py file
from ...functions.scraper_functions.static_scrapy_functions import Static_Scrapy  # Custom shared functions
from ...functions.scraper_functions.general_functions import General_Functions  # Custom shared functions

''' To run this spider pass the following to the terminal:
        cd ./path/to/YOU-DARE_scrapers_folder
        scrapy crawl flashback_SPIDER_json -a max_pages_posts=x # MUST MATCH SPIDER NAME!
    where -a max_pages_posts=x is an optional parameter to limit the number of post-pages to render more front pages containing more articles from the start_url
    OR
        cd ./path/to/YOU-DARE_scrapers_folder
        mkdir -p ./data/Sweden/flashback_SPIDER_json # If the folder does not yet exist
        nohup scrapy crawl flashback_SPIDER_json -a max_pages_posts=1 > ./data/Sweden/flashback_SPIDER_json/flashback_SPIDER_json_$(date +%F).log
'''

### CREATING THE SPIDER ###
class StaticSpider(scrapy.Spider): # Can be changed but it's not necessary - if changed also change Super in from_crawler function
    name = 'flashback_SPIDER_json' # Spider name - must be unique within given project
    region = 'Sweden' # Parent folder - used for folderstructure within the data folder - MUST BE IDENTICAL TO SPIDERS DIRECT PARENT FOLDER!
    source = 'Flashback' # The source of the articles - NOT the author!
    start_urls = [
        'https://www.flashback.org/f69-censur-och-yttrandefrihet-51006',
        # 'https://www.flashback.org/f226-integration-och-invandring-51007',
        # 'https://www.flashback.org/f34-nationalsocialism-fascism-och-nationalism-51006'
    ] # The url where the content to be scraped is found - can be multiple urls IF THE CSS/XPATH IS IDENTICAL!

    custom_settings = {
        # Keep it gentle on Flashback, even if global settings differ
        "DOWNLOAD_DELAY": 4,
        "RANDOMIZE_DOWNLOAD_DELAY": True,

        # Concurrency tuned specifically for one forum domain
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,

        # AutoThrottle: be more conservative (back off harder under pressure)
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 4,
        "AUTOTHROTTLE_MAX_DELAY": 120,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,

        # Retry: be more persistent on 429 and transient failures
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 10,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504, 522, 524, 408],

        # Give slow pages time; forums can be spiky
        "DOWNLOAD_TIMEOUT": 60,

        # Use browser-like headers (helps reduce blocks / weird responses)
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            ),
            "Upgrade-Insecure-Requests": "1",
        },

        # Optional: if Flashback sometimes varies content without cookies
        # "COOKIES_ENABLED": True,
    }
    
     ## HTML directions ##
    ''' These can be both CSS and XPath or a mix as long as it's matched within the response functions within the different parse functions.
        E.g. 'some_css' must use response.css('some_CSS') and 'some_xpath' must use response.xpath('some_XPATH')
        For clarrification:
            Front page referes to the first site the spider encounters after following the start_urls
            Article page referes to the site of each individual article
    '''
    # QUERIES FROM THE FRONT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the front page. 
        For functionality the following queries HAVE to be found on the front page:
            links_to_follow # The links to the individual articles
            next_page # The links to the next page (if the next page is fetchable)
    '''
    links_to_follow_posts_XPATH = '//table[@id="threadslist"]//td[contains(@class,"td_title")]/div[1]/a[1]/@href' # All posts
    next_page_posts_CSS = 'li.next a::attr(href)' # To gather more posts
    # QUERIES FROM THE COMMENT PAGE!!!
    ''' CSS or XPath queries for relevant information found on the individual post.
    '''
    post_title_CSS = 'h1 a::text' # Post title
    post_publication_date_XPATH = "//*[@id='posts']/*[@class='post'][1]/*[@class='post-heading']/text()" # Publication date of post (first "comment")
    post_author_CSS = '#posts .post .post-user .dropdown strong::text, #posts .post a.post-user-username::text, ' # Author of post (first "comment")
    post_categories_CSS = '.breadcrumb *::text' # Categories of post

    next_page_comments_CSS = 'li.next a::attr(href)' # To gather more comments 
    # QUERIES FROM EACH COMMENT!!!
    ''' CSS or XPath queries for relevant information found on the individual comment.
    '''
    comments_CSS = '#posts .post' # Overall comment block
    comment_publication_date_XPATH = ".//*[@class='post-heading']/text()" # Publication date of each comment
    comment_author_CSS = '.post-user .dropdown strong::text, a.post-user-username::text' # Author of each comment
    comment_text_XPATH = ".//div[contains(@class,'post_message')]//text()[not(ancestor::div[contains(@class,'post-bbcode-quote-wrapper')])]" # Text of each comment
    image_links_CSS = None 
    embedded_media_links_CSS = None
    comment_links_in_text_XPATH = ".//div[contains(@class,'post_message')]//a[not(ancestor::div[contains(@class,'post-bbcode-quote-wrapper')])]/@href" # Links in each comment
    other_items_CSS = None

    comment_tag_CSS = 'a.jumptarget::attr(name)' # The tag of each comment (used for qutation of this comment)
    comment_cited_tag_CSS = '.post-bbcode-quote-wrapper a[href*="#p"]::attr(href)' # The tag of the cited comment (used to reference quoted comment)
    comment_cited_tag_RE = r'#(p\d+)'
    comment_quote_XPATH = ".//div[contains(@class,'post-bbcode-quote-wrapper')]//text()" # Text within qutation (used for external citation)

    comment_content_nodes_XPATH = ".//div[contains(@class,'post_message')]/node()" # Makes sure that the order of citations and text is preserved.

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
        self.seen_links = Static_Scrapy.load_existing_links(self.save_file, column='post_link') # See doc string

    def generate_YAML(self, comment_author, comment_date, comment_tag, comment_text, post=False):
        label = 'POST' if post else 'COMMENT'
        return f'\n\n\n---\n{label}: \nAuthor: {comment_author}\nDate: {comment_date}\nTag: {comment_tag}\n---\n{comment_text}'

    def generate_dict(self, comment_author, comment_date, comment_tag, comment_text, post=False, index=None):
        return {
            'label': 'POST' if post else f'COMMENT_{index}',
            'author': comment_author,
            'date': comment_date,
            'tag': comment_tag,
            'text': comment_text
            }

    def normalize_swedish_date(self, raw_date):
        """
        Converts 'Idag' and 'Igår' to actual YYYY-MM-DD format
        based on current scrape date.
        """
        if not raw_date:
            return raw_date

        raw_date = raw_date.strip()

        today = datetime.now()
        
        if raw_date.lower().startswith("idag"):
            # Extract time part if present
            time_part = raw_date[4:].strip()
            date_part = today.strftime("%Y-%m-%d")
            return f"{date_part} {time_part}".strip()

        if raw_date.lower().startswith("igår"):
            time_part = raw_date[4:].strip()
            yesterday = today - timedelta(days=1)
            date_part = yesterday.strftime("%Y-%m-%d")
            return f"{date_part} {time_part}".strip()

        return raw_date

    ### THE ACTUAL SPIDER FUNCTIONALITY ###
    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_posts, # Calls parse_post on each url
                meta={'current_page': 1} # Information sent to parse_post
            )

    def parse_posts(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN START_REQUESTS!
        current_page_post = response.meta['current_page'] # Saves 'current_page_post' from start_request

        # Finds and follows post links 
        post_links = response.xpath(self.links_to_follow_posts_XPATH).getall() # Gets all article links 
        for partial_link in post_links:
            link = response.urljoin(partial_link)
            link = re.sub(r'(/t\d+)s$', r'\1', link)
            if link in self.seen_links: # Only scrapes information from the front page for posts that has not yet been scraped - can be removed if only the link is found from the front page
                self.logger.info(f"Skipping duplicate post: {link}")
                continue

            yield response.follow(
                url=link,
                callback=self.parse_comments, # Calls parse_comments on each link
                meta={
                    'post_link': link, # Sends the link to parse_comment so that it can be stored as an item. To also send e.g. the 'publication_date' simply add it here!
                    'current_page': 1,
                    'replies': [],
                    'combined_text': '',
                    'combined_links_in_text': [],
                    'publication_date_clean': None,
                    'post_author_clean': None,
                    'comment_counter': 0
                }
            )

        # Goes to next page if possible
        next_page_post = response.css(self.next_page_posts_CSS).get()
        next_page_post_url = Static_Scrapy.turn_page(self, response, next_page_post, self.parse_posts) # Follows the next page - See doc string
        if next_page_post_url: # Only go to the next page if the page is not None
            yield next_page_post_url

    def parse_comments(self, response): # Can be renamed. IF IT IS REMEBER TO REDIRECT THE CALLBACK IN PARSE_FRONT!
        current_page_comment = response.meta['current_page']
        replies = response.meta.get('replies', [])
        publication_date_clean = response.meta.get('publication_date_clean')
        post_author_clean = response.meta.get('post_author_clean')
        combined_text = response.meta.get('combined_text', '')
        combined_links_in_text = response.meta.get('combined_links_in_text', [])
        comment_counter = response.meta.get('comment_counter', 0)

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
                comment_publication_date_clean = self.normalize_swedish_date(comment_publication_date_clean)
            else:
                comment_publication_date_clean = comment_publication_date

            # Extract 'comment_tag' 
            comment_tag = comment.css(self.comment_tag_CSS).get()

            # Skip inline quotes and show the reference if citing comment
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

                    # 2) Links (keep in text flow; links_in_text are still collected by your existing block below)
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

            # Distinguish the very first post from later comments
            if current_page_comment == 1 and i == 0:
                text_dict = self.generate_dict(comment_author_clean, comment_publication_date_clean, comment_tag, comment_text_clean, post=True)
                if not post_author_clean:
                    post_author_clean = comment_author_clean
                if not publication_date_clean:
                    publication_date_clean = comment_publication_date_clean
            else:
                comment_counter += 1
                text_dict = self.generate_dict(comment_author_clean, comment_publication_date_clean, comment_tag, comment_text_clean, index=comment_counter)

            if combined_text:
                combined_text = f"{combined_text}\n---\n\n{comment_text_clean}"
            else:
                combined_text = comment_text_clean

            replies.append(text_dict)

            # Extract 'comment_links_in_text' 
            comment_links_in_text_partial = comment.xpath(self.comment_links_in_text_XPATH).getall()
            full_links = [response.urljoin(link) for link in comment_links_in_text_partial]
            combined_links_in_text.extend(full_links)

        ### HANDLE PAGINATION ###
        next_page_comment = response.css(self.next_page_comments_CSS).get()
        if next_page_comment: # If there is a next page of comments, follow it
            yield response.follow(
                url=response.urljoin(next_page_comment),
                callback=self.parse_comments,
                meta={
                    'post_link': response.meta['post_link'],
                    'publication_date_clean': publication_date_clean,
                    'post_author_clean': post_author_clean,
                    'combined_text': combined_text, # Pass along accumulated text
                    'replies': replies,
                    'combined_links_in_text': combined_links_in_text,
                    'current_page': current_page_comment + 1,
                    'comment_counter': comment_counter,
                }
            )
            return # Don’t yield items yet, wait until the last page is reached

        ### FINALIZE AND YIELD ITEM (ONLY ON LAST PAGE) ###
        # Extract 'scrape_date'
        timestamp = datetime.now().strftime('%Y-%m-%d')
        # Extract 'source' 
        source = self.source
        # Extract 'post_link' 
        post_link = response.meta['post_link'] # Extract 'post_link'
        # Extract 'post_title'
        post_title = response.css(self.post_title_CSS).get()
        if post_title:
            post_title_clean = General_Functions.clean_text(post_title)
        else:
            post_title_clean = post_title
        # Extract 'publication_date' 
        publication_date = publication_date_clean
        # Extract 'post_categories'
        post_categories = response.css(self.post_categories_CSS).getall()
        if post_categories:
            post_categories_clean = General_Functions.join_and_clean(post_categories, join_character=', ')
        else:
            post_categories_clean = post_categories
        # Extract 'post_text' 
        post_text = combined_text
        # Extract 'image_links'
        image_links = self.image_links_CSS
        # Extract 'embedded_media_links' 
        embedded_media_links = self.embedded_media_links_CSS
        # Extract 'links_in_text' 
        links_in_text = combined_links_in_text
        # Extract 'other_items' 
        other_items = self.other_items_CSS

        items = ScrapersItem() # Makes the items from items.py accessable within this spider for every single article

        # Assign variables to items here
        items['scrape_date'] = timestamp
        items['source'] = source
        items['post_link'] = post_link
        items['post_title'] = post_title_clean
        items['publication_date'] = publication_date
        items['post_author'] = post_author_clean
        items['post_categories'] = post_categories_clean
        items['thread_text'] = post_text
        items['image_links'] = image_links
        items['embedded_media_links'] = embedded_media_links
        items['links_in_text'] = links_in_text
        items['replies'] = replies
        items['other_items'] = other_items

        self.seen_links.add(post_link) # Adds article to list of scraped articles

        yield items # Writes the items to the FEEDS function in the settings.py file hence saving them

