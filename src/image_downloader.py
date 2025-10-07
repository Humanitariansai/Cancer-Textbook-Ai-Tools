# src/image_downloader.py
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from io import BytesIO
import time


def download_image(url, filepath):
    """Helper to download an image from URL and save it."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        img.save(filepath, "JPEG")
        return f"{img.width}x{img.height}"
    except Exception as e:
        print(f"   ❌ Failed to download {url}: {e}")
        return None


def get_full_res_url(detail_url):
    """Visit NIH detail page and extract the full-res image link."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(detail_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Strategy 1: look for <img class="previewlg">
        img_tag = soup.find("img", class_="previewlg")
        if img_tag and img_tag.get("src"):
            return "https://visualsonline.cancer.gov/" + img_tag["src"].lstrip("/")

        # Strategy 2: look for retrieve.cfm link
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if "retrieve.cfm" in href:
                return "https://visualsonline.cancer.gov/" + href.lstrip("/")

        return None
    finally:
        driver.quit()


def download_nih_images(csv_path="data/nih_results.csv", save_dir="data/nih_images"):
    """
    Download thumbnails AND attempt full-resolution images.
    """
    os.makedirs(save_dir, exist_ok=True)

    df = pd.read_csv(csv_path)
    downloaded = []

    for i, row in df.iterrows():
        print(f"\n⬇️ {i+1}: {row['thumbnail']}")

        # Thumbnail
        thumb_name = f"nih_thumb_{i+1}.jpg"
        thumb_path = os.path.join(save_dir, thumb_name)
        thumb_size = download_image(row["thumbnail"], thumb_path)

        # Full resolution
        full_res_url = get_full_res_url(row["url"])
        full_name, full_size = None, None
        if full_res_url:
            print(f"   🔍 Found full-res: {full_res_url}")
            full_name = f"nih_full_{i+1}.jpg"
            full_path = os.path.join(save_dir, full_name)
            full_size = download_image(full_res_url, full_path)
        else:
            print("   ⚠️ No full-res found")

        downloaded.append({
            "index": i+1,
            "title": row.get("title", ""),
            "source_url": row["url"],
            "thumb_file": thumb_name,
            "thumb_size": thumb_size,
            "full_file": full_name,
            "full_size": full_size,
        })

    # Save manifest
    manifest = os.path.join(save_dir, "manifest_full.csv")
    pd.DataFrame(downloaded).to_csv(manifest, index=False)
    print(f"\n💾 Manifest saved: {manifest}")


if __name__ == "__main__":
    download_nih_images()
