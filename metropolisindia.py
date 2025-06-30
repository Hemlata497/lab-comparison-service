from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import re

async def main(playwright, city_name="Mumbai"):
    city_name = city_name.capitalize()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    # Block images, fonts, stylesheets for faster loading
    await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "stylesheet"] else route.continue_())
    page = await context.new_page()

    try:
        print("Navigating to https://www.metropolisindia.com/")
        await page.goto('https://www.metropolisindia.com/', wait_until='domcontentloaded')

        print("Waiting for the location dropdown button...")
        dropdown_selector = 'button#locationDropdown[current-city]'
        dropdown_button_locator = page.locator(dropdown_selector)
        try:
            await dropdown_button_locator.wait_for(state='visible', timeout=15000)
        except PlaywrightTimeoutError:
            print(f"Error: Dropdown button not found with selector: {dropdown_selector} within timeout.")
            return

        if await dropdown_button_locator.count() == 0:
            print("Error: Dropdown button not found after wait, count is 0.")
            return

        print("Clicking the location dropdown button...")
        await dropdown_button_locator.scroll_into_view_if_needed()
        await dropdown_button_locator.click()

        print(f"Waiting for the city selection list for {city_name}...")
        city_selector = f'div.city-selection-wrapper[city-data="{city_name}"]'
        city_element_locator = page.locator(city_selector)
        try:
            await city_element_locator.wait_for(state='visible', timeout=15000)
        except PlaywrightTimeoutError:
            print(f"Error: City '{city_name}' element not found within timeout with selector: {city_selector}")
            return

        city_count = await city_element_locator.count()
        print(f"Found {city_count} city element(s) for {city_name}.")
        if city_count == 0:
            print(f"Error: City '{city_name}' not found in the selection list after wait.")
            return

        try:
            city_text = await city_element_locator.first.text_content(timeout=5000) or "No text content"
            print(f"City element text: {city_text}")
        except Exception as e:
            print(f"Warning: Failed to retrieve city text - {str(e)}. Proceeding with click.")

        if await city_element_locator.first.is_visible() and await city_element_locator.first.is_enabled():
            print(f"Clicking city: {city_name}")
            await city_element_locator.first.scroll_into_view_if_needed()
            await city_element_locator.first.click()
        else:
            print(f"Error: City '{city_name}' is not visible or enabled.")
            return

        print("Waiting for UI to update after selecting city...")
        await page.wait_for_timeout(2000)  # Reduced wait for UI update
        print(f"Successfully selected city: {city_name}")

        print("Starting to scrape test names, prices, and details from both sections...")

        all_tests_container_selectors = [
            '#test-all div.owl-carousel.owl-theme.package-slide.owl-loaded.owl-drag',
            '#nav-all div.owl-carousel.owl-theme.package-slide.owl-loaded.owl-drag'
        ]

        individual_test_item_selector = 'div.owl-item'
        test_price_selector = 'div.package-price h5'

        all_scraped_tests = []

        for container_selector in all_tests_container_selectors:
            print(f"\nAttempting to scrape from container: {container_selector}")

            # Adjust name selector based on container
            if container_selector.startswith("#test-all"):
                test_name_selector = 'h4.test-head'
            elif container_selector.startswith("#nav-all"):
                test_name_selector = 'h4.package-head'
            else:
                test_name_selector = 'h4'

            try:
                await page.locator(container_selector).wait_for(state='visible', timeout=15000)
                print(f"Found container: {container_selector}")

                # Batch extract all test items in this container
                test_data = await page.eval_on_selector_all(
                    f'{container_selector} {individual_test_item_selector}',
                    f'''
                    (nodes) => nodes.map(node => {{
                        const nameEl = node.querySelector('{test_name_selector}');
                        const priceEl = node.querySelector('{test_price_selector}');
                        const name = nameEl ? nameEl.textContent.trim() : 'N/A';
                        const rawPrice = priceEl ? priceEl.textContent.trim() : 'N/A';
                        const cleanPrice = rawPrice.replace(/[^\\d.]/g, '').replace(/^\\./, '') || 'N/A';
                        return {{ name: name, price: cleanPrice }};
                    }})
                    '''
                )
                # Filter incomplete data if needed
                filtered = [t for t in test_data if t['name'] != 'N/A' and t['price'] != 'N/A']
                all_scraped_tests.extend(filtered)
                print(f"Found {len(filtered)} valid test items in this container.")
            except PlaywrightTimeoutError:
                print(f"Warning: Container '{container_selector}' not found within timeout. Skipping this section.")
            except Exception as e:
                print(f"An unexpected error occurred while scraping from '{container_selector}': {e}")

        os.makedirs("output", exist_ok=True)
        output_json_file = f"output/metropolis_tests_all_sections_{city_name}.json"
        if all_scraped_tests:
            with open(output_json_file, 'w', encoding='utf-8') as f:
                json.dump(all_scraped_tests, f, ensure_ascii=False, indent=4)
            print(f"\nScraped data from both sections saved to {output_json_file}")
        else:
            print("\nNo structured test data was scraped from any section.")

    except PlaywrightTimeoutError as e:
        print(f"Error: Playwright timeout during navigation or element interaction: {str(e)}")
    except Exception as e:
        print(f"An unhandled error occurred: {str(e)}")
    finally:
        print("Closing the browser...")
        await browser.close()



if __name__ == "__main__":
    import asyncio
    async def run_metropolis_direct():
        city = input("Enter the city name (e.g., Delhi): ").strip() or "Mumbai"
        async with async_playwright() as p:
            await main(p, city)
    asyncio.run(run_metropolis_direct())
