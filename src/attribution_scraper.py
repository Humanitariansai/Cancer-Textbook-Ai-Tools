# src/attribution_scraper.py
import os
import re
import time
import argparse
import requests
import pandas as pd
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

IN_CSV = "data/paragraph_image_map.csv"
OUT_CSV = "data/paragraph_image_attributions.csv"
IMG_DIR = "data/nih_images_full"

NIH_BASE = "https://visualsonline.cancer.gov/"


def get_selenium_driver():
    from selenium.webdriver.chrome.service import Service
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def find_fullres_and_meta(html: str):
    """
    Parse NIH detail page:
    - caption: look for descriptive blocks
    - credit/author: look for 'credit', 'source', 'rights'
    - full-res: previewlg <img> or retrieve.cfm link
    """
    soup = BeautifulSoup(html, "html.parser")

    # Caption candidates (site varies)
    caption = ""
    # Try common selectors
    for sel in [
        ("div", {"class": "caption"}),
        ("div", {"id": "caption"}),
        ("div", {"class": "resultsitemdesc"}),
        ("p", {"class": "caption"}),
    ]:
        tag = soup.find(*sel)
        if tag and tag.get_text(strip=True):
            caption = tag.get_text(" ", strip=True)
            break
    if not caption:
        # fallback: first paragraph in detail content area
        paras = soup.find_all("p")
        if paras:
            caption = paras[0].get_text(" ", strip=True)[:500]

    # Credit / rights
    credit = ""
    text = soup.get_text("\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        low = l.lower()
        if any(k in low for k in ["credit", "source", "rights", "creator", "author", "photo by"]):
            credit = l
            break

    # Full-res image
    full_url = None
    # Strategy 1: large preview image
    img_tag = soup.find("img", {"class": "previewlg"})
    if img_tag and img_tag.get("src"):
        u = img_tag["src"]
        full_url = u if u.startswith("http") else (NIH_BASE + u)

    # Strategy 2: retrieve.cfm link
    if not full_url:
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            text = a.get_text(" ", strip=True).lower()
            if "retrieve.cfm" in href or any(k in text for k in ["full", "download", "high", "large"]):
                full_url = href if href.startswith("http") else (NIH_BASE + href.lstrip("/"))
                break

    return caption or "No caption found", credit or "No credit info", full_url


def download_full_image(url: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        # use imageid from URL if present
        m = re.search(r"imageid=(\d+)", url)
        img_id = m.group(1) if m else os.path.basename(url).split("?")[0].split("#")[0]
        fname = f"nih_{img_id}.jpg"
        path = os.path.join(out_dir, fname)
        img.save(path, "JPEG")
        return path, f"{img.width}x{img.height}"
    except Exception as e:
        return "", f"download_error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Scrape NIH attributions + download full-res")
    parser.add_argument("--input", default=IN_CSV, help="Input CSV from paragraph_image_matcher")
    parser.add_argument("--out", default=OUT_CSV, help="Output CSV with attributions")
    parser.add_argument("--download", action="store_true", help="Download full-res images")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between requests (sec)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input CSV not found: {args.input}")
        return

    df = pd.read_csv(args.input)
    df = df.dropna(subset=["detail_url"]).copy()
    df = df[df["detail_url"].astype(str).str.startswith("http")]

    # de-dupe per detail_url to avoid re-scraping the same page
    unique = df.sort_values(["detail_url", "match_score"], ascending=[True, False]).drop_duplicates("detail_url")

    driver = get_selenium_driver()
    rows = []
    for _, r in unique.iterrows():
        detail = r["detail_url"]
        try:
            driver.get(detail)
            time.sleep(args.sleep)
            html = driver.page_source

            caption, credit, full_url = find_fullres_and_meta(html)
            img_path, dims = ("", "")
            if args.download and full_url:
                img_path, dims = download_full_image(full_url, IMG_DIR)

            rows.append({
                "detail_url": detail,
                "thumbnail": r.get("thumbnail", ""),
                "picked_title": r.get("picked_title", ""),
                "caption": caption,
                "credit": credit,
                "fullres_url": full_url or "",
                "download_path": img_path,
                "dimensions": dims
            })
        except Exception as e:
            rows.append({
                "detail_url": detail,
                "thumbnail": r.get("thumbnail", ""),
                "picked_title": r.get("picked_title", ""),
                "caption": "scrape_error",
                "credit": f"{e}",
                "fullres_url": "",
                "download_path": "",
                "dimensions": ""
            })

    driver.quit()
    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    print(f"✅ Saved {len(out)} rows → {args.out}")

    # Join back to paragraph mapping for full traceability (optional)
    joined = df.merge(out, on="detail_url", how="left")
    joined.to_csv("data/paragraph_image_attributions_joined.csv", index=False)
    print("✅ Saved joined map → data/paragraph_image_attributions_joined.csv")


if __name__ == "__main__":
    main()
