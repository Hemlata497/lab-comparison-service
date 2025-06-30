from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from compare_test import run_scrapers_and_compare
import asyncio

router = APIRouter()

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
    try:
        data = await run_scrapers_and_compare(city)
    except Exception as e:
        if "Incorrect API key provided" in str(e) or "OpenAI Embedding API failed" in str(e):
            raise HTTPException(status_code=500, detail="OpenAI API key error: Please check your API key and environment configuration.")
        raise HTTPException(status_code=500, detail=f"Error running comparison: {str(e)}")
    if not data or not data.get("data"):
        raise HTTPException(status_code=404, detail=f"No comparison data found for location: {city}")
    required_tests = {"CBC", "Glucose", "TSH", "Uric Acid", "SGPT"}
    filtered_data = {}
    for lab, tests in data["data"].items():
        filtered_data[lab] = {k: v for k, v in tests.items() if k in required_tests}
    return {"data": filtered_data}

class AnalyzeRequest(BaseModel):
    prices: dict

@router.post("/analyze")
async def analyze_endpoint(payload: AnalyzeRequest):
    prices = payload.prices
    response_lines = []
    required_tests = {"CBC", "Glucose", "TSH", "Uric Acid", "SGPT"}
    test_names = set()
    for lab, tests in prices.items():
        test_names.update(tests.keys())
    test_names = [t for t in test_names if t in required_tests]
    for test_name in test_names:
        all_values = []
        for lab, tests in prices.items():
            if test_name in tests and tests[test_name] is not None:
                all_values.append((lab, tests[test_name]))
        if all_values:
            min_price = min([v for _, v in all_values])
            max_price = max([v for _, v in all_values])
            recommended_lab = next(lab for lab, price in all_values if price == min_price)
            response_lines.append(
                f"{test_name}: market range ₹{min_price}–₹{max_price},  AI Recommended: ₹{min_price} (offered by {recommended_lab})"
            )
    report_text = " | ".join(response_lines)
    return {"report": report_text}