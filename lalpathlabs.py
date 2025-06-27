from playwright.async_api import async_playwright
import json
from datetime import datetime
import re

async def run(playwright, location):
    # Start timing
    start_time = datetime.now()

    # Launch the browser (Chromium)
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    # List to store scraped data
    tests_data = []

    try:
        # Visit the page with user's location
        await page.goto(f'https://www.lalpathlabs.com/book-a-test/{location}')
        print(f"Opened page for location: {location}")

        # Wait for the page to load and test elements to appear
        await page.wait_for_load_state('networkidle')
        await page.wait_for_selector('div.col-12.col-sm-6.col-md-6.col-lg-4', timeout=10000)

        # Step 4: Scrape top 50 test elements
        test_elements = await page.query_selector_all('div.col-12.col-sm-6.col-md-6.col-lg-4')

        # Limit to top 50 elements
        top_fifty_tests = test_elements[:50]

        for index, test in enumerate(top_fifty_tests, 1):
            try:
                # Extract test details based on image structure
                test_name_el = await test.query_selector('h3.testName')
                test_name = await test_name_el.text_content() if test_name_el else 'N/A'
                test_name = test_name.strip() if test_name else 'N/A'
                
                # Try parameter selectors
                parameters_element = await test.query_selector('p.parameterText')
                if not parameters_element:
                    parameters_element = await test.query_selector('p.parameters')
                parameters = await parameters_element.text_content() if parameters_element else 'N/A'
                if parameters != 'N/A':
                    parameters = parameters.replace('Parameters: ', '').strip()

                # Try price selectors
                price_element = await test.query_selector('p.testPrice span')
                if not price_element:
                    price_element = await test.query_selector('span.testPrice')
                price_text = await price_element.text_content() if price_element else 'N/A'

                # Clean and format price (remove all currency symbols, keep only numeric value)
                formatted_price = re.sub(r'[^\d.]', '', price_text) if price_text else 'N/A'
                if not formatted_price: # Handle case where regex might return empty string
                    formatted_price = 'N/A'

                # Check for Home Collection and Lab Visit
                home_collection = bool(await test.query_selector('div.homeLabCollectionAvaliable p:has-text("Home Collection")'))
                lab_visit = bool(await test.query_selector('div.homeLabCollectionAvaliable p:has-text("Lab Visit")'))

                # Store data in a dictionary
                test_data = {
                    "test_number": index,
                    "test_name": test_name,
                    "parameters": parameters,
                    "price": formatted_price, # Storing the formatted price
                    "home_collection_available": home_collection,
                    "lab_visit_available": lab_visit
                }
                tests_data.append(test_data)


            except Exception as e:
                print(f"Error processing test {index}: {e}")

        # Step 5: Save data to JSON file
        with open(f'output\{location}_lalpathlabs_tests_data.json', 'w', encoding='utf-8') as f:
            json.dump(tests_data, f, indent=4)
        print(f"Saved scraped data to {location}_lalpathlabs_tests_data.json")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the browser
        await browser.close()
        # End timing and print total time taken in seconds
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        print(f"Total execution time: {total_time:.2f} seconds")

# For direct script run (optional)
if __name__ == "__main__":
    import asyncio
    async def main():
        location = input("Enter the city name (e.g., Delhi): ").strip() or "Mumbai"
        async with async_playwright() as p:
            await run(p, location)
    asyncio.run(main())