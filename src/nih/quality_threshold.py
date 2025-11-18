"""
Quality Threshold Filter
=========================
Keeps only high-quality image matches based on rank.
Implements Evin's feedback: "eliminate the ones that didn't make the cut"

Strategy:
- Only keep images with rank <= threshold (default: 5)
- This ensures we only keep the most relevant matches
"""

import pandas as pd
import os

def apply_quality_threshold(input_csv, output_csv, rank_threshold=5, stats_file=None):
    """
    Filter images by quality threshold based on rank
    
    Args:
        input_csv: Input CSV with deduplicated images
        output_csv: Output CSV with only high-quality matches
        rank_threshold: Maximum rank to keep (1-10, default 5)
        stats_file: Optional statistics file
    """
    
    df = pd.read_csv(input_csv)
    
    print("\n" + "=" * 70)
    print("🎯 QUALITY THRESHOLD FILTERING")
    print("=" * 70)
    print(f"Total images before: {len(df)}")
    print(f"Rank threshold: ≤ {rank_threshold} (keeping only top {rank_threshold} matches per subsection)")
    print("=" * 70 + "\n")
    
    # Show rank distribution before filtering
    print("📊 Rank Distribution (Before):")
    rank_counts = df['rank'].value_counts().sort_index()
    for rank, count in rank_counts.items():
        marker = "✓" if rank <= rank_threshold else "✗"
        print(f"  {marker} Rank {rank}: {count} images")
    print()
    
    # Apply threshold
    high_quality = df[df['rank'] <= rank_threshold].copy()
    low_quality = df[df['rank'] > rank_threshold].copy()
    
    # Save high-quality images
    os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
    high_quality.to_csv(output_csv, index=False)
    
    # Save removed images for review
    if len(low_quality) > 0:
        removed_csv = output_csv.replace('.csv', '_removed_low_rank.csv')
        low_quality.to_csv(removed_csv, index=False)
        print(f"📋 Low-rank images saved to: {removed_csv}\n")
    
    # Results
    print("=" * 70)
    print("✅ QUALITY FILTERING COMPLETE")
    print("=" * 70)
    print(f"Original: {len(df)} images")
    print(f"High quality (rank ≤ {rank_threshold}): {len(high_quality)} images ({len(high_quality)/len(df)*100:.1f}%)")
    print(f"Removed (rank > {rank_threshold}): {len(low_quality)} images")
    print(f"\n📁 Saved to: {output_csv}")
    
    # Distribution by subsection
    print("\n" + "=" * 70)
    print("📊 IMAGES PER SUBSECTION (After Quality Filter)")
    print("=" * 70)
    
    subsection_counts = high_quality.groupby(['subsection_id', 'subsection_name']).size()
    total_subsections = df['subsection_id'].nunique()
    subsections_with_images = len(subsection_counts)
    
    for (sub_id, sub_name), count in subsection_counts.items():
        print(f"  {sub_id}. {sub_name[:50]}: {count} images")
    
    print("=" * 70)
    print(f"  TOTAL: {len(high_quality)} images across {subsections_with_images} subsections")
    
    # Check if any subsections lost all images
    subsections_lost = total_subsections - subsections_with_images
    if subsections_lost > 0:
        print(f"  ⚠️  WARNING: {subsections_lost} subsections have no images after filtering")
        
        # Find which subsections lost images
        all_subsections = set(df['subsection_id'].unique())
        remaining_subsections = set(high_quality['subsection_id'].unique())
        lost_subsections = all_subsections - remaining_subsections
        
        if lost_subsections:
            print(f"\n  Subsections without images:")
            for sub_id in sorted(lost_subsections):
                sub_name = df[df['subsection_id'] == sub_id].iloc[0]['subsection_name']
                print(f"    - {sub_id}: {sub_name}")
    
    print("=" * 70 + "\n")
    
    # Statistics file
    if stats_file:
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("QUALITY THRESHOLD FILTERING REPORT\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Rank threshold: ≤ {rank_threshold}\n")
            f.write(f"Original images: {len(df)}\n")
            f.write(f"High quality images: {len(high_quality)}\n")
            f.write(f"Removed images: {len(low_quality)}\n")
            f.write(f"Retention rate: {len(high_quality)/len(df)*100:.1f}%\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("RANK DISTRIBUTION\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("Before filtering:\n")
            for rank, count in rank_counts.items():
                f.write(f"  Rank {rank}: {count} images\n")
            
            f.write("\nAfter filtering:\n")
            high_rank_counts = high_quality['rank'].value_counts().sort_index()
            for rank, count in high_rank_counts.items():
                f.write(f"  Rank {rank}: {count} images\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("IMAGES PER SUBSECTION\n")
            f.write("=" * 70 + "\n\n")
            
            for (sub_id, sub_name), count in subsection_counts.items():
                f.write(f"{sub_id}. {sub_name}: {count} images\n")
            
            if len(low_quality) > 0:
                f.write("\n" + "=" * 70 + "\n")
                f.write("SAMPLE REMOVED IMAGES (Rank > 5)\n")
                f.write("=" * 70 + "\n\n")
                
                for idx, row in low_quality.head(10).iterrows():
                    f.write(f"Rank {row['rank']}: {row['Title']}\n")
                    f.write(f"  Subsection: {row['subsection_name']}\n")
                    f.write(f"  Image ID: {row['image_id']}\n\n")
        
        print(f"📊 Statistics saved to: {stats_file}\n")
    
    return high_quality

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Filter images by quality threshold (rank)"
    )
    parser.add_argument(
        '--input',
        default='data/filtered_images_subsections_dedup.csv',
        help='Input deduplicated CSV'
    )
    parser.add_argument(
        '--output',
        default='data/filtered_images_final_quality.csv',
        help='Output CSV with high-quality images only'
    )
    parser.add_argument(
        '--rank-threshold',
        type=int,
        default=5,
        help='Maximum rank to keep (default: 5)'
    )
    parser.add_argument(
        '--stats',
        default='data/quality_threshold_stats.txt',
        help='Statistics file'
    )
    
    args = parser.parse_args()
    
    apply_quality_threshold(args.input, args.output, args.rank_threshold, args.stats)

if __name__ == "__main__":
    main()