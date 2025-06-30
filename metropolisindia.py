from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import re
import time
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

async def main(playwright, city_name="Mumbai"):
    start_time = time.time()
    city_name = city_name.capitalize()

    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        print(f"Navigating to https://www.metropolisindia.com/")
        await page.goto('https://www.metropolisindia.com/', wait_until='domcontentloaded')

        # Click city dropdown fast
        dropdown = page.locator('button#locationDropdown[current-city]')
        await dropdown.click(force=True)

        city_selector = f'div.city-selection-wrapper[city-data="{city_name}"]'
        city = page.locator(city_selector)

        try:
            await city.first.click(timeout=3000)
        except:
            print(f"❌ City '{city_name}' not found.")
            return

        print("✅ City selected. Scraping...")

        # Give some time for city-specific test data to load
        await page.wait_for_timeout(2000)

        all_scraped_tests = []

        containers = [
            '#test-all div.owl-carousel.owl-theme.package-slide.owl-loaded.owl-drag',
            '#nav-all div.owl-carousel.owl-theme.package-slide.owl-loaded.owl-drag'
        ]

        for container in containers:
            print(f"➡️ Scraping: {container}")
            try:
                await page.locator(container).wait_for(state='visible', timeout=3000)
                test_items = await page.locator(f'{container} div.owl-item').all()

                for item in test_items:
                    test_info = {}
                    try:
                        name_elem = item.locator('h4.test-head, h4.package-head')
                        name = await name_elem.first.text_content()
                        test_info['name'] = name.strip() if name else "N/A"
                    except:
                        test_info['name'] = "N/A"

                    try:
                        price_elem = item.locator('div.package-price h5')
                        price_raw = await price_elem.first.text_content()
                        if price_raw:
                            price = re.sub(r"[^\d.]", "", price_raw).lstrip(".")
                            test_info['price'] = price or "N/A"
                        else:
                            test_info['price'] = "N/A"
                    except:
                        test_info['price'] = "N/A"

                    if test_info['name'] != "N/A" or test_info['price'] != "N/A":
                        all_scraped_tests.append(test_info)

            except Exception as e:
                print(f"⚠️ Skipping {container}: {e}")

        os.makedirs("output", exist_ok=True)
        out_file = f"output/metropolis_tests_all_sections_{city_name}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_scraped_tests, f, ensure_ascii=False, indent=2)

        print(f"✅ Scraped {len(all_scraped_tests)} tests. Saved to {out_file}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        duration = round(time.time() - start_time, 2)
        print(f"Total time taken: {duration} seconds")
        await browser.close()


if __name__ == "__main__":
    async def run():
        city = input("Enter the city name (e.g., Delhi): ").strip() or "Mumbai"
        async with async_playwright() as p:
            await main(p, city)
    asyncio.run(run())