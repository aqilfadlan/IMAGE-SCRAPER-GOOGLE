#!/usr/bin/env python3
"""
Image scraper using DDGS (renamed from duckduckgo_search).
With rate limit handling and retry logic.
"""

from ddgs import DDGS
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse, unquote
from collections import deque
import requests
import os
import re
import time
import random

# Config
TARGET_CLASS = "scissor"
OUTPUT_DIR = f"dataset/{TARGET_CLASS}"
NUM_IMAGES = 200

# Search queries per class, biased toward a single item on a white/plain
# background. Highlighter queries additionally exclude makeup-related terms.
QUERIES_BY_CLASS = {
    "scissor": [
        "single scissors isolated on white background",
        "one pair of scissors white background",
        "scissors product photo white background",
        "scissors stationery single item white background",
        "pair of scissors closeup white background",
    ],
    "eraser": [
        "single eraser isolated on white background",
        "one eraser white background",
        "eraser product photo white background",
        "eraser stationery single item white background",
        "pencil eraser closeup white background",
    ],
    "ruler": [
        "single ruler isolated on white background",
        "one ruler white background",
        "ruler product photo white background",
        "ruler stationery single item white background",
        "measuring ruler closeup white background",
    ],
    "highlighter": [
        "single highlighter pen isolated on white background -makeup -cosmetic",
        "one highlighter marker white background -makeup",
        "highlighter pen product photo white background",
        "highlighter pen stationery single item white background -makeup -cosmetic",
        "fluorescent highlighter marker closeup white background -makeup -cosmetic",
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

# Heuristic thresholds for the "single item on white background" guard.
WHITE_PIXEL_THRESHOLD = 235
WHITE_BORDER_FRACTION = 0.06
WHITE_BORDER_MIN_RATIO = 0.85
OBJECT_GRID_SIZE = 64
OBJECT_MIN_AREA = 4
OBJECT_DILATE = 1

def is_makeup_result(result):
    text = " ".join(str(result.get(field, "")) for field in ("title", "image", "url")).lower()
    return any(keyword in text for keyword in MAKEUP_KEYWORDS)

def has_white_background(img):
    """Heuristic: most of the border pixels are near-white."""
    w, h = img.size
    bw = max(1, int(w * WHITE_BORDER_FRACTION))
    bh = max(1, int(h * WHITE_BORDER_FRACTION))
    pixels = img.load()

    samples = []
    for y in list(range(0, bh)) + list(range(h - bh, h)):
        for x in range(0, w, max(1, w // 50)):
            samples.append(pixels[x, y])
    for x in list(range(0, bw)) + list(range(w - bw, w)):
        for y in range(0, h, max(1, h // 50)):
            samples.append(pixels[x, y])

    if not samples:
        return False

    white_count = sum(1 for p in samples if all(c >= WHITE_PIXEL_THRESHOLD for c in p[:3]))
    return (white_count / len(samples)) >= WHITE_BORDER_MIN_RATIO

def count_foreground_objects(img):
    """Heuristic: downscale, threshold against white, and count connected
    non-white blobs (4-connectivity, with a small dilation to bridge gaps
    within a single object)."""
    size = OBJECT_GRID_SIZE
    gray = img.convert("L").resize((size, size))
    pixels = gray.load()
    mask = [[pixels[x, y] < WHITE_PIXEL_THRESHOLD for x in range(size)] for y in range(size)]

    if OBJECT_DILATE:
        dilated = [[False] * size for _ in range(size)]
        for y in range(size):
            for x in range(size):
                if mask[y][x]:
                    for dy in range(-OBJECT_DILATE, OBJECT_DILATE + 1):
                        for dx in range(-OBJECT_DILATE, OBJECT_DILATE + 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < size and 0 <= nx < size:
                                dilated[ny][nx] = True
        mask = dilated

    visited = [[False] * size for _ in range(size)]
    components = 0
    for y in range(size):
        for x in range(size):
            if mask[y][x] and not visited[y][x]:
                area = 0
                queue = deque([(y, x)])
                visited[y][x] = True
                while queue:
                    cy, cx = queue.popleft()
                    area += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < size and 0 <= nx < size and mask[ny][nx] and not visited[ny][nx]:
                            visited[ny][nx] = True
                            queue.append((ny, nx))
                if area >= OBJECT_MIN_AREA:
                    components += 1
    return components

def is_single_item_on_white(img):
    return has_white_background(img) and count_foreground_objects(img) == 1

def filename_from_url(url, used_names):
    """Keep the original filename from the URL (forced to .jpg, since the
    downloaded content is always re-encoded as JPEG). Falls back to a random
    name if the URL has none, and de-dupes against files already claimed in
    this run."""
    path = urlparse(url).path
    stem = os.path.splitext(os.path.basename(unquote(path)))[0]
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:80]
    if not stem:
        stem = f"image_{random.randint(100000, 999999)}"

    name = f"{stem}.jpg"
    suffix = 1
    while name in used_names or os.path.exists(os.path.join(OUTPUT_DIR, name)):
        name = f"{stem}_{suffix}.jpg"
        suffix += 1

    used_names.add(name)
    return name

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

        if not is_single_item_on_white(img):
            return False

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
    used_names = set(os.listdir(OUTPUT_DIR))

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

            filename = filename_from_url(url, used_names)
            filepath = os.path.join(OUTPUT_DIR, filename)

            if download_image(url, filepath):
                print(f"  ✓ {filename}")
                downloaded += 1
            else:
                used_names.discard(filename)
                print(f"  ✗ skipped")

            time.sleep(random.uniform(0.3, 0.8))

        print(f"  Done — {downloaded} downloaded for this query.")

    total = len([f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(".jpg")])
    print(f"\n✅ Done! {total} images saved to '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    scrape_images()
