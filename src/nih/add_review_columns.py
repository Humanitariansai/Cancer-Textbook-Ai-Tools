"""
Add Review Columns for Evin's Feedback
=======================================
Adds columns for manual review and selection
"""

import pandas as pd

def add_review_columns(input_csv, output_csv):
    """
    Add review columns for Evin to mark each image
    """
    
    df = pd.read_csv(input_csv)
    
    # Add review columns right after subsection_name (position 3)
    df.insert(3, 'KEEP?', '')           # Evin marks: YES or NO
    df.insert(4, 'QUALITY', '')         # Evin marks: GOOD, OK, or BAD
    df.insert(5, 'NOTES', '')           # Evin's comments
    
    # Reorder columns for easier review
    review_order = [
        'chapter_id',
        'subsection_id', 
        'subsection_name',
        'image_id',
        'Title',
        'Description',
        'Credit',
        'match_score',              # Shows semantic relevance
        'rank',
        'Source',
        'thumbnail',
        'detail_url',
        'query',
        'picked_title',
        'candidate_count',
        'Image ID',
        'License',
        'KEEP?',                    # ← Evin fills
        'QUALITY',                  # ← Evin fills
        'NOTES',                    # ← Evin fills        
    ]
    
    # Keep only existing columns
    existing = [c for c in review_order if c in df.columns]
    remaining = [c for c in df.columns if c not in existing]
    final_order = existing + remaining
    
    df = df[final_order]
    
    # Save
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
    print("TIP: The 'match_score' column shows semantic relevance")
    print("     (0.7+ is excellent, 0.6+ is good, 0.5+ is okay)")
    print("=" * 70 + "\n")
    
    # Show sample
    print("📸 SAMPLE FORMAT:")
    print("-" * 70)
    sample_cols = ['subsection_name', 'KEEP?', 'QUALITY', 'Title', 'match_score']
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
        default='data/filtered_semantic_final.csv',
        help='Input filtered CSV'
    )
    parser.add_argument(
        '--output',
        default='data/Chapter14_Images_FOR_EVIN_REVIEW.csv',
        help='Output review sheet'
    )
    
    args = parser.parse_args()
    
    add_review_columns(args.input, args.output)