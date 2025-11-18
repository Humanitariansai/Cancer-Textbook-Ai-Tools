"""
Notebook-Friendly Chapter Processor
====================================
Simple Python functions for Jupyter/Colab - no terminal commands needed!

Usage in Jupyter/Colab:
    from process_chapters_notebook import process_chapter, process_multiple_chapters
    
    # Process one chapter
    process_chapter(3)
    
    # Process multiple chapters
    process_multiple_chapters([3, 4, 5, 6])
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob

# Add script directories to path
sys.path.insert(0, 'src/core')
sys.path.insert(0, 'src/nih')

def process_chapter(chapter_id, min_score=0.5, topk=10, keep_duplicates=True):
    """
    Process a single chapter end-to-end
    
    Parameters:
    -----------
    chapter_id : int or str
        Chapter number (e.g., 3, "14")
    min_score : float
        Minimum semantic similarity score (default: 0.5)
    topk : int
        Maximum images per subsection (default: 10)
    keep_duplicates : bool
        Keep duplicate images across subsections (default: True per Evin's request)
        
    Returns:
    --------
    str : Path to the final review CSV file
    
    Example:
    --------
    # In Jupyter/Colab
    from process_chapters_notebook import process_chapter
    
    output_file = process_chapter(3)
    print(f"Review sheet ready: {output_file}")
    """
    
    chapter_id = str(chapter_id)
    
    print("\n" + "=" * 70)
    print(f"🚀 PROCESSING CHAPTER {chapter_id}")
    print("=" * 70)
    print(f"Settings: min_score={min_score}, topk={topk}, keep_duplicates={keep_duplicates}")
    print("=" * 70 + "\n")
    
    try:
        # STEP 1: Generate subsection queries
        print("📝 STEP 1/5: Generating subsection queries...")
        
        from subsection_query_generator import process_chapter as gen_queries
        subsection_df = gen_queries(chapter_id)
        subsection_csv = f"data/subsection_queries_chapter_{chapter_id}.csv"
        print(f"✅ Generated {len(subsection_df)} subsection queries\n")
        
        # STEP 2: Semantic matching
        print("🔗 STEP 2/5: Semantic matching...")
        
        from subsection_semantic_matcher import match_subsections_to_images
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        semantic_map = f"data/subsection_image_map_semantic_{chapter_id}_{timestamp}.csv"
        
        matches_df = match_subsections_to_images(
            subsection_csv,
            'data/nih_image_embeddings.pkl',
            semantic_map,
            min_score,
            topk
        )
        
        if len(matches_df) == 0:
            print(f"⚠️ No semantic matches found for Chapter {chapter_id}")
            print("Try lowering --min-score (e.g., 0.45)")
            return None
        
        print(f"✅ Found {len(matches_df)} matches\n")
        
        # STEP 3: Scrape metadata
        print("🔍 STEP 3/5: Scraping metadata from NIH...")
        
        # Import and run attribution scraper functions directly
        import requests
        from bs4 import BeautifulSoup
        import time
        import random
        import csv
        import re
        
        # Load the semantic matches
        with open(semantic_map, 'r') as f:
            rows = list(csv.DictReader(f))
        
        # Import scraping functions
        sys.path.insert(0, 'src/nih')
        from attribution_scraper_v2 import fetch_metadata, parse_metadata_from_html
        
        html_cache_dir = "data/html_cache"
        os.makedirs(html_cache_dir, exist_ok=True)
        
        all_metadata = []
        
        for i, r in enumerate(rows):
            image_id = r.get('image_id')
            if not image_id:
                continue
            
            html_file = os.path.join(html_cache_dir, f"{image_id}.html")
            
            if os.path.exists(html_file):
                print(f"[{i+1}/{len(rows)}] Cached: {image_id}")
                with open(html_file, "r", encoding="utf-8") as f:
                    html = f.read()
            else:
                print(f"[{i+1}/{len(rows)}] Fetching: {image_id}")
                html = fetch_metadata(image_id)
                if html:
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    time.sleep(random.uniform(2, 4))
                else:
                    continue
            
            if html:
                metadata = parse_metadata_from_html(html, image_id, r)
                all_metadata.append(metadata)
        
        metadata_df = pd.DataFrame(all_metadata)
        metadata_csv = f"data/extracted_metadata_ch{chapter_id}.csv"
        metadata_df.to_csv(metadata_csv, index=False)
        
        print(f"✅ Scraped metadata for {len(metadata_df)} images\n")
        
        # STEP 4: Filter
        print("🔬 STEP 4/5: Filtering (license + content)...")
        
        from content_filtering_nih import filter_images
        
        filtered_csv = f"data/filtered_semantic_ch{chapter_id}.csv"
        stats_file = f"data/filtering_stats_ch{chapter_id}.txt"
        
        filtered_df = filter_images(metadata_csv, filtered_csv, stats_file)
        print(f"✅ Filtered to {len(filtered_df)} images\n")
        
        # STEP 5: Add review columns (skip dedup if requested)
        print("📋 STEP 5/5: Creating review sheet...")
        
        from add_review_columns import add_review_columns
        
        final_output = f"data/Chapter{chapter_id}_Images_FOR_REVIEW.csv"
        add_review_columns(filtered_csv, final_output)
        
        print(f"✅ Review sheet created\n")
        
        # COMPLETION
        print("=" * 70)
        print(f"🎉 CHAPTER {chapter_id} COMPLETE!")
        print("=" * 70)
        print(f"📁 Review sheet: {final_output}")
        print(f"📊 Total images: {len(filtered_df)}")
        print(f"📧 Ready to send to Evin!")
        print("=" * 70 + "\n")
        
        return final_output
        
    except Exception as e:
        print(f"\n❌ Error processing Chapter {chapter_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_multiple_chapters(chapter_ids, min_score=0.5, topk=10):
    """
    Process multiple chapters in sequence
    
    Parameters:
    -----------
    chapter_ids : list
        List of chapter numbers (e.g., [3, 4, 5, 6])
    min_score : float
        Minimum semantic similarity score
    topk : int
        Maximum images per subsection
        
    Returns:
    --------
    dict : Dictionary mapping chapter_id to output file path
    
    Example:
    --------
    from process_chapters_notebook import process_multiple_chapters
    
    results = process_multiple_chapters([3, 4, 5, 6])
    for ch, file in results.items():
        print(f"Chapter {ch}: {file}")
    """
    
    results = {}
    
    print("\n" + "=" * 70)
    print(f"📚 PROCESSING {len(chapter_ids)} CHAPTERS")
    print("=" * 70)
    print(f"Chapters: {chapter_ids}")
    print("=" * 70 + "\n")
    
    for chapter_id in chapter_ids:
        output = process_chapter(chapter_id, min_score, topk)
        results[chapter_id] = output
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 BATCH PROCESSING COMPLETE")
    print("=" * 70)
    
    for ch_id, output in results.items():
        status = "✅" if output else "❌"
        print(f"{status} Chapter {ch_id}: {output if output else 'Failed'}")
    
    print("=" * 70 + "\n")
    
    return results

# Convenience function
def quick_process(chapter):
    """
    Quick process with default settings
    
    Example:
    --------
    from process_chapters_notebook import quick_process
    quick_process(3)
    """
    return process_chapter(chapter)

if __name__ == "__main__":
    # If run from terminal, use argparse
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--chapter', type=str, help='Chapter to process')
    parser.add_argument('--chapters', nargs='+', help='Multiple chapters')
    parser.add_argument('--min-score', type=float, default=0.5)
    parser.add_argument('--topk', type=int, default=10)
    
    args = parser.parse_args()
    
    if args.chapter:
        process_chapter(args.chapter, args.min_score, args.topk)
    elif args.chapters:
        process_multiple_chapters(args.chapters, args.min_score, args.topk)
    else:
        print("Usage: python process_chapters_notebook.py --chapter 3")
        print("   or: python process_chapters_notebook.py --chapters 3 4 5 6")