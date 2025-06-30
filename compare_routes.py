from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from compare_test import run_scrapers_and_compare
import asyncio
import os
import json
import aiofiles

router = APIRouter()

# Define input model
class LocationInput(BaseModel):
    location: str
    competitors: list[str]

@router.post("/scrape")
async def compare_tests(location: LocationInput):
    """
    Endpoint to compare lab tests for a given location and competitors, returning the common tests with prices and parameters.

    Args:
        location (LocationInput): The city name and list of competitors.
    
    Returns:
        dict: JSON data containing common tests with prices and parameters.
    
    Raises:
        HTTPException: If the location is invalid or no data is found.
    """
    city = location.location.strip()
    competitors = location.competitors
    if not city:
        raise HTTPException(status_code=400, detail="Location name cannot be empty")
    if not competitors or not isinstance(competitors, list):
        raise HTTPException(status_code=400, detail="Competitors list cannot be empty")

    # Run the comparison pipeline (pass competitors if run_scrapers_and_compare supports it)
    try:
        await run_scrapers_and_compare(city, competitors)
    except TypeError:
        # Fallback for backward compatibility if function does not accept competitors
        await run_scrapers_and_compare(city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running comparison: {str(e)}")

    # Load the output file asynchronously
    out_path = f"output/common_tests_with_prices_{city}.json"
    if not os.path.exists(out_path):
        raise HTTPException(status_code=404, detail=f"No comparison data found for location: {city}")

    try:
        async with aiofiles.open(out_path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
        if not data:
            raise HTTPException(status_code=404, detail=f"No common tests found for location: {city}")
        required_tests = {"CBC", "Glucose", "TSH", "Uric Acid", "SGPT"}
        filtered_data = {lab: {k: v for k, v in tests.items() if k in required_tests}
                         for lab, tests in data["data"].items()}
        return {"data": filtered_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading output file: {str(e)}")
    
class AnalyzeRequest(BaseModel):
    prices: dict

@router.post("/analyze")
async def analyze_endpoint(payload: AnalyzeRequest):
    prices = payload.prices
    response_lines = []

    # Compute recommended prices dynamically
    # Only include these tests in the report
    required_tests = {"CBC", "Glucose", "TSH", "Uric Acid", "SGPT"}
    test_names = set()
    for lab, tests in prices.items():
        test_names.update(tests.keys())
    test_names = [t for t in test_names if t in required_tests]

    for test_name in test_names:
        all_values = [(lab, tests[test_name]) for lab, tests in prices.items() if test_name in tests and tests[test_name] is not None]
        if all_values:
            min_lab, min_price = min(all_values, key=lambda x: x[1])
            max_price = max(v for _, v in all_values)
            response_lines.append(
                f"{test_name}: market range ₹{min_price}–₹{max_price},  AI Recommended: ₹{min_price} (offered by {min_lab})"
            )

    report_text = " | ".join(response_lines)
    return {"report": report_text}
s
