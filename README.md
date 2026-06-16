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
pip install ddgs requests
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

Each class works best with tailored search queries. Find the `SEARCH_QUERIES` list and update it to match your class:

```python
SEARCH_QUERIES = [
    "eraser stationery",
    "eraser isolated white background",
    "eraser office supply",
    "eraser product photo",
    "pencil eraser closeup",
]
```

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

## ⚠️ Common Issues

### Got 0 images — Rate limited
DuckDuckGo may rate-limit rapid requests. The script already adds random delays between queries, but if it still fails:
- Wait 1–2 minutes, then run again
- The script will auto-retry up to 3 times per query

### Got fewer than 200 images
Some search queries return fewer results than expected. Try:
- Adding more varied entries to `SEARCH_QUERIES`
- Lowering the minimum file size filter (change `> 5000` to `> 2000` in the `download_image` function)

### `ModuleNotFoundError: No module named 'ddgs'`
Run:
```bash
pip install ddgs
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
