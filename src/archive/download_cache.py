# ================================================================
# NIH Visuals Online Downloader (Cache HTML Once per Image)
# Uses undetected-chromedriver to bypass bot protection.
# ================================================================
# --- Python 3.12 distutils fix ---
import setuptools
setuptools._distutils_hack.add_shim()
# ---------------------------------


import undetected_chromedriver as uc
uc.install()

import os
import re
import csv
import time
import setuptools  # Fix for Python 3.12 distutils removal
setuptools._distutils_hack.add_shim()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------
CACHE_DIR = "cache/html"
os.makedirs(CACHE_DIR, exist_ok=True)

INPUT_CSV = "data/paragraph_image_map_14__20251027_234226.csv"

# ----------------------------------------------------------------
# FETCH + CACHE FUNCTION
# ----------------------------------------------------------------
def fetch_and_cache(image_id: str, url: str):
    """Renders NIH image detail page and saves its full HTML once."""
    cache_path = os.path.join(CACHE_DIR, f"{image_id}.html")

    # Skip if already downloaded
    if os.path.exists(cache_path):
        print(f"✅ Cached already: {image_id}")
        return True

    # Set up Chrome (stealth mode)
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Launch driver (use_subprocess avoids hangs on macOS)
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        driver.get(url)
        # Wait until metadata text like "Title:" or "Description:" appears
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//p[contains(., 'Title:') or contains(., 'Description:')]")
            )
        )

        html = driver.page_source
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"💾 Saved {image_id}.html")

        return True

    except Exception as e:
        print(f"⚠️ Failed {image_id}: {e}")
        return False

    finally:
        driver.quit()
        time.sleep(0.5)  # avoid overloading server


# ----------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------
def main():
    if not os.path.exists(INPUT_CSV):
        print(f"❌ Input CSV not found: {INPUT_CSV}")
        return

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"🔍 Loaded {len(rows)} image rows.")

    success, fail = 0, 0

    for r in rows:
        url = r.get("detail_url") or r.get("Image URL")
        if not url:
            continue

        match = re.search(r"imageid=(\d+)", url)
        if not match:
            continue

        image_id = match.group(1)
        print(f"[{success + fail + 1}/{len(rows)}] Fetching {image_id}...")
        ok = fetch_and_cache(image_id, url)
        if ok:
            success += 1
        else:
            fail += 1

    print(f"\n✅ Done. Cached: {success}, Failed: {fail}")
    print(f"HTML saved in → {CACHE_DIR}/")


# ----------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------
if __name__ == "__main__":
    main()
