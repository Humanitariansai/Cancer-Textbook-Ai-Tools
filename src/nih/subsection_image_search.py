"""
Subsection-Based NIH Image Search
==================================
Searches NIH Visuals Online using subsection queries and maps images to subsections.

Usage:
    python subsection_image_search.py --chapter 14 --limit 10
"""

import pandas as pd
import requests
import time
import random
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BASE_URL = "https://visualsonline.cancer.gov/"

def search_nih_by_query(query, limit=10, delay=5):
    """
    Search NIH Visuals Online for a given query
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        delay: Seconds to wait before returning (to be respectful)
        
    Returns:
        List of dicts with image info: {title, url, thumbnail, image_id}
    """
    
    # Encode query for URL
    encoded_query = quote_plus(query[:200])  # Limit query length
    search_url = f"{BASE_URL}searchaction.cfm?q={encoded_query}&sort=relevance"
    
    # Vary user agents to avoid detection
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Add delay before request
            if attempt > 0:
                wait_time = delay * (2 ** attempt) + random.uniform(1, 3)
                print(f"  ⏳ Retry {attempt + 1}/{max_retries}, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            
            response = requests.get(search_url, headers=headers, timeout=45)
            
            if response.status_code == 403:
                print(f"  ⚠️  Got 403 Forbidden (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    continue
                return []
            
            if response.status_code != 200:
                print(f"  ⚠️  Got status code {response.status_code}")
                if attempt < max_retries - 1:
                    continue
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result containers
            containers = soup.find_all("div", class_="resultsitempic")
            
            results = []
            for idx, container in enumerate(containers[:limit], 1):
                try:
                    img_tag = container.find("img")
                    link_tag = container.find("a")
                    
                    if not img_tag or not link_tag:
                        continue
                    
                    # Get image URL and detail URL
                    thumbnail = img_tag.get("src", "")
                    if thumbnail and not thumbnail.startswith("http"):
                        thumbnail = BASE_URL + thumbnail.lstrip("/")
                    
                    detail_url = link_tag.get("href", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = BASE_URL + detail_url.lstrip("/")
                    
                    # Extract image ID from detail URL
                    image_id = ""
                    match = re.search(r"imageid=(\d+)", detail_url)
                    if match:
                        image_id = match.group(1)
                    
                    title = img_tag.get("alt", f"Image {idx}")
                    
                    results.append({
                        "title": title,
                        "detail_url": detail_url,
                        "thumbnail": thumbnail,
                        "image_id": image_id,
                        "rank": idx
                    })
                    
                except Exception as e:
                    print(f"  ⚠️  Error parsing result {idx}: {e}")
                    continue
            
            # Be respectful - add delay
            time.sleep(delay + random.uniform(1, 3))
            
            return results
            
        except requests.exceptions.Timeout:
            print(f"  ⏰ Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                continue
            return []
            
        except Exception as e:
            print(f"  ❌ Search failed: {e}")
            if attempt < max_retries - 1:
                continue
            return []
    
    return []

def search_all_subsections(subsection_csv, images_per_subsection=10, output_csv=None):
    """
    Search NIH for all subsections and create image mapping
    
    Args:
        subsection_csv: CSV with subsection queries
        images_per_subsection: Max images to retrieve per subsection
        output_csv: Output file path
        
    Returns:
        DataFrame with subsection-image mappings
    """
    
    # Load subsection queries
    df_queries = pd.read_csv(subsection_csv)
    
    print("\n" + "=" * 70)
    print("🔍 NIH SUBSECTION IMAGE SEARCH")
    print("=" * 70)
    print(f"Subsections: {len(df_queries)}")
    print(f"Images per subsection: {images_per_subsection}")
    print("=" * 70 + "\n")
    
    all_mappings = []
    
    for idx, row in df_queries.iterrows():
        chapter_id = row['chapter_id']
        subsection_id = row['subsection_id']
        subsection_name = row['subsection_name']
        query = row['query_final']
        
        print(f"[{idx+1}/{len(df_queries)}] {subsection_name}")
        print(f"  Query: {query[:100]}...")
        
        # Search NIH
        results = search_nih_by_query(query, limit=images_per_subsection, delay=random.uniform(2, 4))
        
        if not results:
            print(f"  ⚠️  No results found")
            continue
        
        print(f"  ✅ Found {len(results)} images")
        
        # Create mappings
        for result in results:
            mapping = {
                'chapter_id': chapter_id,
                'subsection_id': subsection_id,
                'subsection_name': subsection_name,
                'query': query[:500],  # Truncate long queries
                'picked_title': result['title'],
                'detail_url': result['detail_url'],
                'thumbnail': result['thumbnail'],
                'image_id': result['image_id'],
                'rank': result['rank'],
                'candidate_count': len(results)
            }
            all_mappings.append(mapping)
    
    # Create DataFrame
    df_mappings = pd.DataFrame(all_mappings)
    
    # Save to CSV
    if output_csv:
        os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
        df_mappings.to_csv(output_csv, index=False)
        
        print("\n" + "=" * 70)
        print("✅ SEARCH COMPLETE")
        print("=" * 70)
        print(f"Total subsections searched: {len(df_queries)}")
        print(f"Total images found: {len(df_mappings)}")
        print(f"Average images per subsection: {len(df_mappings)/len(df_queries):.1f}")
        print(f"\n📁 Saved to: {output_csv}")
        print("=" * 70 + "\n")
    
    return df_mappings

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Search NIH using subsection queries"
    )
    parser.add_argument(
        '--chapter',
        type=str,
        required=True,
        help='Chapter ID to process (e.g., "14")'
    )
    parser.add_argument(
        '--subsection-csv',
        help='Path to subsection queries CSV (auto-detected if not provided)'
    )
    parser.add_argument(
        '--output',
        help='Output CSV path (auto-generated if not provided)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum images per subsection (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Auto-detect input file if not provided
    if not args.subsection_csv:
        args.subsection_csv = f"data/subsection_queries_chapter_{args.chapter}.csv"
    
    # Auto-generate output file if not provided
    if not args.output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"data/subsection_image_map_{args.chapter}_{timestamp}.csv"
    
    # Check if input exists
    if not os.path.exists(args.subsection_csv):
        print(f"❌ Input file not found: {args.subsection_csv}")
        print(f"\nRun this first:")
        print(f"  python src/core/subsection_query_generator.py --chapter {args.chapter}")
        return
    
    # Run search
    df_mappings = search_all_subsections(
        args.subsection_csv,
        images_per_subsection=args.limit,
        output_csv=args.output
    )
    
    # Show sample results
    print("📸 SAMPLE RESULTS (first 3):")
    print("-" * 70)
    for idx, row in df_mappings.head(3).iterrows():
        print(f"\n{row['subsection_name']}")
        print(f"  Image: {row['picked_title']}")
        print(f"  ID: {row['image_id']}")
        print(f"  Rank: {row['rank']}")

if __name__ == "__main__":
    main()