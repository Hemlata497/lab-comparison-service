from playwright.async_api import async_playwright
import json
import time
import re
import os
import pandas as pd
import asyncio

async def scrape_page(playwright, url):
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=120000)
        await page.wait_for_selector('li.product', timeout=15000)
        product_elements = await page.query_selector_all('li.product')
        scraped = []
        for product in product_elements:
            try:
                title_element = await product.query_selector('h2.woocommerce-loop-product__title')
                price_element = await product.query_selector('span.price')
                title = (await title_element.text_content()).strip() if title_element else 'N/A'
                price = (await price_element.text_content()).strip() if price_element else 'N/A'
                formatted_price = re.sub(r'[^-Za-z0-9. ]+', '', price) if price else 'N/A'
                if not formatted_price:
                    formatted_price = 'N/A'
                scraped.append({
                    'test': title,
                    'price': formatted_price
                })
            except Exception as e:
                print(f"Error scraping product: {e}")
                continue
        await browser.close()
        return scraped
    except Exception as e:
        print(f"Failed to load {url}: {e}")
        await browser.close()
        return []

async def scrape_srl_diagnostics(playwright, base_url, output_filename="output/srl_test.json"):
    scraped_data = []
    max_page = 3  # Only first three pages
    print(f"Starting scraping from {base_url}...")
    # Prepare URLs for first three pages
    urls = []
    for page_num in range(1, max_page + 1):
        if page_num == 1:
            urls.append(base_url)
        else:
            parts = base_url.split('?')
            url = f"{parts[0]}page/{page_num}/?{parts[1]}" if len(parts) > 1 else f"{parts[0]}page/{page_num}/"
            urls.append(url)
    # Scrape all three pages concurrently
    print(f"Scraping pages: 1 to 3 concurrently")
    tasks = [scrape_page(playwright, url) for url in urls]
    batch_results = await asyncio.gather(*tasks)
    for result in batch_results:
        scraped_data.extend(result)
    print("SRL Scraping completed.")
    if scraped_data:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"Scraped data from SRL saved to {output_filename}")
    else:
        print(f"No data scraped from SRL.")

# For direct script run (optional)
if __name__ == "__main__":
    async def main():
        base_url = "https://srldiagnostics.in/shop/?orderby=price"
        async with async_playwright() as p:
            await scrape_srl_diagnostics(p, base_url)
    asyncio.run(main())