from playwright.async_api import async_playwright
import json
from datetime import datetime
import asyncio
import os

async def run(playwright, location):
    start_time = datetime.now()

    # Launch browser
    browser = await playwright.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    context = await browser.new_context()
    page = await context.new_page()

    # Block unnecessary resources (images, CSS, fonts)
    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] else route.continue_())

    tests_data = []

    try:
        await page.goto(f'https://www.lalpathlabs.com/book-a-test/{location}', wait_until='domcontentloaded')
        print(f"Opened page for location: {location}")

        await page.wait_for_selector('div.col-12.col-sm-6.col-md-6.col-lg-4', timeout=10000)

        # Extract all data inside browser context for better performance
        tests_data = await page.eval_on_selector_all(
            'div.col-12.col-sm-6.col-md-6.col-lg-4',
            '''
            nodes => nodes.slice(0, 50).map((node, index) => {
                const getText = (selector) => {
                    const el = node.querySelector(selector);
                    return el ? el.textContent.trim() : 'N/A';
                };

                const priceText = getText('p.testPrice span') || getText('span.testPrice');
                const price = priceText.replace(/[^\d.]/g, '') || 'N/A';

                const parametersRaw = getText('p.parameterText') || getText('p.parameters');
                const parameters = parametersRaw.replace('Parameters: ', '').trim();

                const hasHomeCollection = [...node.querySelectorAll('div.homeLabCollectionAvaliable p')]
                    .some(p => p.textContent.includes("Home Collection"));

                const hasLabVisit = [...node.querySelectorAll('div.homeLabCollectionAvaliable p')]
                    .some(p => p.textContent.includes("Lab Visit"));

                return {
                    test_number: index + 1,
                    test_name: getText('h3.testName'),
                    parameters: parameters || 'N/A',
                    price: price,
                    home_collection_available: hasHomeCollection,
                    lab_visit_available: hasLabVisit
                };
            })
            '''
        )

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        output_file = f'output/{location}_lalpathlabs_tests_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tests_data, f, indent=4)
        print(f"Saved scraped data to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        await browser.close()
        total_time = (datetime.now() - start_time).total_seconds()
        print(f"Total execution time: {total_time:.2f} seconds")


# Entry point
if __name__ == "__main__":
    async def main():
        location = input("Enter the city name (e.g., Delhi): ").strip() or "Mumbai"
        async with async_playwright() as p:
            await run(p, location)

    asyncio.run(main())
