# ### IMPORTS ###
# # External imports #
# import scrapy
# from scrapy import signals
# from scrapy.selector import Selector
# import asyncio
# from twisted.internet.defer import inlineCallbacks, returnValue
# from twisted.internet.threads import deferToThread
# from datetime import datetime
# from urllib.parse import urljoin
# # Internal imports #
# from ...items import ScrapersItem  # Imports the items from the items.py file
# from ...functions.scrapy_functions import Dynamic_Scrapy_Click  # Custom shared click functions
# from ...functions.scrapy_functions import DynamicClickAndWait # Custom click with wait
# from ...functions.general_functions import General_Functions  # Custom shared functions

# async def test():
#     links = await DynamicClickAndWait.click_and_collect_links(
#         url='https://nordfront.se/',
#         click_button_selector='//button[@id="load-more-articles"]',
#         links_selector='//*[@id="post-collections"]//a[contains(@class, "item") and @data-status="publish" and .//h1]',
#         max_clicks=30,
#         wait_time=5000
#     )
#     print(f"Collected {len(links)} links")
#     for l in links[:10]:
#         print(l)

# asyncio.run(test())


