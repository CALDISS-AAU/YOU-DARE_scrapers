# YOU-DARE Scrapers

## Project description
As a part of the EU Horizon project YOU-DARE, CALDISS has contributed with the development of web scrapers for a number of sources and actors across various platforms. These scrapers have been written in Python and can generally be put into one of three categories depending on their targeted platform:
- [Scrapers for websites](#Scrapers-for-websites)
- [Scrapers for YouTube](#Scrapers-for-YouTube)
- [Scrapers for Telegram](#Scrapers-for-Telegram)

What information is gathered for each source along with the overall functionality and the technical description of the three catregories of scrapers will be covered in seperate sections.

It should be noted, that while CALDISS has developed these tools, the relevant actors and their respective platforms for each country have been specified by researchers associated with the YOU-DARE project.

This project is meant primarily to serve as documentation for how raw data was collected in the research project and is therefore *not* in active development nor maintained. No guarantee is provided that any scraper in this repository still works. 

### Folder structure
The overall folder structure of this project can be depicted as
```
├── data
├── post-processing
├── review
├── scrapers
│   ├── functions
│   ├── spiders
│   │   ├── Denmark
│   │   ├── France
│   │   ├── Hungary
│   │   ├── Italy
│   │   ├── Romania
│   │   ├── Spain
│   │   ├── Sweeden
│   │   ├── United_Kingdom
│   │   └── ...
│   └── ...
└── ...
```
where only the most relevant folders have been included. The fundamental folder structure of this project has been created using `scrapy` by calling `scrapy startproject scrapers` within the YOU-DARE folder. For more informaton about the resulting folder structure from this command, and scrapy in general, see [Scrapy 2.13 documentation](https://docs.scrapy.org/en/2.13/).

Please note that the data directory is not included on this repository, as this is where collected data is stored.

Within the inner scrapers folder, three folders in particular are of interest:
- **The functions folder**: The individual elements within this folder will be discussed in further detail where relevant in context of scraper type. 
- **The spiders folder**: This folder contains one subfolder for each country, in which all scrapers for said country, regardless of platform, is found.

## Data collected

### Websites

All website scrapers within this repository generate a jsonlines dataset containing these 13 items in this order:
* **scrape_date** : The date of data collection
* **source** : The name of the actor
* **article_link** : Link for the individual article
* **article_title** : The title of the article
* **publication_date** : Publication date of the article
* **author** : Author of the article
* **article_categories** : Categories, topics, tags etc. of the article
* **article_text** : The text body of the article including subtitles and other relevant text-bits
* **image_links** : Links for images within the article text
* **embedded_media_links** : Links for YouTube videos, social media posts etc. within the article_text
* **links_in_text** : Links for e.g. references within the article_text
* **other_items** : Anyother information of interest for the specific source requested by the scientist
* **article_HTML** : The full response HTML of the article. 

>[!Note] 
>It is not always possible to retrieve all 13 types of data for all websites, for various reasons, and in these cases the query for said data type has been set to `None`.

All websites scrapers are based on `scrapy`. See [Scrapers for websites](#Scrapers-for-websites) for further details.

### YouTube

YouTube scrapers are based on either `PyTube` or `yt-dlp`. Each scraper generates a jsonlines dataset (`videos.jl` from `PyTube` scrapers and `metadata.jl` from `yt-dlp` scrapers) containing these 6 items in this order:
* **scrape_date** : The date of data collection
* **video_title** : The title of the video
* **source** : The name of the actor
* **publication_date** : Publication date of the video
* **video_link** : Link for the individual video
* **video_id** : ID for the individual video

Audio tracks from collected YouTube videos are downloaded to a `m4a_files`-folder containg one `.m4a` file per video collected.

See the [scrapers for YouTube section](#scrapers-for-youtube) for further details.

### Telegram

Telegram data has been collected using `Telepathy`. For specifics on what specific metadata is gathered using this tool, please colsult the [telepathy documentation](#https://github.com/proseltd/Telepathy-Community).

## Scrapers for websites
In order to scrape and gather relevant information from a number of different sections across various websites a unique scraper has been developed for each website. While each scraper is unique they are all based on the same principles and can roughly be split into two categories - [Static scrapes](#Static-scrapers) and [Dynamic scrapers](#Dynamic-scrapers).

Regardless of the type of scraper they are all developed as `scrapy` modules and should be run as such:

```
cd ./YOU-DARE/scrapers
scrapy crawl spider_name # spider_name varies and is unique to exactly one scraper
``` 

This exact instruction of how to run each `scrapy` scraper is repeated at the top of each scraper script, where `spider_name` has been replaced by the name of that specific spider. 


### Requirements for running scrapers for websites

To setup the python environment used for developing and running the scraper, use the provided `requirements.txt` which can be installed via `pip`:

`pip install -r requirements.txt`

The scrapers for websites are based primarily on the following dependencies:
- `scrapy` (version 2.13.3)
- `playwright` (version 1.55.0)
- `scrapy_playwright` (version 0.0.44)

Futhermore `playwright` is required:
- `playwright install`
- `playwright install-deps` (might be irrelevant depending on the operating system)

Please note that while each spider has its own dedicated script, they all require the full content of the `scraper_functions` folder within the `functions` folder, which will be further described in [Shared functions - scrapy](#Shared-functions---scrapy).

### Variations to the standard scrapy project

**Changes to the `settings.py` file**:
The `spider` folder would commonly be the only folder from which `scrapy spiders` could crawl, however, this has been changed so that the active `SPIDER_MODULES` are the country specific subfolders instead.
The code for `SPIDER_MODELES` can be seen below.

        ```
        SPIDER_MODULES = [
            # "scrapers.spiders", # Note that this folder has been commented out
            "scrapers.spiders.Denmark", 
            "scrapers.spiders.France", 
            "scrapers.spiders.Hungary", 
            "scrapers.spiders.Italy", 
            "scrapers.spiders.Romania", 
            "scrapers.spiders.Spain", 
            "scrapers.spiders.Sweden", 
            "scrapers.spiders.United_Kingdom",
            ]
        ```

All active spiders are therefore placed within one of these country folders without any further nesting. Any spider placed elsewhere will not be recognised and can therefore not be run.

The filenaming and saving functionality has been handled by `scrapy`'s `FEEDS` mentioned [further below](#Variations-to-the-standard-scrapy-project).

Other changes to`settings.py` include:

- The `USER_AGENT` module has been activated to avoid being blocked by some websites.
- The `FEEDS` module has been included to ensure that all data is saved in a uniform folder structure by `data/%(region)s/%(name)s/data_%(name)s.jl`, where `region` and `name` are spider dependent variables.

**Adding relevant items to the `items.py` file** 
This file specifies the fields collected from the target websites.
(see [Data collection - Websites](#Data-collection---Websites))

### Static scrapers
"Static scrapers" assume that the target website exposes at least the link for the individual article on a front or landing page (the first page the spider meets by following the given start url). All relevant information is gathered from the article page that is reached by following the individual article linke. If all information can be found from the front or landing page, everything is parsed from said page. 

Static scrapers differ from dynamic scrapers in the way new articles are found. For static scrapers, new articles or links are rendered by following the link provided by "clicking" the 'next page'-button which loads the next page with a different URL than the page before it. In other words - all pages with links and contents are static and can be reached via a specific URL.

A general example of a static scraper in its entirety can be seen in 
`YOU-DARE/scrapers/scrapers/spiders/template_static_SPIDER.py`, however, the general structure of a static scraper follows a standard scrapy spider, where links are found from the front page and then followed. The spider will thereafter go to the next page if one exists, follow the links from that page and so on. This will be repeated until all articles have been scraped, and the final dataset will then be saved at the end.

>[!Note] 
>The process of finding new links and following them is in reality done in parallel, due to the scrapy architecture, however, for simplicity these steps are discussed as being serialised.

#### Extra functionality for static scrapers
The scrapers developed by CALDISS implement some additional functionality than one would expect within the standard scrapy project. The two most noticable being:
- **Only scrape previously unscraped articles**: A check for any existing datasets created by running the scraper of interest has been implemented. If such a dataset exists the links for the previously scraped articles will be imported and all links found by running the scraper will be held up against the imported links. If the link is already in the dataset the article will be skipped, hence preventing scraping any article more than once.
- **Ability to limit the number of pages to scrape**: The possibility to limit the number of pages to scrape has been implemented in such a way that the spider will continue rendering new "front pages" until the last possible page or until `max_pages` has been reached. In order to utilise this limitation one needs to add `-a max_pages=x` flag to the terminal call like this `scrapy crawl spider_name -a max_pages=x`, where `x` is the number of pages the user wants to scrape.

>[!TIP]
>The ability to limit the number of pages to scrape has various usecases and is especially encouraged when:
    - **Testing out a new scraper**: to test whether all data from a given page is gathered accurately one can save significant time by only scraping one or two pages until it has been verified that the given css/xpath queries are accurate.
    - **The page has previously been scraped in full but is missing newer content**: if new articles has been added to a site since the last time it was scraped it will save time to only scrape the first couple of pages containing the new articles rather than scraping the entire site once more even though links within the dataset are skipped.
    - **The page in question is prone to craching**: due to the data only being saved just before the scraper finishes no data is saved if the scraper for some reason craches while it's scraping. It can therefore be useful to scrape a page in batches rather than scraping everything at once, e.g. `-a max_pages=100` in the first run, `-a max_pages=200` in the second run and so on. 

#### General structure of a static scraper
Static scrapers within this project all follow the same structure:
1. **Imports**: External imports of `scrapy` and `datetime` and internal imports of `items` from the scrapy project along with functions from the function classes `Static_Scrapy` and `General_Functions` developed for this specific project.
2. **Setting up the spider**: Defining fundamental variables for the spider. This includes:
```
name: spider_name
region: country of the spider 
        # used for generating the FEEDS folder structure previously mentioned
source: The name of the actor of the website
start_urls: All urls the spider should scrape
All CSS/XPath queries for gathering information:
        links_to_follow: link from the front page to the article page
        next_page: link to the next page - if available
        article_title: title of the article
        publication_date: publication date of the article
        author: author of the article - Not the same as the source
        article_categories: categories, tags etc. 
        article_text: all relevant text excluding title and image captions
        image_links: the src link of images within the article
        embedded_media_links: interactive YouTube-links, links for instagram posts etc.
        links_in_text: all hyperlinks within the text excluding image_links and embedded_media_links
        other_items: Always None unless some specific information is requested
        # If the following information is available, otherwise set to None
```
3. **Calling setup-functions**: Should always be included and never fiddled with.
4. **Making the spider functional**: Setting up the spider per standard scrapy by defining and calling the following functions:
    * `async def start`: Default scrapy function to access start_urls. From here `parse_front` is called on each start_url
    * `def parse_front`: Crawl a given start url (from `start`), collects all article links, checks whether each article has already been scraped and if not calls `parse_article` for each article link. Finally it goes to the next page if possible.
    * `def parse_article`: Crawl a given article link (from `parse_front`), generates a timestamp and fetches all relevant information using the variables and queries previously defined in step 2. Here collected information is also prepared for the final dataset (data is cleaned, text is joined etc.). Lastly all gathered information is parsed to the relevant items before `scrapy` handles the actual functionality of saving data.

#### All sources collected using static scrapers and possible exceptions to the general structure of a static scraper
Here the full list of static scrapers within this project will be listed, along with any exceptions to the general static scraper structure:
:::info
**Denmark**
* Dansk regnbueråd - Artikler
    * Has implemented additional functionality to exclude links to the site's own social media accounts
    * There's only a single page hence any functionality regarding going to the next page has been removed
* Dansk regnbueråd - Nyheder
    * Everything can be found from the front page, hence parse_article has been made obsolete and removed. This has also lead to other minor changes within the code
* Identitær
* Manderådet
* Nordfront DK

**France**
* Generation Zemmour
* La Cocarde Etudiante 
    * Uses WayBack to acess the website
    * Due to the limited number of pages on the website and the difficulty in getting the scraper to follow the link for the next page, the next page functionality was skipped and the start_urls were expanded to include urls for every page
* Les identitaires

**Hungary**
* Betýarseg
    * Has a newer USER_AGENT in custom_settings in order to avoid bot-detection and thereby being blocked. If this scraper does not run due to ERROR 403 it will likely be fixed by updating this USER_AGENT to a newer version.
* Legio Hungaria

**Italy**
* Blocco Stedentesco
* Casa pound Italia
* Il redpillatore
* Uominiedonne

**Romania**
* Comunitatea identitara
* Noua dreapta - actiuni and acasa
* Noua drepta - opinii
* Provita
* Rost

**Sweden**
* Samnytt
    * Has disabled 'ROBOTSTXT_OBEY' via custom_settings. *NOTE:* Running this scraper is in direct violation with rules set by the website in their robots.txt
    * Has implemented additional functionality to ensure standardised article_links, since all links are valid on the '.se'-domain while some are both valid on the '.se'- and '.nu'-domain

**United Kingdom**
* Homeland party - news
* Homeland party our thinking
* Steve Laws
    * Uses WayBack to acess the website
:::

#### Flashback - static scraper for a forum
Within the YOU-DARE project a unique static scraper has been developed for the Swedish forum "Flashback". What makes this website unique from other sources collected here is the forum-structure, where there's not only multiple front pages with multiple post links on each page, but also multiple comment pages for every post. This unique structure naturally calls for a custom build scraper, and due to the static nature of the site the scraper has been based on the general structure of a static scraper. However, the deviations of this scraper in comparison to the general structure is so vast that this scraper has been put in it's own section.

In short the overall structure has been extended to not only go to the next post page but also the next comment page. 
>[!Warning] 
>The functionality of limiting the number of pages does only apply to the number of post pages.

Likewise does the scraper only check existing links for posts, hence if a post has already been scraped and the scraper is run again it will not find any new comments on this post. 

The last major divergence of this scraper is the number of queries along with what information is parsed to what scrapy item. This expansion of the scraper has been implemented to ensure that all text from all comments and all relevant information for said comment has been collected, combined and saved after every comment has been included. If this step was not included one would possibly end up with multiple jsonlines for each post (one for each comment page) or a single jsonline for each post containing only the first or last comment page. 

The relevant scrapy items that diviate from the general static scraper and what they contain are, for clarrification, listed below:
```
post_link: The link of the post page
post_title: The title of the post
publication_date: The publication date of the actual post (the first "comment")
post_author: The author of the actual post (the first "comment")
post_categories: The categories of the post
thread_text: The combined text of the post along with every comment. 
             The final 'thread_text' will be build in this way:
                 ---
                 label: POST (if it's the first "comment")/COMMENT
                 Author: the author of the comment
                 Date: the publication_date of the comment
                 Tag: the comment tag/id
                 ---
                 Text: All text of the comment including external citations. 
                       Internal citations will not be included, 
                          however the tag of the cited comment will be listed.
             This type of comment-text-blocks will be repeated and joined 
                and parsed as the combined text
image_links, embedded_media_links and links_in_text: 
             Complete lists of all relevant lists across all comments for a given post 
```

### Dynamic scrapers
"Dynamic scrapers" are built for sites where all relevant URLs are not retrievably via specific URLs, but instead require additional rendering of the same page.

The dynamic scrapers can in simple terms be split into one of two categories:
- Scrapers that interacts with the current page by scrolling in order to render more articles, hence the number of accessible articles increases by every scroll
- Scrapers that interacts with the current page by clicking a button to either 
    * increase the number of accessible articles for every click, or 
    * replace the current articles with a new set of articles, keeping the number of accessible articles constant.
 
Regardless of how new articles are rendered it is always the case that the URL of the front page does not change, and that content on the page is dynamically rendered by "interacting" with the page.
>[!Note] 
>There are few examples of websites where clicking the "next page" button does in fact alter the URL when replacing the accessible articles, or where one can skip articles by adding a page-indicator to the URL instead of scrolling the site. However, in these cases the content of said websites are still dynamically rendered, and a static scraper would therefore be insufficient for data collection.

Dynamic scrapers are also built with `scrapy` and uses `playwright` for handling js-rendered content.

This repository holds two general examples of dynamic scrapers - one utilising a scroll-functionality (`YOU-DARE/scrapers/scrapers/spiders/template_dynamic_scroll_SPIDER.py`) and one using a click-functionality (`YOU-DARE/scrapers/scrapers/spiders/template_dynamic_click_SPIDER.py`).

Even though these two types of dynamic scrapers vary quite significantly in their way of retrieving all article links they still share their overall structure. While the static scrapers found new article links while following already rendered links in parallel, all dynamic scrapers uses `playwright` to render all article links before `scrapy` is called for scraping and saving all relevant information.

As was the case for [static scrapers](#Extra-functionality-for-static-scrapers) some extra functionality has been implemented for the dynamic scrapers. These functions are similar to the functionality of the static scrapers, where previously scraped articles are skipped and the user can limit the number of scrolls or clicks/pages by adding `-a max_scrolls=x` or `-a max_pages=x` to the terminal call.

#### General structure of a dynamic scraper
In [General structure of a static scraper](#General-structure-of-a-static-scraper) the structure of static scrapers was divided into 4 steps, where step 1-3 remains the same for dynamic scrapers. For all dynamic scrapers, disregarding the rendering functionality, step 4 looks like this:

4. **Making the spider functional**: Setting up the spider using both `playwright` and `scrapy` by defining and calling the following functions:
    * `def parse`: Default scrapy function to accessing start_urls before interacting with the website using playwright, either by scrolling or clicking to render the entire website (or the given number of scrolls/clicks) and collecting all links. The links are then followed and their content fetched using playwright, before the response from this step is sent to `parse_article`. Lastly all scraped data is returned to this function before being parsed on to the `scrapy` saving functionality.
    * `def parse_article` for dynamic scrapers only differ from the static version where it does not parse the collected data directly to `scrapy` for saving, but returns it to `parse`.

#### All sources collected using dynamic scrapers and possible exceptions to the general structure of a dynamic scraper
Here the full list of dynamic scrapers, within this project will be presented, along with any exceptions to the general dynamic scraper structure:
:::info
**Denmark**
* Maniphesto
* Modstrømmen 
    * Utilises the `click_and_collect_links_and_article_categories` function rather than the standard `click_and_collect_links` function, due to the article category only being accessible from the front page (see [Shared functions - scrapy](#dynamic_click_scrapy_functions.py))
* Reel ligestilling
* Retten til liv
    * Has disabled 'ROBOTSTXT_OBEY' via custom_settings. *NOTE:* Running this scraper is in direct violation with rules set by the website in their robots.txt
    * Has implemented functionality to exclude links for author-pages from article-links
    * Has implemented additional functionality in order to accurately collect the author, due to varying authors being nested differently within the article HTML
* Stop islamiseringen af Danmark
    * Everything can be found from the front page, hence parse_article has been made obsolete and removed. This has also lead to other minor changes within the code 
    
**Hungary**
* Fidesz
    * Extra functionality to automatically generate front pages since their urls change like one would expect from a static scraper and the clicking functionality does not work for this website
* Hvim
    * Has implemented extra functionality to find and load YouTube links since these links does not appear in the HTML until the video is clicked
* Viktor Orban - beszedek, hirek and interjuk

**Italy**
* Familyday
* Gioventu nazionale
* Pro vite a famioglia
    * Utilises the `click_and_collect_links_and_publication_dates` function rather than the standard `click_and_collect_links` function, due to the publication date of the article only being accessible from the front page (see [Shared functions - scrapy](#dynamic_click_scrapy_functions.py))

**Romania**
* Cultura vietii

**Sweden**
* Motstandsrørelsen
* Nordfront SE
    * The HTML for some older articles on this website vary from the HTML of newer articles, and two sets of queries has therefore been implented along with functionality to spot the different formats
* Nya tider

**United Kingdom**
* GB news
    * Has implemented to scroll beyond what is visible on the site to reach older articles (the site uses a FIFO model). Besides acessing more articles this also makes the max_scrolls obsolete since the scroll functionality in general differs from the rest of the dynamic_scroll scrapers
* Lotus eaters
    * Has disabled 'ROBOTSTXT_OBEY' via custom_settings. *NOTE:* Running this scraper is in direct violation with rules set by the website in their robots.txt
    * Articles on this website is rendered using both scrolling and clicking. This scraper does therefore use a unique set of functions to handle this (see [Shared functions](#Shared-functions)). The number of articles for this scraper is consequently controlled by `max_loads` rather than `max_scrolls` or `max_clicks`
* Mallard
* Mansworld magazine
* Modernity
:::

### Shared functions - scrapy
As briefly mentioned in [Folder structure](#Folder-structure) a functions folder has been created in order to contain all shared functions within this repository for both webscrapers and PyTube scrapers. The functions of relevance to webscrapers can be found within this tree and will be reviewed individually.
```
── functions
   ├── scraper_functions
   │   ├── dynamic_click_scrapy_functions.py
   │   ├── dynamic_scroll_and_click_scrapy_functions.py
   │   ├── dynamic_scroll_scrapy_functions.py
   │   ├── general_functions.py
   │   ├── static_scrapy_functions.py
   │   └── ...
   └── ...
```
#### general_functions.py
The function class within this script is called `General_Functions` and contains the following functions:
* `clean_text` : Takes a string as input and cleans it for `\n`, `\r`, `\t` and spare spaces 
* `join_and_clean` : Takes a list of strings, joins them and cleans the resulting string

#### static_scrapy_functions.py
The function class within this script is called `Static_Scrapy` and contains the following functions:
* `get_feed_output_path` : 
    * Constructs the absolute output file path for the feed based on Scrapy settings.
    * Args:
        * settings (dict): The Scrapy project settings.
        * name (str): The name of the spider.
        * region (str): The region for which the spider runs.
    * Returns:
        * str: Absolute file path or URI where the feed should be saved.
    * Raises:
        * ValueError: If no 'FEEDS' setting is found.
* `load_existing_links` : 
    * Loads previously scraped article links from a JSON Lines (.jl) file. This helper reads the file line-by-line, parses each line as JSON, and collects values under the "article_link" key into a set. Invalid JSON lines are silently skipped. If the file does not exist, an empty set is returned.
    * Args:
        * save_path (str): Path to the JSON Lines file containing scraped items.
    * Returns:
        * set: A set of unique article links already present in the file.
* `setup_from_crawler` :
    * Sets up the spider instance with required attributes and connects the `open_spider` signal.
    * Args:
        * spider (scrapy.Spider): The spider instance being set up.
        * crawler (scrapy.Crawler): The Scrapy crawler instance.

* `initialize` :
    * Initializes the spider with optional maximum page limit and default attributes.
    * Args:
        * spider (scrapy.Spider): The spider instance to initialize.
        * max_pages (int, optional): Optional limit for the number of pages to scrape.
* `turn_page` :
    * Follows a pagination link to the next page if available and within the page limit.
    * The current page number is read from `response.meta['current_page']` (defaulting to 1).
    * If `next_page` is truthy and the spider has not reached `MAX_PAGES`, this method yields a new `Request` to the next page and increments the page counter in `meta`.
    * Args:
        * spider (scrapy.Spider): The active spider instance. Must have `MAX_PAGES` set (or None for no limit).
        * response (scrapy.http.Response): The current response object containing meta.
        * next_page (str | None): URL (absolute or relative) for the next page, or None if no next page exists.
        * callback (callable): The callback function to handle the next page response.
    * Returns:
        * scrapy.Request | None: A `Request` to the next page when pagination should continue, otherwise None.


#### dynamic_scroll_scrapy_functions.py
The function class within this script is called `Dynamic_Scroll_Scrapy` and contains the following functions:
* `get_feed_output_path`, `load_existing_links`, `setup_from_crawler` and `initialize` : Identical to the functions of identical names within [Static_Scrapy](#static_scrapy_functions.py) except for defining maximum scroll limit rather than maximum page limit
* `scroll_adaptive` :
    * Scrolls a Playwright page adaptively until no new content loads or a scroll limit is reached.
    * The function scrolls to the bottom repeatedly, checking for growth in either:
        * total document height, or
        * number of elements matching `article_selector`.
    * If no growth is detected, the wait time is increased (up to `max_wait`) for a few plateau checks before concluding the page is fully loaded.
    * Args:
        * page (playwright.async_api.Page): The Playwright page instance to scroll.
        * article_selector (str): CSS selector for items expected to load dynamically (e.g., article cards). Used to detect new content.
        * max_scrolls (int, optional): Maximum number of scrolls to perform. None for unlimited.
        * start_wait (int, optional): Initial wait time after a scroll in milliseconds.
        * max_wait (int, optional): Maximum wait time between checks in milliseconds.
        * growth_factor (float, optional): Multiplier for increasing wait time when no change is detected.
        * plateau_checks (int, optional): Number of consecutive "no change" checks allowed per scroll before stopping.
        * post_scroll_pause (int, optional): Extra pause after detecting growth, in milliseconds.
    * Returns:
        * str: The final rendered HTML content after adaptive scrolling.
* `fetch_with_playwright_adaptive` :
    * Fetches a fully rendered page using Playwright with adaptive scrolling.
    * This is a convenience wrapper around `scroll_adaptive`. It:
        * launches a headless Chromium browser,
        * navigates to `url`,
        * adaptively scrolls until content stops growing (or max scrolls are reached),
        * returns the final HTML.
    * Args:
        * url (str): The target page URL.
        * article_selector (str): CSS selector for dynamically loaded items used for growth detection.
        * max_scrolls (int, optional): Maximum number of scrolls to perform. None for unlimited.
        * start_wait (int, optional): Initial wait time after a scroll in milliseconds.
        * max_wait (int, optional): Maximum wait time between checks in milliseconds.
        * growth_factor (float, optional): Multiplier for increasing wait time when no change is detected.
        * plateau_checks (int, optional): Number of consecutive "no change" checks allowed per scroll.
        * post_scroll_pause (int, optional): Extra pause after detecting growth, in milliseconds.
    * Returns:
        * str: The final rendered HTML content after adaptive scrolling.
* `scroll` :
    * Scrolls the page to the bottom up to `max_scrolls` times or until no more new content is loaded.
    * Args:
        * page (playwright.async_api.Page): The Playwright page instance.
        * max_scrolls (int, optional): Maximum number of scrolls. None for unlimited.
        * wait_time (int, optional): Milliseconds to wait after each scroll (default: 2000).
    * Returns:
        * str: The final page content after scrolling.
* `fetch_with_playwright` :
    * Uses Playwright to fetch fully rendered page content with optional scrolling.
    * Args:
        * url (str): The target page URL.
        * max_scrolls (int, optional): Number of scrolls to simulate (None for infinite).
        * wait_time (int, optional): Wait time between scrolls in milliseconds.
    * Returns:
        * str: Final HTML content after scrolling.


#### dynamic_click_scrapy_functions.py
The function class within this script is called `Dynamic_Click_Scrapy` and contains the following functions:
* `get_feed_output_path`, `load_existing_links`, `setup_from_crawler` and `initialize` : Identical to the functions of identical names within [Static_Scrapy](#static_scrapy_functions.py) except for defining maximum click limit rather than maximum page limit
* `click_and_collect_links` :
    * Clicks a "load more" / pagination button repeatedly and collects unique links from the page.
    * The function opens `url` in headless Chromium, optionally dismisses cookie/consent popups, then performs a click loop:
        * After each click, it waits incrementally (`wait_time` × retry index) up to `incremental_retries` times to allow JS-rendered content to appear.
        * Links are extracted via `links_selector` and normalized to absolute URLs.
        * The loop stops when:
            * `max_clicks` is reached,
            * no button is found or the button becomes hidden,
            * a stop selector is matched (`stop_when_button_has_class`),
            * the button’s class attribute contains a stop class (`stop_when_button_has_class_attr`),
            * or a click produces no new links after retries.
    * Selectors may be CSS or raw XPath. Raw XPath is auto-detected and routed through Playwright’s XPath locator.
    * Args:
        * url (str): The starting page URL to open.
        * click_button_selector (str): CSS or XPath selector for the "load more" button. If multiple match, the last match is used.
        * links_selector (str, optional): CSS or XPath selector for link elements to collect. Must be provided for this links-only variant.
        * max_clicks (int, optional): Maximum number of clicks to perform. None for unlimited.
        * wait_time (int, optional): Base wait time (ms) between click and extraction retries.
        * timeout_time (int, optional): Navigation timeout for the initial page load, in ms.
        * stop_when_button_has_class (str, optional): Selector whose presence indicates pagination should stop (e.g., a disabled button state element).
        * stop_when_button_has_class_attr (str | list[str], optional): One or more class-name fragments that, if found on the button itself, will stop pagination.
        * consent_selectors (list[str], optional): Custom selectors for cookie/consent buttons. If None, a small default list is used.
        * pagination_navigates (bool, optional): If True, treat each click as a navigation and wait for DOMContentLoaded after click.
        * incremental_retries (int, optional): Number of incremental waits after each click before deciding that no new links appeared.
    * Returns:
        * list[str]: A list of unique absolute URLs collected across all clicks.
    * Raises:
        * ValueError: If `links_selector` is not provided.

* `click_and_collect_links_and_publication_dates` :
    * Clicks a "load more" / pagination button repeatedly and collects links with publication dates.
    * This helper opens `url` in headless Chromium, optionally dismisses cookie/consent popups, then runs a click loop:
        * After each click, it waits incrementally to allow JS-rendered content to appear.
        * For every element matching `container_selector`, it extracts:
            * a link from `link_selector` (href normalized to an absolute URL),
            * a publication date from `publication_date_selector` (text, stripped).
        * Results are deduplicated by link.
        * The loop stops when:
            * `max_clicks` is reached,
            * no button is found or the button becomes hidden,
            * a stop selector is matched (`stop_when_button_has_class`),
            * the button’s class attribute contains a stop class (`stop_when_button_has_class_attr`),
            * or a click produces no new links.
    * Selectors may be CSS or raw XPath. Raw XPath is auto-detected and routed through Playwright’s XPath locator.
    * Args:
        * url (str): The starting page URL to open.
        * click_button_selector (str): CSS or XPath selector for the "load more" button. If multiple match, the last match is used.
        * container_selector (str): Selector for the outer container holding an item (e.g., an article card).
        * link_selector (str): Selector (relative to each container) for the link element.
        * publication_date_selector (str): Selector (relative to each container) for the publication date element.
        * max_clicks (int, optional): Maximum number of clicks to perform. None for unlimited.
        * wait_time (int, optional): Base wait time (ms) between click and extraction retries.
        * stop_when_button_has_class (str, optional): Selector whose presence indicates pagination should stop (e.g., a disabled-state element).
        * stop_when_button_has_class_attr (str | list[str], optional): One or more class-name fragments that, if found on the button itself, will stop pagination.
        * consent_selectors (list[str], optional): Custom selectors for cookie/consent buttons. If None, a small default list is used.
        * pagination_navigates (bool, optional): If True, treat each click as a navigation and wait for DOMContentLoaded after click.
        * incremental_retries (int, optional): Number of incremental waits after each click before collecting containers again.
    * Returns:
        * list[dict]: A list of dictionaries with keys:
            * "link" (str): Absolute URL of the item.
            * "publication_date" (str | None): Extracted date text, if found.

* `click_and_collect_links_and_article_categories` :
    * Clicks a "load more" / pagination button repeatedly and collects links with article categories.
    * This helper opens `url` in headless Chromium, optionally dismisses cookie/consent popups, then runs a click loop:
        * After each click, it waits incrementally to allow JS-rendered content to appear.
        * For every element matching `container_selector`, it extracts:
            * a link from `link_selector` (href normalized to an absolute URL),
            * article categories from `article_categories_selector` (text, stripped).
        * Results are deduplicated by link.
        * The loop stops when:
            * `max_clicks` is reached,
            * no button is found or the button becomes hidden,
            * a stop selector is matched (`stop_when_button_has_class`),
            * the button’s class attribute contains a stop class (`stop_when_button_has_class_attr`),
            * or a click produces no new links.
    * Selectors may be CSS or raw XPath. Raw XPath is auto-detected and routed through Playwright’s XPath locator.
    * Args:
        * url (str): The starting page URL to open.
        * click_button_selector (str): CSS or XPath selector for the "load more" button. If multiple match, the last match is used.
        * container_selector (str): Selector for the outer container holding an item (e.g., an article card).
        * link_selector (str): Selector (relative to each container) for the link element.
        * article_categories_selector (str): Selector (relative to each container) for the article categories element.
        * max_clicks (int, optional): Maximum number of clicks to perform. None for unlimited.
        * wait_time (int, optional): Base wait time (ms) between click and extraction retries.
        * stop_when_button_has_class (str, optional): Selector whose presence indicates pagination should stop (e.g., a disabled-state element).
        * stop_when_button_has_class_attr (str | list[str], optional): One or more class-name fragments that, if found on the button itself, will stop pagination.
        * consent_selectors (list[str], optional): Custom selectors for cookie/consent buttons. If None, a small default list is used.
        * pagination_navigates (bool, optional): If True, treat each click as a navigation and wait for DOMContentLoaded after click.
        * incremental_retries (int, optional): Number of incremental waits after each click before collecting containers again.
    * Returns:
        * list[dict]: A list of dictionaries with keys:
            * "link" (str): Absolute URL of the item.
            * "article_categories" (str | None): Extracted category text, if found.

* `fetch_page_with_playwright` :
    * Uses Playwright to fetch a single fully rendered page without any scrolling or pagination interaction.
    * The function:
        * launches a headless Chromium browser,
        * navigates to `url` with a configurable timeout,
        * waits for `domcontentloaded` and then an extra fixed delay (`wait_time`) to allow client-side JavaScript to finish,
        * returns the final HTML markup of the page.
    * If navigation fails (e.g., timeout or network error), a warning is logged and an empty string is returned instead of raising an exception.
    * Args:
        * url (str): The URL of the page to fetch.
        * timeout_time (int, optional): Maximum time in milliseconds to wait for the initial navigation to complete (default: 60000).
        * wait_time (int, optional): Additional wait time in milliseconds after `domcontentloaded` before capturing the page content (default: 2000).
    * Returns:
        * str: The HTML content of the page after load and wait. If the page cannot be loaded, an empty string is returned.


#### dynamic_scroll_and_click_scrapy_functions.py
The function class within this script is called `Dynamic_Scroll_And_Click` and contains the following functions:
* `get_feed_output_path`, `load_existing_links`, `setup_from_crawler` and `initialize` : Identical to the functions of identical names within [Static_Scrapy](#static_scrapy_functions.py) except for defining maximum loads limit rather than maximum page limit
* `load_and_collect_links` :
    * Loads a listing page with Playwright and incrementally reveals more items by combining scroll actions and "load more" button clicks.
    * One successful load is counted when the number of elements matching `article_selector` increases due to either:
        * a scroll step, or
        * a click on the "load more" button (`load_more_selector`).
    * The behavior of `max_loads` is:
        * 0 → only the initial content is loaded (no scrolls or clicks),
        * N > 0 → perform at most N successful loads,
        * None → keep loading until scrolling/clicking no longer increases the article count or no button is available.
    * The function:
        * opens `url` in a headless Chromium context with a tall viewport,
        * best-effort dismisses common cookie/consent banners,
        * repeatedly:
            * performs a small scroll and checks for new articles,
            * optionally clicks a "load more" button if present, waiting for additional items to render,
            * stops when no further progress is made or `max_loads` is reached,
        * returns the final rendered HTML as a string.
    * Args:
        * url (str): The URL of the listing page to load.
        * article_selector (str): CSS selector for article/card elements to count.
        * load_more_selector (str): CSS selector for a "load more" button used to reveal additional items, if present.
        * max_loads (int | None, optional): Maximum number of successful loads (scroll/click that increases article count). If None, load until no new items appear.
        * wait_after_click (int, optional): Base wait time (in milliseconds) after scrolls or clicks before re-counting articles (default: 1200).
        * stop_when_button_has_class (str | list[str] | None, optional): One or more class-name fragments; if any are found in the button’s `class` attribute, loading stops (useful for disabled or "end of feed" states).
    * Returns:
        * str: The final HTML content of the page after all loads are completed.

* `fetch_page_with_playwright` : Identical to the function with the same name within [Dynamic_Click_Scrapy](#dynamic_click_scrapy_functions.py)

## Scrapers for YouTube
The vast majority of the scraped YouTube material has been collected using [PyTube](#PyTube), more specifically `PyTubefix`, due to it's simplicity, while a few channels, where `PyTube` was insufficient, have been scraped using [yt-dlp](#yt-dlp-docs). 

All YouTube scrapers have been included in the same [folder structure](#Folder-structure) as the scrapers for websites, however, unlike the `scrapy` scrapers they have been further nested into subfolders like seen below.
```
─── spiders
    ├── Country
    │   ├── PyTube
    │   │   └── All PyTube scrapers
    │   ├── yt-dlp
    │   │   └── All yt-dlp scrapers
    │   └── ...
    └── ...
```
This step of additional nesting has been implemented due to `scrapy` functionality. For further clarrification - all YouTube scrapers would work as intended no matter their placement within this repository, as long as all relative paths for function imports, etc. are adjusted to their location. However, when a `scrapy` scraper is called by parsing `scrapy crawl spider_name` to the terminal it will initially import all Python modules within all active `SPIDER_MODULES` as part of spider discovery before running the relevant scraper (in this case the scraper with the name `spider_name`). This works great in a project with only `scrapy` scrapers, however, in this case it would not only import `scrapy` scrapers but also all `PyTube` and `yt-dlp` scrapers. Since these scrapers contain executable code at module import time, any such code would execute when the module is imported, meaning that these YouTube scrapers may execute before the relevant `scrapy` scraper. 

In other words - if this further nesting was not implemented and the YouTube scrapers were still reachable from an active `SPIDER_MODULES` path, one of two things would happen:
* Best case : The `scrapy` scraper would run, but only after any import-time execution in the YouTube scrapers had completed. This would not only be extremely time consuming and highly inefficient but `PyTube` scrapers within this repository will not execute until one has associated a YouTube login to the current scraper job for age verification, hence a `scrapy` scraper would need a YouTube login to run.
* Worst case : Something within any non-scrapy script would fail (e.g. an incorrect import within a single YouTube scraper) causing the `scrapy` command to terminate during spider discovery, before even attempting to run the requested scraper.

>[!Note]
>While this `scrapy` functionality of how scrapers are discovered via module imports is of particular interest here, it's relevance is not limited to YouTube scrapers but also [Telegram scrapers](#Scrapers-for-Telegram), and any other script within an active spider module without further nesting.

### Requirements for running scrapers for YouTube
The required packages for the YouTube scrapers are included in the provided `requirements.txt`.

The YouTube scrapers are based primarily on the following dependencies:
- `pytubefix` (version 9.5.1)
- `dateparser` (version 1.2.2)
- `jsonlines` (version 4.0.0)
- `yt-dlp` (version 2025.12.8)

Furthermore one needs to install and setup `yt-dlp` separatedly (including `FFMPEG`), if to be used. Please see [yt-dlp](#yt-dlp) for further information.

Please note that while each YouTube scraper has its own dedicated script, they all require the full content of the `pytube_functions` folder within the `functions` folder.

### PyTube
Almost all scrapers based on `PyTube` within this repository are identical, except for the given channel URL, and consists of just two one-line function calls to functions within the [pytube_functions](#Shared-functions---PyTube) file.

Because the PyTube scrapers depend on shared modules in this repository (outside the scraper file itself), they must be executed as modules so Python treats the codebase as a package and resolves imports relative to the project structure. If a scraper is run as a plain script (e.g. `python full/path/to/pytube/scraper.py`), Python often sets the import root to that script’s directory, which can break imports of shared utilities in sibling/parent packages. The terminal call should therefore look like this:
```
python -m full.path.to.pytube.scraper
```
or, to keep consistency between different types of scrapers:
```
cd ./YOU-DARE/scrapers
python -m relative.path.to.pytube.scraper
```

The first time a PyTube scraper is run this message is printed in the terminal:
```
Please open https://www.google.com/device and input code ABC-DEF-GHI
Press enter when you have completed this step.
```
When following this link and entering this code one is asked to choose a YouTube user. This step has been implemented and hardcoded into the functions to circumvent being denied access to videos with age restriction etc. that would normally be accessable if one was logged into YouTube with an age verified user. Once this step has been completed the scraper will continue scraping the given channel URL. 
>[!Note]
>Depending on the environment this step might only be requered once, or it might need to be refreshed after closing and reopening the environment. 

#### General structure of a PyTube scraper
As previously stated almost all PyTube scrapers are identical and look like this:
```
from .....functions.pytubefix_functions import Pytubefix_Functions

# The link to the channel of interest
channel_url = 'https://www.youtube.com/@Handle/videos'

# Generates a jsonlines file and downloads all audio from all videos and 
# deposits it on the generated output path
output_path = Pytubefix_Functions.pytubefix_from_channel(
    channel_url, 
    __file__
)

# Retries videos that couldn't be downloaded
Pytubefix_Functions.retry_failed_downloads(output_path)
```
[Shared functions - PyTube](#Shared-functions---PyTube) will provide further clarrification of the actual functionality behind these function calls.

#### All sources collected using PyTube scrapers and possible exceptions to the general structure of a PyTube scraper
Here the full list of PyTube scrapers within this project will be listed, along with any exceptions to the general PyTube scraper structure:
:::info
**Denmark**
* Dansk regnbueråd
* Dansk Folkepartis Ungdom (DFU)
* Manderådet
* Maniphesto
* Rasmus Munch
* Retten til liv

**France**
* Alex Hitchens
* Charlotte Dornellas
* Iseul and Anne
* Jordan Bardella
* Julien Rochedy
* Le raptor
* Le syndicat de la familie
* Marion Marechal
* Nemesis media

**Hungary**
* Budahazy Edda
* Budahazy Gyorgy
* Duro Dora
* Fidelitas
* Fidesz
    * This PyTube scraper does not fetch all videos from a given channel but is instead given a list of YouTube links from a website. It therefore has its own set of functions to collect data from individual videos rather than entire channels. 
        * These YouTube links have been collected by a simple `scrapy` scraper (`fidesz_videos_SPIDER.py`). This scraper does in no way resemble any of the scrapers described [previously](#Scrapers-for-websites) and has therefore been omitted from that section. In short this scraper cralws the given website in a similar way as any other static scraper, collects video links from the front page and saves them as a `.txt` file, which is then used as input for the Fidesz Pytube scraper.
    * Due to the amount of videos from this source only some audio files have been collected by PyTube while the rest have been collected using yt-dlp. All metadata has been collected using PyTube.
* Mi Magunk
* Magyar Önvédelmi Mozgalom
* Novák Elód
* Project Legionary
* Totockai Laszlo
* Viktor Orban

**Italy**
* Essere Uomo
* Isabella Tovaglieri
* Lealta Azione
* Yasmin Pani

**Romania**
* Claudiu Tarziu
    * Does not only collect videos from a given channel but also shorts and lives
    * Does collect videos from three playlists and a single video along with the full channel
* Comunitatea identitara
* Noua drepta

**Spain**
* Alvise Perez
* Anthony Sanchez
* Desokupa TV
* Estudiants Pel Canvi
* Info vlogger
* La Catalunya woke
* Red pill podcast
* Roberto Vaquero
* Roma Gallardo
* Vox Espana
    * Due to the amount of videos from this source all audio files have been collected using yt-dlp, while all metadata has been collected using PyTube.
    * Only videos released after 2024-01-01 have been scraped. As a formality it has further been implemented that any videos released after 2026-01-01 will not be scraped. 
* Wall street Wolverine

**Sweden**
For all You-Tube sources for Sweden, only videos released between 2021-06-01 and 2025-06-30 has been scraped.
* Alternativ for Sverige
* Christion Peterson
* Det fria Sverige
* Inblick med Nick
* SDMicke
* SDMonkan
* The golden one

**United Kingdom**
* Dangerfield
* Hamza Ahmed
* Reform UK
* Zoomer historian
:::

#### Shared functions - PyTube
All functions relevant to all `PyTube` scrapers are found in the script `pytubefix_functions.py` within the functions folder. The function class within this script is called `Pytubefix_Functions` and contains the following functions:
* `parse_partial_date` :
    * Parses a potentially partial / fuzzy date string into a `datetime.date`.
    * This helper uses `dateparser.parse` with settings that bias parsing toward:
        * the first day of the month when the day is missing,
        * dates in the past when the year is ambiguous.
    * Args:
        * date_str (str): A date string such as "2024", "2024-10", "Oct 2024", etc.
    * Returns:
        * datetime.date: The parsed date component.
    * Raises:
        * ValueError: If the input cannot be parsed into a date.

* `extract_source` :
    * Extracts a YouTube channel handle from a URL.
    * The function looks for the `@handle` pattern in the URL. If no handle is found, it returns "Unknown".
    * Args:
        * url (str): A YouTube channel URL (e.g., "https://www.youtube.com/@SomeChannel").
    * Returns:
        * str: The extracted channel handle (without "@"), or "Unknown" if not found.

* `generate_output_path` :
    * Generates a standardized output path for Pytubefix scrapers.
    * This helper derives an output directory using the caller script path (`file`) and an expected repository layout. It is designed for cases where scraper scripts live under a country folder and output should land under:
        * `<repo_root>/data/<country>/<script_name>/`
    * Notes:
        * `file` should almost always be `__file__` from the calling script.
        * `nesting_level` controls how far upward to walk from the script location to find the repository root and country folder.
    * Args:
        * file (str | Path): Path to the calling script. Typically `__file__`.
        * nesting_level (int, optional): Number of parent directories to traverse to locate the repository root (default: 4).
    * Returns:
        * pathlib.Path: The generated output path directory.

* `pytubefix_from_channel_jsonlines` :
    * Scrapes video metadata from a YouTube channel and writes results to a JSON Lines file.
    * The function uses `pytubefix.Channel` to iterate channel content types (videos/shorts/live), filters out items already present in `videos.jl`, and appends new metadata entries.
    * Writing is buffered and flushed every `flush_every` items to reduce IO overhead and to allow long runs to resume safely after interruptions.
    * Date filtering:
        * If a video's publish date is available, `from_date` and `to_date` filters are applied.
        * If publish date is missing, the item is still written with an empty string date.
    * Args:
        * url (str): YouTube channel URL.
        * output_path (pathlib.Path | str): Directory where `videos.jl` will be written.
        * source (str, optional): Source label to write in output. If empty, it is derived from the URL handle.
        * from_date (datetime.date, optional): If set, stop scraping when encountering an older publish date than this threshold.
        * to_date (datetime.date, optional): If set, skip items newer than this threshold.
        * flush_every (int, optional): Number of buffered items before writing to disk.
        * videos (bool, optional): Whether to include channel videos.
        * shorts (bool, optional): Whether to include channel shorts.
        * live (bool, optional): Whether to include channel live videos.
    * Returns:
        * None

* `pytubefix_from_channel_audio` :
    * Downloads audio (.m4a) for channel videos and logs failures to a JSON Lines file.
    * The function creates/uses an `m4a_files/` folder under `output_path` and downloads the first available audio-only stream for each selected video.
    * Deduplication:
        * If `check_for_downloaded` is True, existing `.m4a` filenames are used to skip already-downloaded video_ids.
    * Failure logging:
        * Failures are appended immediately to `not_downloaded.jl` as:
            * `{"error": [title, video_id, "<exception>"], "retries": 0}`
        * Previously logged failures are loaded at startup to avoid duplicate entries.
    * Date filtering:
        * If a publish date exists, the date filters apply.
        * If publish date is missing, the function downloads audio anyway (and prints a notice).
    * Args:
        * url (str): YouTube channel URL.
        * output_path (pathlib.Path | str): Base directory where `m4a_files/` and logs live.
        * from_date (datetime.date, optional): If set, stop processing when encountering a video older than this threshold.
        * to_date (datetime.date, optional): If set, skip videos newer than this threshold.
        * videos (bool, optional): Whether to include channel videos.
        * shorts (bool, optional): Whether to include channel shorts.
        * live (bool, optional): Whether to include channel live videos.
        * check_for_downloaded (bool, optional): If True, skip any video_id already present as `<video_id>.m4a` in the audio folder.
    * Returns:
        * None

* `pytubefix_from_channel` :
    * End-to-end channel scraper: writes metadata to JSON Lines and downloads audio files.
    * This is a convenience wrapper that:
        * resolves/creates an output directory (generated from `file` unless `output_path` is given),
        * runs `pytubefix_from_channel_jsonlines` to append metadata to `videos.jl`,
        * runs `pytubefix_from_channel_audio` to download `.m4a` files.
    * Args:
        * url (str): YouTube channel URL.
        * file (str | Path): Path to the calling script. Typically `__file__`.
        * nesting_level (int, optional): Passed to `generate_output_path` if output_path is not set.
        * source (str, optional): Source label written into output. If empty, derived from URL.
        * output_path (pathlib.Path | str, optional): Custom output directory to use instead of generating one from `file`.
        * from_date (datetime.date, optional): Lower bound for publish date filtering.
        * to_date (datetime.date, optional): Upper bound for publish date filtering.
        * videos (bool, optional): Whether to include channel videos.
        * shorts (bool, optional): Whether to include channel shorts.
        * live (bool, optional): Whether to include channel live videos.
        * check_for_downloaded (bool, optional): Whether to skip audio downloads that already exist.
    * Returns:
        * pathlib.Path: The output directory used for writing metadata and audio.

* `retry_failed_downloads` :
    * Retries downloading audio files listed in `not_downloaded.jl`.
    * This function reads failures from `not_downloaded.jl`, attempts to download each missing `.m4a` again, and rewrites the file with only the still-failing items.
    * Each retry increments a `retries` counter and appends a `retry_error_<i>` field preserving the full retry history. The original "error" field is retained.
    * If all failures are recovered, `not_downloaded.jl` is deleted.
    * Args:
        * output_path (pathlib.Path | str): Directory containing `m4a_files/` and `not_downloaded.jl`.
        * max_attempts (int, optional): Maximum number of retry rounds.
        * sleep_seconds (int, optional): Sleep between individual retries to reduce rate limits.
    * Returns:
        * None

* `pytubefix_from_playlist_jsonlines` :
    * Equivalent to `pytubefix_from_channel_jsonlines`, but iterates over playlist videos instead of channel content types.
    * Differences compared to `pytubefix_from_channel_jsonlines`:
        * Does not accept `videos`, `shorts`, or `live` flags.

* `pytubefix_from_playlist_audio` :
    * Equivalent to `pytubefix_from_channel_audio`, but downloads audio for playlist videos instead of channel content types.
    * Differences compared to `pytubefix_from_channel_audio`:
        * Does not accept `videos`, `shorts`, or `live` flags.

* `pytubefix_from_playlist` :
    * Equivalent to `pytubefix_from_channel`, but operates on a playlist URL instead of a channel URL.
    * Differences compared to `pytubefix_from_channel`:
        * Does not accept `videos`, `shorts`, or `live` flags (playlist items are fixed).
        * Uses playlist-specific helpers:
            * `pytubefix_from_playlist_jsonlines`
            * `pytubefix_from_playlist_audio`

* `pytubefix_from_single` :
    * Single-video variant of `pytubefix_from_channel`.
    * Differences compared to `pytubefix_from_channel`:
        * Operates on exactly one video URL (no iteration).
        * Skips processing if the video is already present in `videos.jl`.
        * Performs explicit availability checks (private / unavailable / age-restricted).
        * Does not accept `videos`, `shorts`, `live`, or `check_for_downloaded`.

### yt-dlp
[yt-dlp](https://github.com/yt-dlp/yt-dlp) is a feature rich command line audio/video downloader and was primarily utilized when a channel had a significant amount of videos designated for download and PyTube seemed to rigid in its setup resulting in bot flagging and ratelimiting.

#### Structure of the yt-dlp setup
For each source designated for downlading a bash script (`.sh`) was created utilizing the command line feature. Each program was setup to handle several hurdles when downloading from YouTube such as:
- Bot-detection
- request wait times
- WebPO token
- login
- age-restricted content

##### Request wait times
Minimum Sleep intervals was set to 4.5 seconds between each video and maximum was set to 10 seconds to mimic "human" behaviour.

##### Metadata collection
Besides the standard jsonlines (see [Data collection - YouTube](#Data-collection---YouTube)) an archive.txt was defined to keep track of all videos being downloaded in order to get a sense of the available videos from each source and further to get logging for each bash run.

##### Audio quality control & output
`FFMPEG` was further utilized to control soundquality. [FFMPEG](https://ffmpeg.org/) is a free software for audio/video processing. In scripts within this repostiory the build-in command line from yt-dlp was used to point at the FFMPEG program folder. This means that the desired videoquality as m4a could be defined.

The download quality was handled directly in each script as such:
```bash!
--ffmpeg-location "$FFMPEG_DIR" \
--extractor-args "youtube:po_token=web.gvs+$TOKEN_URL;player_client=mweb" \
--format "ba[ext=m4a]/ba[acodec^=opus]/ba/best" \
--audio-format m4a \
```
This was also necessary in order to force the right video client to not get errors from the Youtube SABR, a persistent [issue](https://github.com/yt-dlp/yt-dlp/issues/12482?utm_source=chatgpt.com) with YouTube download. In order for this to work a PO-token was also necessary as SABR downloader has, at the time of writing this, not been created nor implemented.

##### WebPO token
YouTube increasingly requires a PO-token to solve its anti-bot “n-challenge”.
Without it, yt-dlp may fail with errors like:
- n challenge solving failed
- No video formats found
- Sign in to confirm you’re not a bot

To solve this reliably, a local PO-token provider server is run using [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider), which lets yt-dlp request fresh tokens.

For a higherlevel overview it looks like this:
```
yt-dlp
  │
  ├── cookies.txt        (authentication)
  ├── POT request ─────▶ bgutil PO server (Node.js)
  │                         │
  │                         └── generates fresh PO-token
  │
  └── metadata / audio / video
```
For further automatisation the workflow to setup the PO-token was set up like this:
```bash!
# Activate environment
source /work/YOU-DARE/environment/bin/activate
# Change directory
cd bgutil-ytdlp-pot-provider/server
# Install yt-dlp if not already done
pip install yt-dlp
# Install npm and typescript
npm install 
npx tsc
# Install nvm
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Change dir to bashrc
source ~/.bashrc
# Install nvm vervion 20
nvm install 20
# Tell terminal to use -v 20
nvm use 20
# setting up node
node build/main.js

or in the bagground
nohup node/build/main.js > /tmp/pot.log 2>&1 &
nohup node build/main.js > /tmp/pot.log 2>&1 &
echo !$ > /tmp/pot.pid

Verify its alive by pinging it
curl -s 'http://[::1]:4416/ping' || curl -s http://127.0.0.1:4416/ping
```
>[!WARNING]
>The setup of the token was done every time before each run. Be sure to kill the automatic PO-token after use if run in background.


##### Cookies
To handle the bot-detection and to get access to age-restricted videos a Firefox/Chrome extension, such as the cookies.txt extension, was downloaded in the browser to extract cookies from a logged in session of YouTube and then placed in the repository. 
>[!WARNING]
This has its issues such as temporary banning from YouTube.


#### All sources collected using yt-dlp scrapers and possible exceptions to the general structure of a yt-dlp scraper
Here the full list of yt-dlp scrapes within this project will be listed, along with any exceptions to the general yt-dlp scraper structure:
:::info
**Hungary**
* Fidesz (HU)
    * Most audio files have been collected using yt-dlp, while all metadata has been collected using PyTube

**Romania**
* George Simion

**Spain**
* Vox
    * All audio files have been collected using yt-dlp, while all metadata has been collected using PyTube

**Sweden**
* Riks
:::

##### Regarding high-volume channels
For channels with a large amount of videos, collection was not possible in one go. In such cases, YouTube data is requested in batches. 

## Scrapers for Telegram
All Telegram data has been collected the API/OSINT tool [Telepathy](https://github.com/proseltd/Telepathy-Community), which is  developed for investigating and archiving Telegram chats.

As was the case for [YouTube scrapers](#Scraper-for-YouTube), and by the same reasoning, all scrapers for Telegram channels have been nested within the main `spiders` folder like this:
```
─── spiders
    ├── Country
    │   ├── Telegram
    │   │   └── All Telepathy scrapers
    │   └── ...
    └── ...
```

### Requirements for running scrapers for Telegram
In order to run any of the Telegram scrapers within this repository one first needs to set up Telepathy. This is done using git to clone the repo and through pip install in python, by parsing the following commands in bash:
```!bash
$ pip3 install telepathy
$ git clone https://github.com/jordanwildon/Telepathy.git
$ cd Telepathy
$ pip install -r requirements.txt
$ pip3 install cryptg
```
In this repository `telepathy` version 2.3.4 was used.

Setup furthermore requires two-factor validation calling the Telegram API to validate one's account, phone number and hash code. Phonenumber, code and login can be saved in a `.txt` file in a folder directly within the repository for easy access. Such a `.txt` has been set up for internal use within CALDISS, however, for obvious reasons this file has not been included .

### General structure of a Telepathy scraper
All Telepathy scrapers was written as a `.sh` script and run in a python bash terminal. They all follow the same structure where a general example is seen below:
```
#!/usr/bin/env bash

# things to get
telepathy --target telegram_channel --comprehensive --replies
```
The `--target` and `--replies` flags ensured all necessary context for each channel and its replies. `--comprehensive` was added to get more metadata about replies, such as the amount of replies and reactions. In some cases this was reduced even further to:
```
#!/usr/bin/env bash

# things to get
telepathy -t telegram_channel -c -r
```

### All sources collected using Telepathy scrapers
Here the full list of Telepathy scrapers within this project will be listed. 
:::info
**Denmark**
* maniphestocore

**France**
* papacitofdp
* RNJ_officiel

**Hungary**
* durodora
* InczeBelaLegionarius
* jobbszelso
* legiohungaria
* mihazankifjai
* novakelod
* toroczkai

**Italy**
* dodiciraggi
* la_fionda
* retedeipatrioti

**Romania**
* comunitatea_identitara
* nouadreapta
* revistaRost

**Spain**
* AltRightEspana
* AlvisePerez
* cataluynaac
* herQles
* Revuelta_es
* unetenucleonacional
* vitoquilestelegram

**Sweden**
* Aktivklubb_Sverige
* GymXIV
* GymXIV2
* thegoldenone
* WBsthlm

**United Kingdom**
* reformuk
:::

## Reviewing scrapers

All scrapers were reviewed by manually inspecting five randomly drawn entries from each data set. The script for drawing the subset to review is located in the review-foler (`review.py`).

The review directory further contains a script for confirming the number of expected texts from the UK source "Modernity" (`confirm_UK-modernity_count.py`).

## Post-processing

The final datasets collected from these scrapers are in jsonlines format with one line per text. Data collected from the YouTube and Telegram scrapers are not immediately in this format and has been processed using scripts like the ones provided in the post-processing directory. The scripts here are provided as examples, as the same processing was conducted for each YouTube and Telegram source, respectively.

### Post-processing YouTube sources

YouTube scrapers provide metadata and audiofiles, separately. In order to arrive at text data, all audiofiles were auto-transcribed using a Whisper-based transcriber-application hosted by [UCloud](https://docs.cloud.sdu.dk/). No source code is provided for this application here, but merely the functions used to prepare audio files for transcription via this applicaiton (`dataprep_YT/prep_for_transcriber_YT.py`).

Metadata and transcribed video data were joined to a singular jsonlines file using a script like (`dataprep_YT/prep_data_join_YT`)


### Post processing Telegram sources

As Telegram sources could include either a dataset of posts or a dataset of posts *and* replies, sources were processed to single jsonlines files using scripts like the ones found in the `dataprep_TELEGRAM` directory. 

- `prep_post_only.py`: Writes the collected .csv data to jsonlines.
- `prep_posts_and_replies.py`: Combines posts and replies to a single `thread_text` and writes to jsonlines with one line per post.

>[!NOTE]
>The datasets generated using the Telegram post-processing functions here were only used for providing human-readable versions of the data to be used for manual annotation. The final datasets uses a different post-processing for Telegram sources. See the main YOU-DARE project repository for further details.
