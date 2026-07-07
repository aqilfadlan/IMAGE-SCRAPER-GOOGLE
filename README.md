# 🖼️ Stationery Image Scraper

A Python script to scrape images from DuckDuckGo for building a MATLAB image classification dataset.

**Target classes:** scissor · eraser · ruler · highlighter

---

## 📋 Requirements

- Python 3.8 or above
- Internet connection

---

## ⚙️ Installation

Install the required packages:

```bash
pip install ddgs requests pillow
```

---

## 🚀 How to Scrape a Class

### Step 1 — Open `scraper.py`

Find this line near the top of the file:

```python
TARGET_CLASS = "scissor"
```

### Step 2 — Change the class name

Replace `"scissor"` with whichever class you want to scrape:

| Class | Value to use |
|-------|-------------|
| Scissors | `"scissor"` |
| Eraser | `"eraser"` |
| Ruler | `"ruler"` |
| Highlighter | `"highlighter"` |

Example — to scrape erasers:

```python
TARGET_CLASS = "eraser"
```

### Step 3 — (Optional) Update search queries

Each class already has tailored search queries baked into the `QUERIES_BY_CLASS` dictionary and is picked automatically based on `TARGET_CLASS`. Edit the relevant list in `QUERIES_BY_CLASS` if you want to tweak the search terms for a class.

### Step 4 — Run the script

```bash
python scraper.py
```

---

## 📁 Output Folder Structure

Images are saved automatically in a `dataset/` folder, organised by class:

```
dataset/
├── scissor/
│   ├── 00001.jpg
│   ├── 00002.jpg
│   └── ...
├── eraser/
├── ruler/
└── highlighter/
```

Run the script once per class and it will create the correct subfolder automatically.

---

## 🔢 Changing the Number of Images

The default target is **200 images per class**. To change it, edit this line:

```python
NUM_IMAGES = 200
```

For MATLAB training, 150–200 images per class is a good starting point.

---

## 🧪 Image Format Guarantee

Every downloaded file is decoded with Pillow and re-encoded as a genuine JPEG before being saved with a `.jpg` extension — so a file never has a `.jpg` name while actually being a PNG/WebP/corrupted download underneath. Files that fail to decode as a valid image are discarded instead of being saved.

## 🖊️ Highlighter Guard (stationery only)

When `TARGET_CLASS = "highlighter"`, the script does two things to keep the dataset to highlighter **pens/markers** and out of cosmetics:
- The built-in search queries for this class are stationery-worded (e.g. `"highlighter pen stationery -makeup -cosmetic"`).
- Each search result's title/URL is checked against a list of makeup-related keywords (`makeup`, `cosmetic`, `concealer`, `contour`, `blush`, `foundation`, `highlighter palette`, `face highlighter`, etc.) and skipped if matched, before it's ever downloaded.

---

## ⚠️ Common Issues

### Got 0 images — Rate limited
DuckDuckGo may rate-limit rapid requests. The script already adds random delays between queries, but if it still fails:
- Wait 1–2 minutes, then run again
- The script will auto-retry up to 3 times per query

### Got fewer than 200 images
Some search queries return fewer results than expected. Try:
- Adding more varied entries to `QUERIES_BY_CLASS` for your class
- Lowering the minimum file size filter (change `> 5000` to `> 2000` in the `download_image` function)

### `ModuleNotFoundError: No module named 'ddgs'` / `'PIL'`
Run:
```bash
pip install ddgs pillow
```
> ⚠️ Do **not** install `duckduckgo-search` — that package has been renamed to `ddgs`.

---

## 🔄 Full Workflow (All 4 Classes)

```bash
# 1. Scrape scissors
#    Set TARGET_CLASS = "scissor" in scraper.py
python scraper.py

# 2. Scrape erasers
#    Set TARGET_CLASS = "eraser" in scraper.py
python scraper.py

# 3. Scrape rulers
#    Set TARGET_CLASS = "ruler" in scraper.py
python scraper.py

# 4. Scrape highlighters
#    Set TARGET_CLASS = "highlighter" in scraper.py
python scraper.py
```

---

## 🎓 Loading the Dataset in MATLAB

Once all classes are scraped, load the dataset using `imageDatastore` — it automatically labels images by subfolder name:

```matlab
imds = imageDatastore('dataset', ...
    'IncludeSubfolders', true, ...
    'LabelSource', 'foldernames');

% Check class distribution
countEachLabel(imds)
```
