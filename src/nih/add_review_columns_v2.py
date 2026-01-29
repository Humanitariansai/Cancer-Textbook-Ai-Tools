"""
Add Review Columns for Evin's Feedback (Updated for Secondary Filter)
======================================================================
Adds columns for manual review with proper column ordering
"""

import pandas as pd
import os

def add_review_columns(input_csv, output_csv):
    """
    Add review columns for Evin to mark each image
    """
    
    df = pd.read_csv(input_csv)
    
    # Define the ideal column order
    column_order = [
        'chapter_id',
        'subsection_id', 
        'subsection_name',
        'query',
        'image_id',
        'Title',
        'Description',
        'Credit',
        'License',
        'match_score',
        'combined_score',
        'keyword_score',
        'title_bonus',
        'image_type',
        'key_terms',
        'detail_url',
        'thumbnail',
        'KEEP?',
        'QUALITY',
        'NOTES'
    ]
    
    # Add review columns if they don't exist
    if 'KEEP?' not in df.columns:
        df['KEEP?'] = ''
    if 'QUALITY' not in df.columns:
        df['QUALITY'] = ''
    if 'NOTES' not in df.columns:
        df['NOTES'] = ''
    
    # Reorder columns (only use columns that exist)
    existing_cols = [col for col in column_order if col in df.columns]
    
    # Add any remaining columns that weren't in our order
    remaining_cols = [col for col in df.columns if col not in existing_cols]
    final_order = existing_cols + remaining_cols
    
    df = df[final_order]
    
    # Save
    os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
    df.to_csv(output_csv, index=False)
    
    print("\n" + "=" * 70)
    print("📋 REVIEW SHEET CREATED FOR EVIN")
    print("=" * 70)
    print(f"Total images: {len(df)}")
    print(f"Subsections: {df['subsection_id'].nunique()}")
    print(f"\n📁 Saved to: {output_csv}")
    
    print("\n" + "=" * 70)
    print("INSTRUCTIONS FOR EVIN:")
    print("=" * 70)
    print("For each image row, please fill in:")
    print("")
    print("  Column 'KEEP?':")
    print("    - Write 'YES' if you want this image in the textbook")
    print("    - Write 'NO' if you don't want it")
    print("")
    print("  Column 'QUALITY':")
    print("    - Write 'GOOD' if it's highly relevant/useful")
    print("    - Write 'OK' if it's acceptable but not great")
    print("    - Write 'BAD' if it's not relevant/poor quality")
    print("")
    print("  Column 'NOTES':")
    print("    - Add any comments (why it's good/bad, suggestions, etc.)")
    print("")
    print("SCORING REFERENCE:")
    print("  - combined_score: Final relevance score (0.50-1.0)")
    print("  - match_score: Semantic similarity (0.50-1.0)")
    print("  - keyword_score: How many key terms matched (0.0-0.3)")
    print("  - Higher scores = better match")
    print("=" * 70 + "\n")
    
    # Show sample
    print("📸 SAMPLE FORMAT:")
    print("-" * 70)
    sample_cols = ['subsection_name', 'Title', 'combined_score', 'KEEP?', 'QUALITY']
    available = [c for c in sample_cols if c in df.columns]
    print(df[available].head(3).to_string(index=False))
    print("-" * 70 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Add review columns for Evin's feedback"
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input filtered CSV'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output review sheet'
    )
    
    args = parser.parse_args()
    
    add_review_columns(args.input, args.output)