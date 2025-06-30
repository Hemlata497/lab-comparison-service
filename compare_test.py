import openai
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
import asyncio
import time
from playwright.async_api import async_playwright

from metropolisindia import main as metropolis_main_async
from lalpathlabs import run as lalpathlabs_run_async
from srl import scrape_srl_diagnostics

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def match_tests(source_names, source_embeds, target_names, target_embeds, threshold=0.85):
    matches = {}
    used_targets = set()
    for i, (source_name, embed) in enumerate(zip(source_names, source_embeds)):
        sims = cosine_similarity([embed], target_embeds)[0]
        sorted_indices = np.argsort(sims)[::-1]
        for idx in sorted_indices:
            if sims[idx] >= threshold and target_names[idx] not in used_targets:
                print(f"Match: {source_name} -> {target_names[idx]} (Similarity: {sims[idx]:.3f})")
                matches[source_name] = target_names[idx]
                used_targets.add(target_names[idx])
                break
    return matches

def normalize_test_name(name):
    import re
    if ';' in name:
        parts = [p.strip() for p in name.split(';')]
        if len(parts[-1]) <= 6 and parts[-1].isupper():
            return parts[-1]
        return parts[0].title()
    if ',' in name:
        return name.split(',')[0].strip().title()
    name = re.sub(r"\(.*?\)", "", name)
    return name.strip().title()

def get_embeddings(texts):
    if not texts:
        return []
    try:
        response = openai.Embedding.create(input=texts, model="text-embedding-ada-002")
        return [d["embedding"] for d in response["data"]]
    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        raise RuntimeError(f"OpenAI Embedding API failed: {e}")

async def run_scrapers_and_compare(location: str):
    location = location.strip() or "Mumbai"
    print(f"\n🔄 Scraping labs for location: {location}")
    start_time = time.time()
    async with async_playwright() as p:
        print("Running all scrapers concurrently...")
        await asyncio.gather(
            metropolis_main_async(p, location),
            lalpathlabs_run_async(p, location),
            scrape_srl_diagnostics(p, "https://srldiagnostics.in/shop/?orderby=price", output_filename="output/srl_test.json")
        )
        lal_file = f"output/{location}_lalpathlabs_tests_data.json"
        metro_file = f"output/metropolis_tests_all_sections_{location}.json"
        srl_file = "output/srl_test.json"
        import aiofiles
        lal_tests, metro_tests, srl_tests = [], [], []
        if os.path.exists(lal_file):
            async with aiofiles.open(lal_file, mode='r', encoding='utf-8') as f:
                lal_data = await f.read()
                lal_tests = [(t["test_name"].strip(), t["price"].strip()) for t in json.loads(lal_data)]
        else:
            print(f"⚠️ Lalpathlabs file not found at {lal_file}")
        if os.path.exists(metro_file):
            async with aiofiles.open(metro_file, mode='r', encoding='utf-8') as f:
                metro_data = await f.read()
                metro_tests = [(t["name"].strip(), t["price"].replace("Rs.", "").strip()) for t in json.loads(metro_data) if t["name"] != "N/A"]
        else:
            print(f"⚠️ Metropolis file not found at {metro_file}")
        if os.path.exists(srl_file):
            async with aiofiles.open(srl_file, mode='r', encoding='utf-8') as f:
                srl_data = await f.read()
                srl_tests = [(t["test"].strip(), t["price"].replace("₹", "").strip()) for t in json.loads(srl_data)]
        else:
            print(f"⚠️ SRL file not found at {srl_file}")

        # Build dictionaries for fast lookup
        lal_price_dict = {n: p for n, p in lal_tests}
        metro_price_dict = {n: p for n, p in metro_tests}
        srl_price_dict = {n: p for n, p in srl_tests}
        print(f"\n📦 Loaded: {len(lal_tests)} LalPathLabs | {len(metro_tests)} Metropolis | {len(srl_tests)} SRL")
        if not (lal_tests and metro_tests and srl_tests):
            print("❌ Not enough data from all sources to perform comparison.")
            return
        lal_names = [name for name, _ in lal_tests]
        metro_names = [name for name, _ in metro_tests]
        srl_names = [name for name, _ in srl_tests]
        # Batch all embedding requests together for efficiency
        all_texts = lal_names + metro_names + srl_names
        all_embeds = get_embeddings(all_texts)
        lal_embeds = all_embeds[:len(lal_names)]
        metro_embeds = all_embeds[len(lal_names):len(lal_names)+len(metro_names)]
        srl_embeds = all_embeds[len(lal_names)+len(metro_names):]
        if not (lal_embeds and metro_embeds and srl_embeds):
            print("❌ Failed to generate embeddings.")
            raise RuntimeError("Failed to generate embeddings from OpenAI API. Please check your API key or network connectivity.")
        matches_lal_metro = match_tests(lal_names, lal_embeds, metro_names, metro_embeds, threshold=0.85)
        matches_lal_srl = match_tests(lal_names, lal_embeds, srl_names, srl_embeds, threshold=0.85)
        common_tests = set(matches_lal_metro.keys()) & set(matches_lal_srl.keys())
        print(f"\n✅ Common matches in all 3 labs: {len(common_tests)}")
        print("Common tests:", common_tests)
        required_tests = [
            ("CBC", "CBC"),
            ("Glucose", "Glucose"),
            ("TSH", "TSH"),
            ("Uric Acid", "Uric Acid"),
            ("SGPT", "SGPT")
        ]
        required_names = [desc for _, desc in required_tests]
        # Only embed required_names and common_names together for efficiency
        embed_texts = required_names + list(common_tests)
        embed_vectors = get_embeddings(embed_texts)
        required_embeds = embed_vectors[:len(required_names)]
        common_names = list(common_tests)
        common_embeds = embed_vectors[len(required_names):]
        from sklearn.metrics.pairwise import cosine_similarity
        matched_tests = []
        for i, (short_name, _) in enumerate(required_tests):
            if not required_embeds or not common_embeds:
                continue
            sims = cosine_similarity([required_embeds[i]], common_embeds)[0]
            best_idx = int(np.argmax(sims))
            print(f"Matching '{short_name}' to '{common_names[best_idx]}' (Similarity: {sims[best_idx]:.3f})")
            if sims[best_idx] > 0.70:
                matched_tests.append((short_name, common_names[best_idx]))
        lal_dict, metro_dict, srl_dict = {}, {}, {}
        for short_name, matched_name in matched_tests:
            metro_name = matches_lal_metro.get(matched_name)
            srl_name = matches_lal_srl.get(matched_name)
            lal_name = matched_name
            lal_price = lal_price_dict.get(lal_name)
            metro_price = metro_price_dict.get(metro_name)
            srl_price = srl_price_dict.get(srl_name)
            try:
                lal_price_num = int(float(lal_price)) if lal_price else None
            except:
                lal_price_num = None
            try:
                metro_price_num = int(float(metro_price)) if metro_price else None
            except:
                metro_price_num = None
            try:
                srl_price_num = int(float(srl_price)) if srl_price else None
            except:
                srl_price_num = None
            if lal_price_num is not None:
                lal_dict[short_name] = lal_price_num
            if metro_price_num is not None:
                metro_dict[short_name] = metro_price_num
            if srl_price_num is not None:
                srl_dict[short_name] = srl_price_num
        if not lal_dict and not metro_dict and not srl_dict:
            print("⚠️ None of the required tests found in all three labs. Final output is empty.")
            return
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
        out_path = f"output/common_tests_with_prices_{location}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Output saved to: {out_path}")
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    location = input("Enter location (default is Mumbai): ").strip() or "Mumbai"
    asyncio.run(run_scrapers_and_compare(location))
