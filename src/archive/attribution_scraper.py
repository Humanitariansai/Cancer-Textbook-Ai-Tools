from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json, csv, time, re

def classify_license(text):
    """Categorize license based on keywords."""
    t = text.lower()
    if any(x in t for x in ["nci", "national cancer institute", "public domain"]):
        return "Public Domain / NCI"
    elif "creative commons" in t or "cc by" in t:
        return "Creative Commons"
    else:
        return "Restricted / Needs Review"

def fetch_metadata(image_id):
    """Fetch image metadata from NIH Visuals Online JSON API via browser."""
    url = f"https://visualsonline.cancer.gov/details.cfm?imageid={image_id}"
    api_url = f"https://visualsonline.cancer.gov/api/json/image?id={image_id}"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2)

    script = f"""
    return fetch('{api_url}')
      .then(r => r.json())
      .then(data => JSON.stringify(data))
      .catch(e => JSON.stringify({{"error": e.toString()}}));
    """

    try:
        data_json = driver.execute_script(script)
        driver.quit()
        meta = json.loads(data_json)
        if "error" in meta:
            print(f"⚠️ API error for {image_id}: {meta['error']}")
            return None
        return meta
    except Exception as e:
        driver.quit()
        print(f"⚠️ Failed for {image_id}: {e}")
        return None

def get_image_url_field(row):
    """Find correct column name for image URL in CSV row."""
    for key in row.keys():
        if any(x in key.lower() for x in ["url", "link", "detail"]):
            return row[key]
    return ""

def main():
    input_file = "data/paragraph_image_map_14__20251027_234226.csv"
    output_file = "data/image_metadata_fixed.csv"

    with open(input_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("❌ No data found in input CSV.")
        return

    all_data = []

    for idx, r in enumerate(rows[:10]):  # test with first 10 entries
        raw_url = get_image_url_field(r)
        match = re.search(r"imageid=(\d+)", raw_url)
        if not match:
            continue

        image_id = match.group(1)
        print(f"[{idx+1}/{len(rows)}] Fetching metadata for Image ID {image_id}...")

        meta = fetch_metadata(image_id)
        if not meta:
            continue

        credit = meta.get("Credit", "")
        license_text = meta.get("License", "")
        src = meta.get("Source", "")
        title = meta.get("Title", "")
        desc = meta.get("Description", "")
        combined = f"{credit} {license_text} {src}"
        license_class = classify_license(combined)

        attribution = f"{title or 'Untitled'} — Source: {src or 'NCI'}, {license_class}. {raw_url}"

        all_data.append({
            "Image ID": image_id,
            "Title": title,
            "Description": desc,
            "Credit": credit,
            "License": license_text,
            "Source": src,
            "License Class": license_class,
            "Attribution": attribution
        })

    if not all_data:
        print("❌ No metadata extracted.")
        return

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
        writer.writeheader()
        writer.writerows(all_data)

    print(f"✅ Done! Saved metadata for {len(all_data)} images to {output_file}")

if __name__ == "__main__":
    main()
