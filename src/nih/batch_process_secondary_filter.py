"""
Batch Process Secondary Filter for All Chapters
================================================
Processes all chapters through the secondary filter in one go.
"""

import os
import glob
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.append('src/nih')
from secondary_filter import apply_secondary_filter

def batch_process_all_chapters(min_score=0.50):
    """
    Process all filtered_license_only_ch*.csv files through secondary filter
    """
    
    # Find all chapter files
    input_files = sorted(glob.glob('data/filtered_license_only_ch*.csv'))
    
    print("\n" + "=" * 70)
    print("🔬 BATCH SECONDARY FILTERING")
    print("=" * 70)
    print(f"Found {len(input_files)} chapter files")
    print(f"Min combined score: {min_score}")
    print("=" * 70 + "\n")
    
    results = []
    
    for input_file in input_files:
        # Extract chapter number
        filename = os.path.basename(input_file)
        chapter = filename.replace('filtered_license_only_ch', '').replace('.csv', '')
        
        # Generate output filename
        output_file = f'data/filtered_secondary_ch{chapter}_0.50.csv'
        
        # Skip if already processed
        if os.path.exists(output_file):
            print(f"⏭️  Chapter {chapter}: Already processed, skipping...")
            continue
        
        print(f"\n{'='*70}")
        print(f"📚 Processing Chapter {chapter}")
        print(f"{'='*70}")
        
        try:
            # Apply secondary filter
            df_filtered = apply_secondary_filter(input_file, output_file, min_score)
            
            # Track results
            df_input = pd.read_csv(input_file)
            results.append({
                'chapter': chapter,
                'input_images': len(df_input),
                'output_images': len(df_filtered),
                'pass_rate': f"{len(df_filtered)/len(df_input)*100:.1f}%",
                'avg_combined_score': f"{df_filtered['combined_score'].mean():.3f}",
                'status': '✅ Success'
            })
            
        except Exception as e:
            print(f"❌ Error processing Chapter {chapter}: {str(e)}")
            results.append({
                'chapter': chapter,
                'input_images': 0,
                'output_images': 0,
                'pass_rate': 'N/A',
                'avg_combined_score': 'N/A',
                'status': f'❌ Failed: {str(e)[:50]}'
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 BATCH PROCESSING SUMMARY")
    print("=" * 70)
    
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    
    # Save summary
    df_results.to_csv('data/secondary_filter_batch_summary.csv', index=False)
    print(f"\n📁 Summary saved to: data/secondary_filter_batch_summary.csv")
    
    # Overall stats
    successful = df_results[df_results['status'] == '✅ Success']
    total_input = successful['input_images'].sum()
    total_output = successful['output_images'].sum()
    
    print("\n" + "=" * 70)
    print("🎯 OVERALL STATISTICS")
    print("=" * 70)
    print(f"Chapters processed: {len(successful)}/{len(results)}")
    print(f"Total input images: {total_input}")
    print(f"Total output images: {total_output}")
    print(f"Overall pass rate: {total_output/total_input*100:.1f}%")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process all chapters through secondary filter")
    parser.add_argument('--min-score', type=float, default=0.50, help='Minimum combined score (default: 0.50)')
    
    args = parser.parse_args()
    
    batch_process_all_chapters(args.min_score)