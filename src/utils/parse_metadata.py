# src/parse_metadata.py
import os, re, csv
from bs4 import BeautifulSoup

CACHE_DIR = "cache/html"
OUT_FILE = "data/image_metadata_fixed.csv"

def classify_license(text):
    t = text.lower()
    if any(x in t for x in ["nci", "national cancer institute", "public domain"]):
        return "Public Domain / NCI"
    elif "creative commons" in t or "cc by" in t:
        return "Creative Commons"
    else:
        return "Restricted / Needs Review"

def parse_html(image_id):
    path = os.path.join(CACHE_DIR, f"{image_id}.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    data = {"image_id": image_id, "title": "", "description": "", "source": "", "license": ""}
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text.startswith("Title:"):
            data["title"] = text.replace("Title:", "").strip()
        elif text.startswith("Description:"):
            data["description"] = text.replace("Description:", "").strip()
        elif text.startswith("Source:"):
            data["source"] = text.replace("Source:", "").strip()
        elif text.startswith("Reuse Restrictions:"):
            data["license"] = text.replace("Reuse Restrictions:", "").strip()

    combo = " ".join(data.values()).lower()
    data["license_class"] = classify_license(combo)
    data["attribution"] = f"{data['title']} — Source: {data['source'] or 'NCI'}, {data['license_class']}."
    return data

def main():
    image_ids = [re.sub(r"\.html$", "", f) for f in os.listdir(CACHE_DIR) if f.endswith(".html")]
    print(f"Parsing {len(image_ids)} cached files...")

    all_data = []
    for image_id in image_ids:
        d = parse_html(image_id)
        if d:
            all_data.append(d)

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
        writer.writeheader()
        writer.writerows(all_data)

    print(f"✅ Parsed {len(all_data)} → {OUT_FILE}")

if __name__ == "__main__":
    main()
