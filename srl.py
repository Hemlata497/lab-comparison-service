from playwright.async_api import async_playwright
import re
import asyncio

async def scrape_page(context, url):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=90000)
        await page.wait_for_selector('li.product', timeout=50000)
        scraped = await page.eval_on_selector_all(
            'li.product',
            '''(nodes) => nodes.map(node => {
                const title = node.querySelector('h2.woocommerce-loop-product__title')?.textContent.trim() || 'N/A';
                const priceRaw = node.querySelector('span.price')?.textContent.trim() || 'N/A';
                const cleanPrice = priceRaw.replace(/[^-\\w. ]+/g, '') || 'N/A';
                return { test: title, price: cleanPrice };
            })'''
        )
        await page.close()
        return scraped
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        await page.close()
        return []

async def scrape_srl_diagnostics(playwright, base_url):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] else route.continue_())
    print(f"Starting scraping from {base_url}...")
    max_page = 3
    urls = []
    for page_num in range(1, max_page + 1):
        if page_num == 1:
            urls.append(base_url)
        else:
            parts = base_url.split('?')
            url = f"{parts[0]}page/{page_num}/?{parts[1]}" if len(parts) > 1 else f"{parts[0]}page/{page_num}/"
            urls.append(url)
    print(f"Scraping pages 1 to {max_page} concurrently...")
    tasks = [scrape_page(context, url) for url in urls]
    results = await asyncio.gather(*tasks)
    scraped_data = [item for sublist in results for item in sublist]
    await browser.close()
    print(f" SRL scraped {len(scraped_data)} tests")
    return scraped_data  # Return data instead of saving

if __name__ == "__main__":
    import time
    async def main():
        base_url = "https://srldiagnostics.in/shop/?orderby=price"
        start_time = time.time()
        async with async_playwright() as p:
            data = await scrape_srl_diagnostics(p, base_url)
        print(f"Total execution time: {time.time() - start_time:.2f} seconds")
    asyncio.run(main())