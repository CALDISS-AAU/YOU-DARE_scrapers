from playwright.async_api import async_playwright
import asyncio

START_URL = "https://modernity.news/"
# You can adjust this selector if the site changes layout
ARTICLE_SELECTOR = "article, .post, .jeg_post, .td_module_wrap, .tdb_module_loop"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(START_URL, wait_until="domcontentloaded")

        prev_height = 0
        scroll_count = 0

        while True:
            scroll_count += 1
            # Count articles so far
            total_articles = await page.eval_on_selector_all(
                ARTICLE_SELECTOR, "els => els.length"
            )
            print(f"Scroll #{scroll_count} | Articles so far: {total_articles}")

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(12000)  # wait for new batch to load

            # Check if height changed
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                print("No more new content. Stopping.")
                break
            prev_height = new_height

        # Final count
        total_articles = await page.eval_on_selector_all(
            ARTICLE_SELECTOR, "els => els.length"
        )
        print(f"Finished after {scroll_count} scrolls.")
        print(f"Total articles detected: {total_articles}")

        await browser.close()

asyncio.run(run())
