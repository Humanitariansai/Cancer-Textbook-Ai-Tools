"""
Filter Out Irrelevant Images
=============================
Removes images that are not educational/scientific content:
- Buildings, facilities
- People portraits
- Lab equipment (agar plates, etc.)
- Generic/unrelated content
"""

import pandas as pd
import os

def is_irrelevant(row):
    """
    Check if an image is irrelevant based on title and description
    
    Returns True if image should be REMOVED
    """
    title = str(row['Title']).lower()
    description = str(row['Description']).lower()
    
    # Irrelevant keywords
    irrelevant_terms = [
        # Buildings/facilities
        'cancer center', 'building', 'facility', 'garden', 'healing garden',
        
        # People/portraits
        'portrait', 'headshot', 'researcher', 'scientist', 'doctor', 'dr.',
        
        # Lab equipment (non-educational)
        'agar plates', 'lab equipment', 'petri dish',
        
        # Generic/unrelated
        'bowel obstruction', 'lymphedema',
        
        # Stage diagrams (clinical, not TME-related)
        'stage ib', 'stage iia', 'stage iiia', 'stage iiib', 'staging',
        
        # Unrelated diseases
        'chorioretinitis', 'vhl renal', 'bhd renal', 'melanoma stage',
        
        # Non-TME specific histology
        'ductal carcinoma' and 'infiltrating',
    ]
    
    # Check for irrelevant terms
    for term in irrelevant_terms:
        if term in title or term in description:
            return True
    
    # Additional checks
    # Remove if it's just a person's name in the title
    if len(title.split()) <= 3 and ',' in title:
        # Likely a person's name like "Smith, John"
        return True
    
    return False

def filter_irrelevant_images(input_csv, output_csv, removed_csv=None):
    """
    Filter out irrelevant images
    
    Args:
        input_csv: Deduplicated CSV
        output_csv: Output CSV with only relevant images
        removed_csv: Optional CSV to save removed images for review
    """
    
    df = pd.read_csv(input_csv)
    
    print("\n" + "=" * 70)
    print("🔬 RELEVANCE FILTERING")
    print("=" * 70)
    print(f"Total images before: {len(df)}")
    print("=" * 70 + "\n")
    
    # Apply filter
    df['is_irrelevant'] = df.apply(is_irrelevant, axis=1)
    
    relevant_df = df[~df['is_irrelevant']].drop('is_irrelevant', axis=1)
    irrelevant_df = df[df['is_irrelevant']].drop('is_irrelevant', axis=1)
    
    # Save relevant images
    os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
    relevant_df.to_csv(output_csv, index=False)
    
    # Save removed images for review
    if removed_csv and len(irrelevant_df) > 0:
        irrelevant_df.to_csv(removed_csv, index=False)
        print(f"📋 Removed images saved to: {removed_csv}\n")
    
    # Show what was removed
    print("=" * 70)
    print(f"❌ REMOVED IRRELEVANT IMAGES ({len(irrelevant_df)} total)")
    print("=" * 70)
    
    if len(irrelevant_df) > 0:
        print("\nExamples of removed images:\n")
        for idx, row in irrelevant_df.head(10).iterrows():
            print(f"  - {row['image_id']}: {row['Title']}")
            print(f"    Reason: {row['Description'][:80]}...\n")
    else:
        print("  (None removed - all images are relevant!)\n")
    
    # Results
    print("=" * 70)
    print("✅ RELEVANCE FILTERING COMPLETE")
    print("=" * 70)
    print(f"Original: {len(df)} images")
    print(f"Relevant: {len(relevant_df)} images ({len(relevant_df)/len(df)*100:.1f}%)")
    print(f"Removed: {len(irrelevant_df)} images")
    print(f"\n📁 Saved to: {output_csv}")
    
    # Distribution by subsection
    print("\n" + "=" * 70)
    print("📊 IMAGES PER SUBSECTION (After Relevance Filter)")
    print("=" * 70)
    
    subsection_counts = relevant_df.groupby(['subsection_id', 'subsection_name']).size()
    for (sub_id, sub_name), count in subsection_counts.items():
        print(f"  {sub_id}. {sub_name[:50]}: {count} images")
    
    print("=" * 70)
    print(f"  TOTAL: {len(relevant_df)} relevant images")
    print("=" * 70 + "\n")
    
    return relevant_df

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Filter out irrelevant images (buildings, people, equipment)"
    )
    parser.add_argument(
        '--input',
        default='data/filtered_images_subsections_dedup.csv',
        help='Input deduplicated CSV'
    )
    parser.add_argument(
        '--output',
        default='data/filtered_images_relevant.csv',
        help='Output CSV with only relevant images'
    )
    parser.add_argument(
        '--removed',
        default='data/removed_irrelevant.csv',
        help='CSV with removed images for review'
    )
    
    args = parser.parse_args()
    
    filter_irrelevant_images(args.input, args.output, args.removed)

if __name__ == "__main__":
    main()