"""
Comprehensive NIH Image Scraper
================================
Scrapes ALL cancer-related images from NIH Visuals Online across multiple topics.
Creates a comprehensive metadata dataset for embedding generation.

This is a ONE-TIME setup to build a complete NIH image database.

Usage:
    python scrape_all_nih_images.py --max-per-query 100
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os
from urllib.parse import quote_plus
from tqdm import tqdm

BASE_URL = "https://visualsonline.cancer.gov/"

# Comprehensive search terms covering all cancer topics
SEARCH_TERMS = [
    # General
    "cancer", "tumor", "malignancy", "carcinoma", "neoplasm",
    
    # Cancer types
    "lung cancer", "breast cancer", "prostate cancer", "colorectal cancer",
    "pancreatic cancer", "melanoma", "leukemia", "lymphoma",
    "ovarian cancer", "liver cancer", "kidney cancer", "brain tumor",
    
    # Biological processes
    "cell division", "cell cycle", "apoptosis", "metastasis",
    "angiogenesis", "tumor microenvironment", "invasion",
    "proliferation", "growth", "oncogene", "tumor suppressor",
    
    # Molecular/Genetic
    "DNA", "mutation", "chromosomal", "genetic", "genomic",
    "epigenetic", "methylation", "gene expression",
    
    # Cellular/Tissue
    "cells", "tissue", "biopsy", "histology", "pathology",
    "fibroblast", "immune cells", "T cells", "macrophage",
    
    # Treatment
    "chemotherapy", "radiation therapy", "immunotherapy",
    "targeted therapy", "surgery", "treatment",
    
    # Metabolism
    "metabolism", "glycolysis", "Warburg effect", "mitochondria",
    
    # Other
    "screening", "prevention", "diagnosis", "prognosis",
    "clinical trial", "biomarker", "risk factor"
]

def search_nih_images(query, max_results=100, delay=3):
    """
    Search NIH for a query and return all results
    
    Args:
        query: Search term
        max_results: Maximum results to retrieve
        delay: Delay between requests
    """
    
    encoded_query = quote_plus(query)
    search_url = f"{BASE_URL}searchaction.cfm?q={encoded_query}&sort=relevance"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"  ⚠️  Status {response.status_code} for query: {query}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find result containers
        containers = soup.find_all("div", class_="resultsitempic")
        
        results = []
        for container in containers[:max_results]:
            try:
                img_tag = container.find("img")
                link_tag = container.find("a")
                
                if not img_tag or not link_tag:
                    continue
                
                # Get URLs
                thumbnail = img_tag.get("src", "")
                if thumbnail and not thumbnail.startswith("http"):
                    thumbnail = BASE_URL + thumbnail.lstrip("/")
                
                detail_url = link_tag.get("href", "")
                if detail_url and not detail_url.startswith("http"):
                    detail_url = BASE_URL + detail_url.lstrip("/")
                
                # Extract image ID
                image_id = ""
                match = re.search(r"imageid=(\d+)", detail_url)
                if match:
                    image_id = match.group(1)
                
                # Get description snippet
                desc_div = container.find_next_sibling("div", class_="resultsitemdesc")
                snippet = desc_div.get_text(" ", strip=True) if desc_div else ""
                
                title = img_tag.get("alt", "").strip() or snippet[:100] or "Image"
                
                results.append({
                    "image_id": image_id,
                    "title": title,
                    "detail_url": detail_url,
                    "thumbnail": thumbnail,
                    "snippet": snippet,
                    "search_query": query
                })
                
            except Exception as e:
                continue
        
        time.sleep(delay + random.uniform(0, 2))
        return results
        
    except Exception as e:
        print(f"  ❌ Error searching '{query}': {e}")
        return []

def scrape_all_images(search_terms, max_per_query=100, output_csv='data/nih_all_images_raw.csv'):
    """
    Scrape images for all search terms
    """
    
    print("\n" + "=" * 70)
    print("🔍 COMPREHENSIVE NIH IMAGE SCRAPING")
    print("=" * 70)
    print(f"Search terms: {len(search_terms)}")
    print(f"Max per query: {max_per_query}")
    print(f"Estimated time: {len(search_terms) * 5 / 60:.0f} minutes")
    print("=" * 70 + "\n")
    
    all_images = []
    
    for i, term in enumerate(tqdm(search_terms, desc="Searching NIH"), 1):
        results = search_nih_images(term, max_per_query, delay=random.uniform(3, 5))
        
        if results:
            all_images.extend(results)
            print(f"  [{i}/{len(search_terms)}] '{term}': {len(results)} images")
        else:
            print(f"  [{i}/{len(search_terms)}] '{term}': 0 images")
    
    # Create DataFrame
    df = pd.DataFrame(all_images)
    
    # Remove duplicates (same image_id)
    df_dedup = df.drop_duplicates(subset=['image_id'], keep='first')
    
    print("\n" + "=" * 70)
    print("📊 SCRAPING RESULTS")
    print("=" * 70)
    print(f"Total results: {len(df)}")
    print(f"Unique images: {len(df_dedup)}")
    print(f"Duplicates removed: {len(df) - len(df_dedup)}")
    
    # Save
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_dedup.to_csv(output_csv, index=False)
    
    print(f"\n📁 Saved to: {output_csv}")
    print("=" * 70 + "\n")
    
    return df_dedup

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scrape comprehensive NIH image database"
    )
    parser.add_argument(
        '--max-per-query',
        type=int,
        default=100,
        help='Maximum images per search query (default: 100)'
    )
    parser.add_argument(
        '--output',
        default='data/nih_all_images_raw.csv',
        help='Output CSV file'
    )
    parser.add_argument(
        '--custom-terms',
        nargs='+',
        help='Custom search terms (overrides defaults)'
    )
    
    args = parser.parse_args()
    
    search_terms = args.custom_terms if args.custom_terms else SEARCH_TERMS
    
    df = scrape_all_images(search_terms, args.max_per_query, args.output)
    
    print("\n📊 Top 10 Search Terms by Results:")
    print("-" * 70)
    term_counts = df['search_query'].value_counts().head(10)
    for term, count in term_counts.items():
        print(f"  {term}: {count} unique images")
    
    print("\n✅ Next step: Scrape full metadata and create embeddings")
    print(f"   Run: python src/nih/scrape_full_metadata.py --input {args.output}")

if __name__ == "__main__":
    main()