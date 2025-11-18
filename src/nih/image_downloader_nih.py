import pandas as pd
import requests
import os
import time
import random
from pathlib import Path

def download_image(image_id, detail_url, thumbnail_url, output_dir, size='large'):
    """
    Download image from NIH Visuals Online
    
    Args:
        image_id: The image ID
        detail_url: URL to the detail page
        thumbnail_url: URL to thumbnail (backup)
        output_dir: Directory to save images
        size: 'small' (461x259), 'medium' (960x540), or 'large' (1920x1080)
    """
    
    # Determine DPI based on size
    dpi_map = {
        'small': 72,
        'medium': 150,
        'large': 300
    }
    dpi = dpi_map.get(size, 300)
    
    # Construct download URL
    download_url = f"https://visualsonline.cancer.gov/retrieve.cfm?imageid={image_id}&dpi={dpi}&fileformat=jpg"
    
    output_path = os.path.join(output_dir, f"{image_id}.jpg")
    
    # Skip if already downloaded
    if os.path.exists(output_path):
        print(f"  ✓ Already exists: {image_id}.jpg")
        return True
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': detail_url
    }
    
    try:
        response = requests.get(download_url, headers=headers, timeout=30, stream=True)
        
        if response.status_code == 200:
            # Save image
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(output_path) / 1024  # KB
            print(f"  ✓ Downloaded: {image_id}.jpg ({file_size:.1f} KB)")
            return True
        else:
            print(f"  ✗ Failed: {image_id} (Status {response.status_code})")
            return False
            
    except Exception as e:
        print(f"  ✗ Error downloading {image_id}: {str(e)}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download NIH images from filtered CSV")
    parser.add_argument(
        "--input",
        default="data/filtered_images_final.csv",
        help="Input CSV with filtered images"
    )
    parser.add_argument(
        "--output-dir",
        default="data/downloaded_images/",
        help="Directory to save downloaded images"
    )
    parser.add_argument(
        "--size",
        default="large",
        choices=['small', 'medium', 'large'],
        help="Image size: small (461x259), medium (960x540), large (1920x1080)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between downloads in seconds (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    # Load filtered images
    df = pd.read_csv(args.input)
    
    print("\n" + "=" * 70)
    print("📥 NIH IMAGE DOWNLOADER")
    print("=" * 70)
    print(f"Images to download: {len(df)}")
    print(f"Size: {args.size}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 70 + "\n")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    successful = 0
    failed = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        image_id = row.get('image_id') or row.get('Image ID')
        detail_url = row.get('detail_url') or row.get('Source', '')
        thumbnail = row.get('thumbnail', '')
        
        print(f"[{idx+1}/{len(df)}] Downloading image {image_id}...")
        
        result = download_image(image_id, detail_url, thumbnail, args.output_dir, args.size)
        
        if result:
            if os.path.exists(os.path.join(args.output_dir, f"{image_id}.jpg")):
                successful += 1
        else:
            failed += 1
        
        # Delay between downloads
        if idx < len(df) - 1:
            delay = random.uniform(args.delay, args.delay + 1)
            time.sleep(delay)
    
    print("\n" + "=" * 70)
    print("✅ DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(df)}")
    print(f"\n📁 Images saved to: {args.output_dir}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()