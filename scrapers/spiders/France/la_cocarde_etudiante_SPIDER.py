### IMPORTS ###
# External imports #
import scrapy
from scrapy import signals
import os.path
import json
import re 
from datetime import datetime
from w3lib.html import remove_tags
# Internal imports #
from ...items import ScrapersItem # Imports the items from the items.py file
from ...functions.general_functions import General_Functions # importing cleaning functions

### INSTRUCTIONS ###
''' To run this scraper open a terminal, change the directory to
        /work/YOU-DARE/scrapers/
    and pass
        scrapy crawl {name}
    to scrape the entire url, and pass
        scrapy crawl {name} -a max_pages=x
    to only scrape x pages
'''
# --- !!! --- #
# --- Since this spider only scrapes new articles and breaks when a new page contains URLs for 
# --- already scraped articles, the first run should always be of the entire web-page, hence
# ---       scrapy crawl CPI_news
# --- !!! --- # 
''' While this spider might need some adjustments within the function code,
    it should for the most parts be ready to go for any web page after changing
    the variables in the beginning of the class.
    This spider is programmed for web pages on the form:
    - From all start URLs the links for the various articles can be scraped (in parse_front)
    - From the start URLs a link for the next page can be found, and this page should look like the first page (from the start URL)
    - From all articles it should be possible to scrape:
        * title
        * publication_date
        * article_text
        * article_HTML (the full HTML of the text - to capture any formatting of the text)
        * image_links
        * external_links (within the text)
    - To scrape any other information from the articles, e.g. author, internal links etc. the CSS-queries for these needs to be added 
        as variables before any functions (in the same way as existing variables) before they are found in the function parse_article
        (in the same way as existing response calls) and should lastly be assigned to its respectible item (in the same way as existing assignments).
        Lastly it is important to define the item within the "items.py" file (in the same way as existing items has been assigned).
'''

### CREATING THE SPIDER ###
class CocardeEtudianteSpider(scrapy.Spider):
    name = 'la_cocarde_etudiante_SPIDER' # Spider name - must be unique within given project
    region = 'France' # Parent folder - used for folderstructure within the data folder
    # In case of multiple URLs and a given max_pages it will scrape x pages from each start URL
    urls = ['https://cocardeetudiante.com/articles/',
    'https://cocardeetudiante.com/articles/page/2/',
    'https://cocardeetudiante.com/articles/page/3/',
    'https://cocardeetudiante.com/articles/page/4/',
    'https://cocardeetudiante.com/articles/page/5/',
    'https://cocardeetudiante.com/communiques/']
    #start_url_article = f'https://cocardeetudiante.com/articles/page/{i}/' for i in range(2,7), # In case of multiple URLs and a given max_pages it will scrape x pages from each start URL
    #start_url_article_first = ['https://cocardeetudiante.com/articles/']
    #start_url_comm = ['https://cocardeetudiante.com/communiques/']
    save_path = f"./data/{region}/{name}/data_{name}.jl" 

    items = ScrapersItem()
    ### HTML directions ### 
    ''' All of these should be in CSS
        If some are changed to xpath, this also needs to be changed in the relevant function!
    '''
    # FROM THE FRONT PAGE!!!
    article_CSS = '.elementor-post__title' # CSS for the entire article
    links_to_follow_CSS = 'a::attr(href)' 
    next_page_CSS = '.page-numbers::attr(href)'
    publication_date_CSS = '.elementor-post__meta-data::text'
    # FROM THE ARTICLE PAGE!!!
    title_CSS = 'h1.elementor-heading-title.elementor-size-default::text'
    article_text_bits_CSS = '.elementor-widget-container p ::text' # All text bits from the article - these will be combined in parse_article
    article_HTML_bits_CSS = '.elementor-widget-container p' # All HTML bits from the article text - these will be combined in parse_article
    image_links_CSS = '.attachment-large size-large wp-image-7186 lazyloading img::attr(src)'
    author_text_CSS = 'p.has-text-align-right *::text'
    #image_captions_CSS = 'span.post-content div.wp-caption p.wp-caption-text'
    themes_CSS = '.elementor-post-info__terms-list a.elementor-post-info__terms-list-item::text'
    article_references_CSS = 'ul.wp-block-list li.has-small-font-size'
    #reference_text_CSS = 'ul.wp-block-list li.has-small-font-size::text'
    #reference_links_CSS = 'ul.wp-block-list li.has-small-font-size a::attr(href)'

    def __init__(self, max_pages=None): # Initial function that runs before anything else 
        super().__init__()
        # Get max_pages from command line
        self.MAX_PAGES = int(max_pages) if max_pages else None # Allows for max_pages to be defined through the terminal prompt
        self.save_file = self.save_path # The path and name of the data file if it exists
        self.existing_links = set()  # Tracks article links to avoid duplicates
        self.scraped_data = []  # Stores newly scraped data

    @classmethod # REMEMBER TO CHANGE THE SPIDER CLASS TO THE CURRENT SPIDER!
    def from_crawler(cls, crawler, *args, **kwargs): # Function that makes sure that open_spider is run 
        spider = super(CocardeEtudianteSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        return spider

    def open_spider(self, spider): # Function that finds any existing data, which allows for further comparison of URLs, hence ensuring that only new articles are scraped 
        self.logger.info("open_spider() is running!") # Self check
        self.existing_data = set()  # Always define a dataset, even if a dataset doesn't exists yet

        if os.path.exists(self.save_file):  # Check if the JSONL file exists
            try: # Only opens an uncorupted file
                with open(self.save_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            item = json.loads(line.strip())  # Load each JSON object
                            if "article_link" in item:
                                self.existing_data.add(item["article_link"]) # Saves previously scraped article links
                        except json.JSONDecodeError:
                            self.logger.warning("Skipping invalid JSON line.")
                self.logger.info(f"Loaded {len(self.existing_data)} existing articles.")
            except Exception as e: # If the file is corupted
                self.logger.warning(f"Error reading existing data: {e}, starting fresh.")
                self.existing_data = set()

    def start_requests(self): # Starts the scraper from the given start URLs 
        for url in self.urls:
            yield scrapy.Request(
                url = url,
                callback = self.parse_front,
               # meta={'current_page': 1}
            )

    def parse_front(self, response): # Scrapes article links on a given page to follow and afterwards goes to the next page 
       # current_page = response.meta['current_page']  # Get current page from meta
        # Extract article links
        article = response.css(self.article_CSS)
        links_to_follow = article.css(self.links_to_follow_CSS).extract()
        
        print(f'These are the links to follow: {links_to_follow}')

        # Only pass URLs to articles that is not yet scraped
        found_duplicate = False  # Track if we hit a duplicate

        link_list = [] # my super awesome list for links 
        for link in links_to_follow:
            publication_date = article.css(self.publication_date_CSS).getall()
            if link in self.existing_data:
                self.logger.info(f"Skipping duplicate article: {link}")
                found_duplicate = True  # Mark that we found a duplicate
                continue  # Skip this article, but continue checking the rest of the page
                


            yield response.follow(
                url=link,
                callback=self.parse_article,
                meta={'article_link': link, 'publication_date': publication_date}
            )

        # Pagination Break: Only continue if no duplicates were found on this page
        # next_page = response.css(self.next_page_CSS).get()
        # if next_page and not found_duplicate and (self.MAX_PAGES is None or current_page < self.MAX_PAGES):
        #     yield response.follow(
        #         next_page,
        #         callback=self.parse_front,
        #         meta={'current_page': current_page + 1}
        #     )

    def parse_article(self, response): # Scrapes articles that has not yet been scraped 
        items = self.items # Imports defined items
        timestamp = datetime.now().strftime('%Y-%m-%d') # For scrape_date
        # Retrieve the article link from meta data
        article_link = response.meta['article_link'] # Link to follow
        publication_date = response.meta['publication_date']

        # Duplicate Check: Skip if article is already scraped
        if article_link in self.existing_data:
            self.logger.info(f"Skipping duplicate article: {article_link}") # Self check
            return  # Stop processing this article

        # Extract other article details
        article_title = response.css(self.title_CSS).get()
        article_text_bits = response.css(self.article_text_bits_CSS).getall()
        article_text = ' '.join(article_text_bits).strip()
        article_HTML_bits = response.css(self.article_HTML_bits_CSS).getall()
        article_HTML = ' '.join(article_HTML_bits).strip()
        themes_text = response.css(self.themes_CSS).getall()
        author = response.css(self.author_text_CSS).getall()
        # Extract references from article
        article_references = response.css(self.article_references_CSS)
        sources = []
        for li in article_references:
            text_parts = li.css('::text').getall()
            hrefs = li.css('a::attr(href)').getall()
            combined_text = ''.join(part.strip() for part in text_parts if part.strip())
            sources.append({
                'text': combined_text,
                'links': hrefs
                })
        
       # youtube_links = response.css(self.youtube_CSS).getall()
        
        # Extract images and captions  
        image_links = response.css(self.image_links_CSS).getall()  
       # image_captions_html = response.css(self.image_captions_CSS).getall()  
       # image_captions = [remove_tags(caption, keep=("a",)).strip() for caption in image_captions_html]  
        # Ensure captions are correctly aligned with images  
        #fixed_captions = []  
        #caption_index = 0  # Tracks position in image_captions list  
        #for img in image_links:  
            # Check if the image is inside a wp-caption div
         #   parent_div = response.css(f'.attachment-large size-large wp-image-7186 lazyloading img[src="{img}"]')  
         #   if parent_div:  
                # Assign a caption if available, otherwise assign an empty string  
          #      fixed_captions.append(image_captions[caption_index] if caption_index < len(image_captions) else "")  
           #     caption_index += 1  # Move to the next caption  
           # else:  
                # If the image is not in a captioned div, add an empty string  
            #    fixed_captions.append("")  
        # Now image_captions is correctly aligned with image_links  
        #image_captions = fixed_captions

        # Extract hyperlinks within the article - this might/might not be an accurate css query (no examples of external links were found during development)
       # external_links = response.css(self.external_links_CSS).getall()

        # Remove '\n' from article text before passing it to its item        
        article_text = General_Functions.clean_text(article_text)

        # Pass scraped article details to relevant items in this given order
        items['scrape_date'] = timestamp
        items['article_link'] = article_link
        items['article_title'] = article_title
        items['publication_date'] = publication_date
        items['article_text'] = article_text
        items['image_links'] = image_links
       # items['article_HTML'] = article_HTML
        items['themes_text'] = themes_text
        items['references_text'] = sources
        #items['references_links'] = references_links
        items['author'] = author

        # Adds scraped link to list of previously scraped links
        self.existing_links.add(article_link)

        yield items