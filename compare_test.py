from playwright.async_api import async_playwright
import asyncio
import time
from metropolisindia import main as metropolis_main_async
from lalpathlabs import run as lalpathlabs_run_async
from srl import scrape_srl_diagnostics

# Hardcoded test name mappings to standardized names
TEST_NAME_MAPPINGS = {
    "Lal PathLabs": {
        "COMPLETE BLOOD COUNT; CBC": "CBC",
        "GLUCOSE, FASTING (F) AND POST MEAL (PP), 2 HOURS": "Glucose",
        "TSH (THYROID STIMULATING HORMONE), ULTRASENSITIVE": "TSH",
        "URIC ACID, SERUM": "Uric Acid",
        "SGPT; ALANINE AMINOTRANSFERASE (ALT)": "SGPT"
    },
    "Metropolis Labs": {
        "CBC Test (Complete Blood Count)": "CBC",
        "Fasting Blood Sugar (FBS) Test": "Glucose",
        "TSH (Ultrasensitive)/ TSH-U Test": "TSH",
        "Uric Acid Test, Serum": "Uric Acid",
        "SGPT Test / Alanine Aminotransferase (ALT)": "SGPT"
    },
    "SRL Diagnostics": {
        "HEMOGLOBIN": "CBC",
        "FASTING BLOOD SUGAR(GLUCOSE)": "Glucose",
        "THYROID STIMULATING HORMONE (TSH)": "TSH",
        "URIC ACID": "Uric Acid",
        "ALANINE TRANSAMINASE (SGPT)": "SGPT"
    }
}

async def run_scrapers_and_compare(location: str):
    location = location.strip() or "Mumbai"
    print(f"\n🔄 Scraping labs for location: {location}")
    start_time = time.time()
    async with async_playwright() as p:
        print("Running all scrapers concurrently...")
        lal_task = lalpathlabs_run_async(p, location)
        metro_task = metropolis_main_async(p, location)
        srl_task = scrape_srl_diagnostics(p, "https://srldiagnostics.in/shop/?orderby=price")
        lal_tests, metro_tests, srl_tests = await asyncio.gather(lal_task, metro_task, srl_task)
        # Process data in memory
        lal_tests = [(t["test_name"].strip(), t["price"].strip()) for t in lal_tests]
        metro_tests = [(t["name"].strip(), t["price"].replace("Rs.", "").strip()) for t in metro_tests if t["name"] != "N/A"]
        srl_tests = [(t["test"].strip(), t["price"].replace("₹", "").strip()) for t in srl_tests]
        print(f"\n📦 Loaded: {len(lal_tests)} LalPathLabs | {len(metro_tests)} Metropolis | {len(srl_tests)} SRL")
        if not (lal_tests and metro_tests and srl_tests):
            print("❌ Not enough data from all sources to perform comparison.")
            return {}
        # Initialize dictionaries for each lab
        lal_dict, metro_dict, srl_dict = {}, {}, {}
        required_tests = {"CBC", "Glucose", "TSH", "Uric Acid", "SGPT"}
        # Process Lal PathLabs tests
        for test_name, price in lal_tests:
            standardized_name = TEST_NAME_MAPPINGS["Lal PathLabs"].get(test_name)
            if standardized_name in required_tests:
                try:
                    price_num = int(float(price)) if price and price != "N/A" else None
                    if price_num is not None:
                        lal_dict[standardized_name] = price_num
                except ValueError:
                    print(f"⚠️ Invalid price for {test_name} in Lal PathLabs: {price}")
        # Process Metropolis Labs tests
        for test_name, price in metro_tests:
            standardized_name = TEST_NAME_MAPPINGS["Metropolis Labs"].get(test_name)
            if standardized_name in required_tests:
                try:
                    price_num = int(float(price)) if price and price != "N/A" else None
                    if price_num is not None:
                        metro_dict[standardized_name] = price_num
                except ValueError:
                    print(f"⚠️ Invalid price for {test_name} in Metropolis Labs: {price}")
        # Process SRL Diagnostics tests
        for test_name, price in srl_tests:
            standardized_name = TEST_NAME_MAPPINGS["SRL Diagnostics"].get(test_name)
            if standardized_name in required_tests:
                try:
                    price_num = int(float(price)) if price and price != "N/A" else None
                    if price_num is not None:
                        srl_dict[standardized_name] = price_num
                except ValueError:
                    print(f"⚠️ Invalid price for {test_name} in SRL Diagnostics: {price}")
        if not lal_dict and not metro_dict and not srl_dict:
            print("⚠️ None of the required tests found in all three labs. Final output is empty.")
            return {}
        # Compute recommended prices
        recommended_dict = {}
        all_test_names = set(list(lal_dict.keys()) + list(metro_dict.keys()) + list(srl_dict.keys()))
        for test in all_test_names:
            prices = [d[test] for d in [lal_dict, metro_dict, srl_dict] if test in d and d[test] is not None]
            if prices:
                recommended_dict[test] = min(prices)
        final_output = {
            "data": {
                "Lal PathLabs": lal_dict,
                "SRL Diagnostics": srl_dict,
                "Metropolis Labs": metro_dict,
                "Recommended": recommended_dict
            }
        }
        print(f"\n✅ Comparison completed for {location}")
        print(f"Common tests found: {all_test_names}")
        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
        return final_output

if __name__ == "__main__":
    location = input("Enter location (default is Mumbai): ").strip() or "Mumbai"
    result = asyncio.run(run_scrapers_and_compare(location))
    print("Result:", result)