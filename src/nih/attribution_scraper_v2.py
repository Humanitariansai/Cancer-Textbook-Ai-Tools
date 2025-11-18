import requests
from bs4 import BeautifulSoup
import pandas as pd
import json, csv, re, os, time, random

def fetch_metadata(image_id, retry_count=3):
    """Fetch HTML using simple requests"""
    url = f"https://visualsonline.cancer.gov/details.cfm?imageid={image_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                html = response.text
                
                # Validate we got real content
                if len(html) > 1000 and "imageid" in html.lower():
                    return html
                else:
                    print(f"  ⚠️  Attempt {attempt+1}: Page seems empty or blocked")
                    
            else:
                print(f"  ⚠️  Attempt {attempt+1}: Got status code {response.status_code}")
            
            if attempt < retry_count - 1:
                time.sleep(random.uniform(2, 4))
                    
        except Exception as e:
            print(f"  ❌ Attempt {attempt+1} failed: {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(random.uniform(2, 4))
    
    return None

def parse_metadata_from_html(html, image_id, original_row):
    """Extract metadata from the HTML page and merge with original row data"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Start with all original columns from the CSV
    metadata = original_row.copy()
    
    # Add new scraped metadata columns
    metadata["Image ID"] = image_id
    metadata["Title"] = ""
    metadata["Description"] = ""
    metadata["Credit"] = ""
    metadata["License"] = ""
    metadata["Source"] = f"https://visualsonline.cancer.gov/details.cfm?imageid={image_id}"
    
    try:
        # The page title is in <h2> at the top
        h2_elem = soup.find('h2')
        if h2_elem:
            metadata["Title"] = h2_elem.get_text(strip=True)
        
        # Find the image information table
        info_table = soup.find('table', class_='image-information-text')
        
        if info_table:
            # Parse table rows for metadata
            rows = info_table.find_all('tr')
            
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                
                if not th or not td:
                    continue
                
                field_name = th.get_text(strip=True).lower().rstrip(':')
                field_value = td.get_text(strip=True)
                
                # Map table fields to our metadata
                if 'title' in field_name:
                    metadata["Title"] = field_value
                elif 'description' in field_name:
                    metadata["Description"] = field_value
                elif 'credit' in field_name or 'source' in field_name or 'creator' in field_name:
                    metadata["Credit"] = field_value
                elif 'license' in field_name or 'rights' in field_name or 'usage' in field_name or 'copyright' in field_name:
                    metadata["License"] = field_value
                elif 'terms' in field_name or 'reuse' in field_name or 'attribution' in field_name:
                    if not metadata["License"]:  # Don't overwrite if already set
                        metadata["License"] = field_value
        
    except Exception as e:
        print(f"  ⚠️  Error parsing HTML: {str(e)}")
    
    return metadata

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape NIH image metadata")
    parser.add_argument(
        '--input',
        default='data/paragraph_image_map_14__20251027_234226.csv',
        help='Input CSV with image URLs'
    )
    parser.add_argument(
        '--output-json',
        default='data/extracted_metadata.json',
        help='Output JSON file'
    )
    parser.add_argument(
        '--output-csv',
        default='data/extracted_metadata.csv',
        help='Output CSV file'
    )
    
    args = parser.parse_args()
    
    input_file = args.input
    html_cache_dir = "data/html_cache"
    output_json = args.output_json
    output_csv = args.output_csv
    
    os.makedirs(html_cache_dir, exist_ok=True)
    
    with open(input_file, "r") as f:
        rows = list(csv.DictReader(f))
    
    all_metadata = []
    
    for i, r in enumerate(rows):  # Process ALL rows
        # Try to get image_id from the detail_url or image_id column
        if "image_id" in r and r["image_id"]:
            image_id = r["image_id"]
        elif "detail_url" in r:
            m = re.search(r"imageid=(\d+)", r["detail_url"])
            if not m:
                print(f"  ⚠️  Skipping row {i+1}: No image_id found in detail_url")
                continue
            image_id = m.group(1)
        else:
            print(f"  ⚠️  Skipping row {i+1}: No image_id or detail_url column found")
            continue
        html_file = os.path.join(html_cache_dir, f"{image_id}.html")
        
        # Check if we already have this HTML cached
        if os.path.exists(html_file):
            print(f"[{i+1}/{len(rows)}] Loading cached HTML for {image_id}...")
            with open(html_file, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            print(f"[{i+1}/{len(rows)}] Fetching {image_id}...")
            html = fetch_metadata(image_id)
            
            if html:
                # Save to cache
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"  ✅ HTML saved")
            else:
                print(f"  ❌ Failed to fetch HTML after retries")
                continue
        
        # Parse metadata from HTML
        if html:
            metadata = parse_metadata_from_html(html, image_id, r)
            all_metadata.append(metadata)
            print(f"  📄 Title: {metadata['Title'][:50] if metadata['Title'] else 'Not found'}...")
        
        # Be nice to the server - random delay between requests
        if i < len(rows) - 1:
            delay = random.uniform(2, 4)
            print(f"  ⏳ Waiting {delay:.1f}s before next request...")
            time.sleep(delay)
    
    # Save extracted metadata
    if all_metadata:
        # Convert list of dicts to DataFrame to handle column ordering
        df = pd.DataFrame(all_metadata)
        
        # Reorder columns: original columns first, then new metadata
        original_cols = ['chapter_id', 'paragraph_id', 'query', 'picked_title', 'detail_url', 
                        'thumbnail', 'image_id', 'match_score', 'candidate_count', 'rank']
        new_cols = ['Image ID', 'Title', 'Description', 'Credit', 'License', 'Source']
        
        # Keep only columns that exist
        ordered_cols = [col for col in original_cols if col in df.columns]
        ordered_cols.extend([col for col in new_cols if col in df.columns])
        
        # Add any remaining columns not in the lists
        remaining_cols = [col for col in df.columns if col not in ordered_cols]
        ordered_cols.extend(remaining_cols)
        
        df = df[ordered_cols]
        
        # Save as JSON
        df.to_json(output_json, orient='records', indent=2, force_ascii=False)
        print(f"\n✅ Saved {len(df)} metadata entries to {output_json}")
        
        # Save as CSV
        df.to_csv(output_csv, index=False)
        print(f"✅ Saved {len(df)} metadata entries to {output_csv}")
        
        # Show column summary
        print(f"\n📋 Columns in output ({len(df.columns)} total):")
        for col in df.columns:
            print(f"  - {col}")

if __name__ == "__main__":
    main()