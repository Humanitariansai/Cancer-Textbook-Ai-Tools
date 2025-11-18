"""
Remove Duplicate Images from Subsection Results
================================================
Keeps only the best match for each unique image across all subsections.

Strategy:
- Group by image_id
- Keep the one with lowest rank (rank 1 is best)
- If tied, keep the one from the subsection with more specific query
"""

import pandas as pd
import os

def deduplicate_images(input_csv, output_csv, stats_file=None):
    """
    Remove duplicate images, keeping only the best match for each image
    
    Args:
        input_csv: Input CSV with potentially duplicate images
        output_csv: Output CSV with deduplicated images
        stats_file: Optional file to save deduplication statistics
    """
    
    # Load data
    df = pd.read_csv(input_csv)
    
    print("\n" + "=" * 70)
    print("🔍 IMAGE DEDUPLICATION")
    print("=" * 70)
    print(f"Total rows before: {len(df)}")
    print(f"Unique images: {df['image_id'].nunique()}")
    print("=" * 70 + "\n")
    
    # Find duplicates
    duplicates = df[df.duplicated(subset=['image_id'], keep=False)]
    duplicate_image_ids = duplicates['image_id'].unique()
    
    print(f"Found {len(duplicate_image_ids)} images appearing multiple times:\n")
    
    # Show duplicate examples
    for img_id in list(duplicate_image_ids)[:5]:
        img_rows = df[df['image_id'] == img_id]
        print(f"Image {img_id} ({img_rows.iloc[0]['Title'][:50]}...):")
        for idx, row in img_rows.iterrows():
            print(f"  - Subsection {row['subsection_id']}: {row['subsection_name'][:40]}... (rank {row['rank']})")
        print()
    
    if len(duplicate_image_ids) > 5:
        print(f"... and {len(duplicate_image_ids) - 5} more duplicate images\n")
    
    # Deduplication strategy: Keep the one with best (lowest) rank
    # If tied on rank, keep the one from the most specific subsection (lower subsection_id = more general)
    print("=" * 70)
    print("DEDUPLICATION STRATEGY")
    print("=" * 70)
    print("For each duplicate image:")
    print("  1. Keep the match with lowest rank (rank 1 is best)")
    print("  2. If tied, prefer more specific subsections (higher subsection_id)")
    print("=" * 70 + "\n")
    
    # Sort by: image_id, rank (ascending), subsection_id (descending for specificity)
    df_sorted = df.sort_values(['image_id', 'rank', 'subsection_id'], 
                               ascending=[True, True, False])
    
    # Keep first occurrence (best rank, most specific subsection)
    df_dedup = df_sorted.drop_duplicates(subset=['image_id'], keep='first')
    
    # Sort back by subsection for readability
    df_dedup = df_dedup.sort_values(['subsection_id', 'rank'])
    
    # Save deduplicated data
    os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
    df_dedup.to_csv(output_csv, index=False)
    
    # Statistics
    removed_count = len(df) - len(df_dedup)
    
    print("=" * 70)
    print("✅ DEDUPLICATION COMPLETE")
    print("=" * 70)
    print(f"Original rows: {len(df)}")
    print(f"Deduplicated rows: {len(df_dedup)}")
    print(f"Removed duplicates: {removed_count}")
    print(f"Retention rate: {len(df_dedup)/len(df)*100:.1f}%")
    print(f"\n📁 Saved to: {output_csv}")
    
    # Show distribution by subsection
    print("\n" + "=" * 70)
    print("📊 IMAGES PER SUBSECTION (After Deduplication)")
    print("=" * 70)
    
    subsection_counts = df_dedup.groupby(['subsection_id', 'subsection_name']).size()
    for (sub_id, sub_name), count in subsection_counts.items():
        print(f"  {sub_id}. {sub_name[:50]}: {count} images")
    
    print("=" * 70)
    print(f"  TOTAL: {len(df_dedup)} unique images across {len(subsection_counts)} subsections")
    print("=" * 70 + "\n")
    
    # Save statistics if requested
    if stats_file:
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("IMAGE DEDUPLICATION REPORT\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Original rows: {len(df)}\n")
            f.write(f"Deduplicated rows: {len(df_dedup)}\n")
            f.write(f"Removed duplicates: {removed_count}\n")
            f.write(f"Retention rate: {len(df_dedup)/len(df)*100:.1f}%\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("DUPLICATE IMAGES REMOVED\n")
            f.write("=" * 70 + "\n\n")
            
            for img_id in duplicate_image_ids:
                img_rows = df[df['image_id'] == img_id]
                kept_row = df_dedup[df_dedup['image_id'] == img_id].iloc[0]
                
                f.write(f"Image {img_id}: {img_rows.iloc[0]['Title']}\n")
                f.write(f"  Appeared in {len(img_rows)} subsections\n")
                f.write(f"  Kept: Subsection {kept_row['subsection_id']} (rank {kept_row['rank']})\n")
                f.write(f"  Removed from:\n")
                
                for idx, row in img_rows.iterrows():
                    if row['image_id'] == kept_row['image_id'] and row['subsection_id'] != kept_row['subsection_id']:
                        f.write(f"    - Subsection {row['subsection_id']}: {row['subsection_name'][:50]} (rank {row['rank']})\n")
                f.write("\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("IMAGES PER SUBSECTION (After Deduplication)\n")
            f.write("=" * 70 + "\n\n")
            
            for (sub_id, sub_name), count in subsection_counts.items():
                f.write(f"{sub_id}. {sub_name}: {count} images\n")
        
        print(f"📊 Detailed statistics saved to: {stats_file}\n")
    
    return df_dedup

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Remove duplicate images from subsection results"
    )
    parser.add_argument(
        '--input',
        default='data/filtered_images_subsections.csv',
        help='Input CSV with filtered images'
    )
    parser.add_argument(
        '--output',
        default='data/filtered_images_subsections_dedup.csv',
        help='Output CSV with deduplicated images'
    )
    parser.add_argument(
        '--stats',
        default='data/deduplication_stats.txt',
        help='Statistics report file'
    )
    
    args = parser.parse_args()
    
    deduplicate_images(args.input, args.output, args.stats)

if __name__ == "__main__":
    main()