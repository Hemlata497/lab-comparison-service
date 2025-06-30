from playwright.async_api import async_playwright
import json
import re
import os
import pandas as pd
import asyncio

async def scrape_page(context, url):
    page = await context.new_page()

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_selector('li.product', timeout=10000)

        # Use eval_on_selector_all for batch extraction
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

async def scrape_srl_diagnostics(playwright, base_url, output_filename="output/srl_test.json"):
    # Launch browser and block unnecessary resources
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

    # Run all scrapes concurrently using shared context
    tasks = [scrape_page(context, url) for url in urls]
    results = await asyncio.gather(*tasks)

    # Flatten results
    scraped_data = [item for sublist in results for item in sublist]

    await browser.close()

    # Save results
    os.makedirs("output", exist_ok=True)
    if scraped_data:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"✅ SRL data saved to {output_filename}")
    else:
        print(f"⚠️ No data scraped from SRL.")

# For direct execution
if __name__ == "__main__":
    
    import time
    async def main():
        base_url = "https://srldiagnostics.in/shop/?orderby=price"
        start_time = time.time()
        async with async_playwright() as p:
            await scrape_srl_diagnostics(p, base_url)
        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
    asyncio.run(main())
