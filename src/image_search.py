import os, pandas as pd
from nih_scraper import search_nih_images

QUERY_FILE = "data/query_text.txt"
RESULTS_FILE = "data/nih_results.csv"

with open(QUERY_FILE, "r", encoding="utf-8") as f:
    query_text = f.read().strip()

print(f"🔎 Using query: {query_text[:50]}...")
images = search_nih_images(query_text, limit=10)

pd.DataFrame(images).to_csv(RESULTS_FILE, index=False)
print(f"✅ Saved {len(images)} results → {RESULTS_FILE}")
