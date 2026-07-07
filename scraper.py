#!/usr/bin/env python3
"""
Image scraper using DDGS (renamed from duckduckgo_search).
With rate limit handling and retry logic.
"""

from ddgs import DDGS
from io import BytesIO
from PIL import Image
import requests
import os
import time
import random

# Config
TARGET_CLASS = "scissor"
OUTPUT_DIR = f"dataset/{TARGET_CLASS}"
NUM_IMAGES = 200

# Search queries per class. Highlighter queries are biased toward stationery
# (pens/markers) and exclude makeup-related terms at the query level.
QUERIES_BY_CLASS = {
    "scissor": [
        "scissors stationery",
        "scissors isolated white background",
        "scissors office supply",
        "scissors product photo",
        "pair of scissors closeup",
    ],
    "eraser": [
        "eraser stationery",
        "eraser isolated white background",
        "eraser office supply",
        "eraser product photo",
        "pencil eraser closeup",
    ],
    "ruler": [
        "ruler stationery",
        "ruler isolated white background",
        "ruler office supply",
        "ruler product photo",
        "measuring ruler closeup",
    ],
    "highlighter": [
        "highlighter pen stationery -makeup -cosmetic",
        "highlighter marker isolated white background -makeup",
        "highlighter pen office supply",
        "fluorescent highlighter pen product photo",
        "yellow highlighter marker closeup -makeup -cosmetic",
    ],
}

SEARCH_QUERIES = QUERIES_BY_CLASS.get(TARGET_CLASS, QUERIES_BY_CLASS["scissor"])

# Terms that indicate a "highlighter" result is a cosmetics product rather
# than a stationery pen/marker. Used to filter search results when scraping
# the "highlighter" class.
MAKEUP_KEYWORDS = [
    "makeup", "make up", "make-up", "cosmetic", "cosmetics", "concealer",
    "contour", "contouring", "blush", "bronzer", "foundation", "eyeshadow",
    "skincare", "beauty", "glow palette", "highlighter palette",
    "highlighter powder", "highlighter stick", "cheek highlighter",
    "face highlighter", "liquid highlighter", "highlighter cream",
    "highlighter kit", "shimmer powder",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

def is_makeup_result(result):
    text = " ".join(str(result.get(field, "")) for field in ("title", "image", "url")).lower()
    return any(keyword in text for keyword in MAKEUP_KEYWORDS)

def download_image(url, filepath):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200 or len(response.content) <= 5000:
            return False

        # Decode and re-encode as a genuine JPEG so the file on disk always
        # matches its .jpg extension, regardless of the source format.
        try:
            img = Image.open(BytesIO(response.content))
            img.load()
        except Exception:
            return False

        if img.mode != "RGB":
            img = img.convert("RGB")

        img.save(filepath, "JPEG", quality=92)
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

            if TARGET_CLASS == "highlighter" and is_makeup_result(result):
                print(f"  ✗ skipped (makeup highlighter, not stationery)")
                continue

            filename = f"{counter:05d}.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if download_image(url, filepath):
                print(f"  ✓ {filename}")
                counter += 1
                downloaded += 1
            else:
                print(f"  ✗ skipped")

            time.sleep(random.uniform(0.3, 0.8))

        print(f"  Done — {downloaded} downloaded for this query.")

    total = len([f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(".jpg")])
    print(f"\n✅ Done! {total} images saved to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    scrape_images()
