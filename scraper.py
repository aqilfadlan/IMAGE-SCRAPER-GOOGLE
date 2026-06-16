#!/usr/bin/env python3
"""
Image scraper using DDGS (renamed from duckduckgo_search).
With rate limit handling and retry logic.
"""

from ddgs import DDGS
import requests
import os
import time
import random

# Config
TARGET_CLASS = "scissor"
OUTPUT_DIR = f"dataset/{TARGET_CLASS}"
NUM_IMAGES = 200

SEARCH_QUERIES = [
    "scissors stationery",
    "scissors isolated white background",
    "scissors office supply",
    "scissors product photo",
    "pair of scissors closeup",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

def download_image(url, filepath):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200 and len(response.content) > 5000:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

def search_with_retry(ddgs, query, max_results, retries=3):
    for attempt in range(retries):
        try:
            results = list(ddgs.images(query, max_results=max_results))
            return results
        except Exception as e:
            wait = 10 + (attempt * 10) + random.uniform(2, 5)
            print(f"  Rate limited. Waiting {wait:.0f}s before retry {attempt+1}/{retries}...")
            time.sleep(wait)
    return []

def scrape_images():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    images_per_query = NUM_IMAGES // len(SEARCH_QUERIES)
    remainder = NUM_IMAGES % len(SEARCH_QUERIES)
    counter = 1

    ddgs = DDGS()

    for i, query in enumerate(SEARCH_QUERIES):
        count = images_per_query + (remainder if i == 0 else 0)
        print(f"\n[{i+1}/{len(SEARCH_QUERIES)}] Query: '{query}' — targeting {count} images")

        # Wait between queries to avoid rate limit
        if i > 0:
            wait = random.uniform(8, 15)
            print(f"  Waiting {wait:.0f}s before next query...")
            time.sleep(wait)

        results = search_with_retry(ddgs, query, max_results=count * 2)

        if not results:
            print(f"  No results returned, skipping.")
            continue

        downloaded = 0
        for result in results:
            if downloaded >= count:
                break

            url = result.get("image")
            if not url:
                continue

            ext = url.split(".")[-1].split("?")[0].lower()
            if ext not in ("jpg", "jpeg", "png", "webp"):
                ext = "jpg"

            filename = f"{counter:05d}.{ext}"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if download_image(url, filepath):
                print(f"  ✓ {filename}")
                counter += 1
                downloaded += 1
            else:
                print(f"  ✗ skipped")

            time.sleep(random.uniform(0.3, 0.8))

        print(f"  Done — {downloaded} downloaded for this query.")

    total = len([f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
    print(f"\n✅ Done! {total} images saved to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    scrape_images()