"""
Scrape Full Metadata for NIH Images
====================================
Takes the list of image IDs from comprehensive scraping and 
retrieves full metadata (title, description, license, credit).

This creates the complete dataset for embedding generation.

Usage:
    python scrape_full_metadata.py --input data/nih_all_images_raw.csv
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
from tqdm import tqdm

def fetch_metadata(image_id, retry_count=3):
    """Fetch HTML for an image detail page"""
    url = f"https://visualsonline.cancer.gov/details.cfm?imageid={image_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                html = response.text
                if len(html) > 1000:
                    return html
            
            if attempt < retry_count - 1:
                time.sleep(random.uniform(3, 5))
                
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(random.uniform(3, 5))
    
    return None

def parse_metadata(html, image_id):
    """Parse metadata from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    
    metadata = {
        "image_id": image_id,
        "Title": "",
        "Description": "",
        "Credit": "",
        "License": ""
    }
    
    try:
        # Get title from h2
        h2 = soup.find('h2')
        if h2:
            metadata["Title"] = h2.get_text(strip=True)
        
        # Get info from table
        table = soup.find('table', class_='image-information-text')
        if table:
            for row in table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                
                if not th or not td:
                    continue
                
                field = th.get_text(strip=True).lower().rstrip(':')
                value = td.get_text(strip=True)
                
                if 'title' in field:
                    metadata["Title"] = value
                elif 'description' in field:
                    metadata["Description"] = value
                elif 'credit' in field or 'source' in field or 'creator' in field:
                    metadata["Credit"] = value
                elif 'license' in field or 'rights' in field or 'usage' in field:
                    metadata["License"] = value
                elif 'reuse' in field or 'attribution' in field:
                    if not metadata["License"]:
                        metadata["License"] = value
        
    except Exception as e:
        print(f"  ⚠️  Parse error for {image_id}: {e}")
    
    return metadata

def scrape_full_metadata(input_csv, output_csv, use_cache=True):
    """
    Scrape full metadata for all images
    """
    
    # Load image IDs
    df = pd.read_csv(input_csv)
    unique_ids = df['image_id'].dropna().unique()
    
    print("\n" + "=" * 70)
    print("📥 SCRAPING FULL METADATA")
    print("=" * 70)
    print(f"Unique images to scrape: {len(unique_ids)}")
    print(f"Estimated time: {len(unique_ids) * 3 / 60:.0f} minutes")
    print("=" * 70 + "\n")
    
    # Setup cache
    cache_dir = "data/html_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    all_metadata = []
    
    for i, image_id in enumerate(tqdm(unique_ids, desc="Scraping metadata"), 1):
        if not image_id:
            continue
        
        cache_file = os.path.join(cache_dir, f"{image_id}.html")
        
        # Check cache
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            html = fetch_metadata(image_id)
            
            if html and use_cache:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(html)
            
            # Delay for non-cached requests
            if i % 50 == 0:  # Every 50 requests, longer delay
                time.sleep(random.uniform(10, 15))
            else:
                time.sleep(random.uniform(3, 5))
        
        if html:
            metadata = parse_metadata(html, image_id)
            
            # Add source URL
            metadata['detail_url'] = f"https://visualsonline.cancer.gov/details.cfm?imageid={image_id}"
            metadata['thumbnail'] = f"https://visualsonline.cancer.gov/images/{image_id}-previewsm.jpg"
            
            all_metadata.append(metadata)
        else:
            print(f"  ❌ Failed to fetch {image_id}")
    
    # Save
    df_meta = pd.DataFrame(all_metadata)
    
    # Remove entries without titles (failed scrapes)
    df_meta = df_meta[df_meta['Title'].str.len() > 0]
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_meta.to_csv(output_csv, index=False)
    
    print("\n" + "=" * 70)
    print("✅ METADATA SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total images scraped: {len(df_meta)}")
    print(f"With titles: {(df_meta['Title'].str.len() > 0).sum()}")
    print(f"With descriptions: {(df_meta['Description'].str.len() > 0).sum()}")
    print(f"Public domain: {df_meta['License'].str.contains('public domain', case=False, na=False).sum()}")
    print(f"\n📁 Saved to: {output_csv}")
    print("=" * 70 + "\n")
    
    return df_meta

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scrape full metadata for NIH images"
    )
    parser.add_argument(
        '--input',
        default='data/nih_all_images_raw.csv',
        help='Input CSV with image IDs from comprehensive search'
    )
    parser.add_argument(
        '--output',
        default='data/nih_comprehensive_metadata.csv',
        help='Output CSV with full metadata'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable HTML caching (force re-download)'
    )
    
    args = parser.parse_args()
    
    df = scrape_full_metadata(args.input, args.output, use_cache=not args.no_cache)
    
    print("\n✅ Next step: Create comprehensive embeddings")
    print(f"   Run: python src/nih/subsection_semantic_matcher.py --create-embeddings --metadata-csv {args.output} --embeddings-file data/nih_comprehensive_embeddings.pkl")

if __name__ == "__main__":
    main()