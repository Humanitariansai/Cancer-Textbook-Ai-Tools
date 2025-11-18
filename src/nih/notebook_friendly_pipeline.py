"""
NIH Image Pipeline - Notebook/Colab Friendly
=============================================
Easy-to-use functions for Jupyter Notebook or Google Colab

Usage in notebook:
    from nih_pipeline import run_pipeline
    
    # Process chapters 4-9
    run_pipeline(chapters=[4, 5, 6, 7, 8, 9], download_size='large')
    
    # Process all chapters
    run_pipeline(chapters='all', download_size='medium')
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add src directories to path for imports
sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'nih'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'core'))


def run_pipeline(
    chapters='all',
    input_csv='data/paragraph_image_map_14__20251027_234226.csv',
    download_size='large',
    skip_download=False,
    output_dir='data'
):
    """
    Run the complete NIH image pipeline
    
    Parameters:
    -----------
    chapters : list or 'all'
        List of chapter IDs to process (e.g., [4, 5, 6, 7, 8, 9])
        Or 'all' to process all chapters
        
    input_csv : str
        Path to the paragraph-image mapping CSV
        
    download_size : str
        Image size: 'small', 'medium', or 'large'
        
    skip_download : bool
        If True, only get metadata without downloading images
        
    output_dir : str
        Directory for output files (default: 'data')
        
    Returns:
    --------
    dict with paths to generated files
    
    Example:
    --------
    # In Jupyter/Colab:
    from nih_pipeline import run_pipeline
    
    results = run_pipeline(
        chapters=[4, 5, 6, 7, 8, 9],
        download_size='large'
    )
    
    print(f"Downloaded {results['num_images']} images")
    """
    
    print("\n" + "=" * 70)
    print("🚀 NIH IMAGE PIPELINE")
    print("=" * 70)
    print(f"Chapters: {chapters}")
    print(f"Download size: {download_size}")
    print(f"Skip download: {skip_download}")
    print("=" * 70 + "\n")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        'selected_csv': None,
        'metadata_csv': None,
        'filtered_csv': None,
        'attributions_csv': None,
        'download_dir': None,
        'num_images': 0
    }
    
    try:
        # ============================================================
        # STEP 1: Select Chapters
        # ============================================================
        print("📚 STEP 1: Selecting chapters...")
        
        if not os.path.exists(input_csv):
            raise FileNotFoundError(f"Input CSV not found: {input_csv}")
        
        df = pd.read_csv(input_csv)
        
        if chapters != 'all':
            # Filter specific chapters
            df['chapter_id'] = df['chapter_id'].astype(str)
            chapter_ids_str = [str(ch) for ch in chapters]
            df = df[df['chapter_id'].isin(chapter_ids_str)]
            
            if len(df) == 0:
                available = sorted(pd.read_csv(input_csv)['chapter_id'].unique())
                raise ValueError(f"No images found for chapters {chapters}. Available: {available}")
        
        # Save selected chapters
        selected_csv = os.path.join(output_dir, 'selected_chapters_images.csv')
        df.to_csv(selected_csv, index=False)
        results['selected_csv'] = selected_csv
        
        print(f"✅ Selected {len(df)} images from {df['chapter_id'].nunique()} chapters\n")
        
        # ============================================================
        # STEP 2: Scrape Metadata
        # ============================================================
        print("🔍 STEP 2: Scraping metadata from NIH...")
        
        from attribution_scraper_v2 import fetch_metadata, parse_metadata_from_html
        import csv
        import re
        import time
        import random
        
        html_cache_dir = os.path.join(output_dir, "html_cache")
        os.makedirs(html_cache_dir, exist_ok=True)
        
        all_metadata = []
        
        for i, (idx, r) in enumerate(df.iterrows()):
            if "image_id" in r and r["image_id"]:
                image_id = str(r["image_id"])
            elif "detail_url" in r:
                m = re.search(r"imageid=(\d+)", r["detail_url"])
                if not m:
                    continue
                image_id = m.group(1)
            else:
                continue
            
            html_file = os.path.join(html_cache_dir, f"{image_id}.html")
            
            if os.path.exists(html_file):
                print(f"[{i+1}/{len(df)}] Cached: {image_id}")
                with open(html_file, "r", encoding="utf-8") as f:
                    html = f.read()
            else:
                print(f"[{i+1}/{len(df)}] Fetching: {image_id}")
                html = fetch_metadata(image_id)
                if html:
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    time.sleep(random.uniform(2, 4))
                else:
                    continue
            
            if html:
                metadata = parse_metadata_from_html(html, image_id, r.to_dict())
                all_metadata.append(metadata)
        
        metadata_df = pd.DataFrame(all_metadata)
        metadata_csv = os.path.join(output_dir, 'extracted_metadata.csv')
        metadata_df.to_csv(metadata_csv, index=False)
        results['metadata_csv'] = metadata_csv
        
        print(f"✅ Scraped metadata for {len(metadata_df)} images\n")
        
        # ============================================================
        # STEP 3: Filter Images
        # ============================================================
        print("🔬 STEP 3: Filtering images (license + content)...")
        
        from content_filtering_nih import filter_images
        
        filtered_csv = os.path.join(output_dir, 'filtered_images_final.csv')
        stats_file = os.path.join(output_dir, 'filtering_stats.txt')
        
        filtered_df = filter_images(metadata_csv, filtered_csv, stats_file)
        results['filtered_csv'] = filtered_csv
        results['num_images'] = len(filtered_df)
        
        print(f"✅ Filtered to {len(filtered_df)} usable images\n")
        
        # ============================================================
        # STEP 4: Generate Attributions
        # ============================================================
        print("📝 STEP 4: Generating attributions...")
        
        from generate_attributions import generate_attribution_text, generate_caption_text
        
        filtered_df['attribution_text'] = filtered_df.apply(generate_attribution_text, axis=1)
        filtered_df['caption_text'] = filtered_df.apply(generate_caption_text, axis=1)
        
        attributions_csv = os.path.join(output_dir, 'image_attributions.csv')
        filtered_df.to_csv(attributions_csv, index=False)
        results['attributions_csv'] = attributions_csv
        
        print(f"✅ Generated attributions\n")
        
        # ============================================================
        # STEP 5: Download Images (Optional)
        # ============================================================
        if not skip_download:
            print(f"📥 STEP 5: Downloading {download_size} resolution images...")
            
            from image_downloader_nih import download_image
            
            download_dir = os.path.join(output_dir, 'downloaded_images')
            os.makedirs(download_dir, exist_ok=True)
            results['download_dir'] = download_dir
            
            successful = 0
            for idx, row in filtered_df.iterrows():
                image_id = row.get('image_id') or row.get('Image ID')
                detail_url = row.get('detail_url') or row.get('Source', '')
                
                if download_image(image_id, detail_url, '', download_dir, download_size):
                    successful += 1
                    
                if idx < len(filtered_df) - 1:
                    time.sleep(random.uniform(2, 3))
            
            print(f"✅ Downloaded {successful} images\n")
        else:
            print("⏭️  STEP 5: Skipped image download\n")
        
        # ============================================================
        # COMPLETION
        # ============================================================
        print("=" * 70)
        print("🎉 PIPELINE COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Summary:")
        print(f"  Chapters processed: {df['chapter_id'].nunique()}")
        print(f"  Images retrieved: {len(metadata_df)}")
        print(f"  Images filtered: {results['num_images']}")
        
        if not skip_download:
            print(f"  Images downloaded: {successful}")
        
        print(f"\n📂 Output files:")
        for key, path in results.items():
            if path and key != 'num_images':
                print(f"  {key}: {path}")
        
        print("=" * 70 + "\n")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_chapters(input_csv='data/paragraph_image_map_14__20251027_234226.csv'):
    """
    List all available chapters in the dataset
    
    Parameters:
    -----------
    input_csv : str
        Path to the paragraph-image mapping CSV
        
    Example:
    --------
    from nih_pipeline import list_chapters
    list_chapters()
    """
    
    if not os.path.exists(input_csv):
        print(f"❌ File not found: {input_csv}")
        return
    
    df = pd.read_csv(input_csv)
    
    print("\n" + "=" * 70)
    print("📚 AVAILABLE CHAPTERS")
    print("=" * 70)
    
    chapter_stats = df.groupby('chapter_id').size().sort_index()
    
    for chapter_id, count in chapter_stats.items():
        print(f"  Chapter {chapter_id}: {count} images")
    
    print("=" * 70)
    print(f"  TOTAL: {len(df)} images across {len(chapter_stats)} chapters")
    print("=" * 70 + "\n")
    
    return chapter_stats.index.tolist()


# Convenience function for Colab
def quick_run(chapters, size='large'):
    """
    Quick run with minimal parameters
    
    Example in Colab/Jupyter:
    --------------------------
    from nih_pipeline import quick_run
    quick_run([4, 5, 6, 7, 8, 9])
    """
    return run_pipeline(chapters=chapters, download_size=size)