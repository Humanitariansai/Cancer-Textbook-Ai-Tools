import pandas as pd
import os
import json

def is_public_domain_or_free_use(license_text):
    """
    Determine if an image has a public domain or free use license.
    Returns True if image can be freely reused.
    """
    if not license_text:
        return False
    
    license_lower = license_text.lower()
    
    # Public domain indicators
    public_domain_keywords = [
        'public domain',
        'freely reused',
        'free to use',
        'no restrictions',
        'cc0',
        'creative commons zero'
    ]
    
    # Check for public domain
    for keyword in public_domain_keywords:
        if keyword in license_lower:
            return True
    
    # Creative Commons licenses that allow reuse
    # CC-BY and CC-BY-SA allow reuse with attribution
    cc_free_licenses = [
        'cc-by',
        'cc by',
        'creative commons attribution',
        'attribution 4.0',
        'attribution-sharealike'
    ]
    
    for keyword in cc_free_licenses:
        if keyword in license_lower:
            return True
    
    # Exclude restrictive licenses
    restrictive_keywords = [
        'all rights reserved',
        'copyright',
        'no derivatives',
        'non-commercial',
        'nc-nd',
        'cc-by-nc',
        'cc-by-nd'
    ]
    
    for keyword in restrictive_keywords:
        if keyword in license_lower:
            return False
    
    return False

def filter_images(input_file, output_file, stats_file):
    """
    Combined filter: License filtering + Content filtering
    1. Filters for public domain/free use images only
    2. Filters for educational content (illustrations, diagrams, microscopy)
    3. Removes clinical scans (X-ray, CT, MRI)
    
    PRESERVES ALL ORIGINAL COLUMNS from input file
    """
    
    # Load data (supports both JSON and CSV)
    if input_file.endswith('.json'):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    else:
        df = pd.read_csv(input_file)
    
    print("\n" + "=" * 70)
    print("🔍 STARTING COMBINED FILTERING PIPELINE")
    print("=" * 70)
    print(f"Loaded {len(df)} total image records")
    print(f"Input columns: {', '.join(df.columns.tolist())}\n")

    original_count = len(df)
    
    # Store original dataframe to preserve all columns
    df_original = df.copy()

    # Create lowercase versions for filtering only (don't modify original)
    df_lower = df.copy()
    for col in ["Title", "Description", "License", "Credit"]:
        if col in df_lower.columns:
            df_lower[col + '_lower'] = df_lower[col].astype(str).str.lower()
        else:
            df_lower[col + '_lower'] = ""

    # ============================================================
    # STAGE 1: LICENSE FILTERING
    # ============================================================
    print("=" * 70)
    print("STAGE 1: LICENSE FILTERING")
    print("=" * 70)
    
    df_lower['is_free_use'] = df_lower['License_lower'].apply(is_public_domain_or_free_use)
    license_mask = df_lower['is_free_use']
    
    print(f"✅ Free use images: {license_mask.sum()} ({license_mask.sum()/original_count*100:.1f}%)")
    print(f"❌ Restricted images: {original_count - license_mask.sum()}")

    # ============================================================
    # STAGE 2: CONTENT TYPE FILTERING
    # ============================================================
    print("\n" + "=" * 70)
    print("STAGE 2: CONTENT TYPE FILTERING")
    print("=" * 70)
    
    # --- FILTER A: Keep illustrations, diagrams, and microscopy ---
    illustration_terms = [
        "illustration", "diagram", "infographic", "graphic", "schematic", 
        "drawing", "chart", "concept", "overview", "pathway",
        "microscopy", "microscope", "microscopic", "cells", "tissue"
    ]
    
    mask_relevant_content = (
        df_lower["Title_lower"].str.contains("|".join(illustration_terms), case=False, na=False) |
        df_lower["Description_lower"].str.contains("|".join(illustration_terms), case=False, na=False)
    )

    # --- FILTER B: Remove clinical scans only ---
    clinical_imaging_terms = [
        "x-ray", "ct scan", "mri scan", "pet scan",
        "radiograph", "mammogram", "ultrasound"
    ]
    
    mask_not_clinical = ~df_lower["Description_lower"].apply(
        lambda x: any(term in str(x) for term in clinical_imaging_terms)
    )
    
    mask_not_clinical_title = ~df_lower["Title_lower"].apply(
        lambda x: any(term in str(x) for term in clinical_imaging_terms)
    )

    # --- Combine all filters ---
    final_mask = license_mask & mask_relevant_content & mask_not_clinical & mask_not_clinical_title
    
    print(f"After content type filter: {final_mask.sum()} images")
    print(f"  - Relevant content (illustrations/diagrams/microscopy): {mask_relevant_content.sum()}")
    print(f"  - Non-clinical imaging: {mask_not_clinical.sum()}")

    # ============================================================
    # STAGE 3: EDUCATIONAL CONTENT BOOST (for sorting only)
    # ============================================================
    educational_terms = [
        "what is", "how", "process", "mechanism", "function",
        "role", "interaction", "relationship", "system", "overview"
    ]
    
    df_lower['educational_score'] = df_lower.apply(
        lambda row: sum(term in str(row['Title_lower']) or term in str(row['Description_lower']) 
                       for term in educational_terms),
        axis=1
    )
    
    # Apply filter to ORIGINAL dataframe (preserves all original columns and values)
    final_filtered = df_original[final_mask].copy()
    
    # Add educational score for sorting
    final_filtered['educational_score'] = df_lower.loc[final_mask, 'educational_score'].values
    
    # Sort by chapter_id and paragraph_id (ascending), then by educational value
    sort_columns = []
    if 'chapter_id' in final_filtered.columns:
        sort_columns.append('chapter_id')
    if 'paragraph_id' in final_filtered.columns:
        sort_columns.append('paragraph_id')
    
    if sort_columns:
        # Convert to numeric if they're strings
        for col in sort_columns:
            final_filtered[col] = pd.to_numeric(final_filtered[col], errors='coerce')
        
        # Sort by chapter_id, paragraph_id (ascending), then educational_score (descending)
        sort_columns.append('educational_score')
        ascending_order = [True] * (len(sort_columns) - 1) + [False]  # Last one descending
        final_filtered = final_filtered.sort_values(sort_columns, ascending=ascending_order)
    else:
        # If no chapter/paragraph columns, just sort by educational value
        final_filtered = final_filtered.sort_values('educational_score', ascending=False)
    
    # Remove the temporary educational_score column
    final_filtered = final_filtered.drop('educational_score', axis=1)

    # ============================================================
    # SAVE RESULTS
    # ============================================================
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    if output_file.endswith('.json'):
        final_filtered.to_json(output_file, orient='records', indent=2, force_ascii=False)
    else:
        final_filtered.to_csv(output_file, index=False)

    # ============================================================
    # GENERATE STATISTICS REPORT
    # ============================================================
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("NIH IMAGE FILTERING REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("SUMMARY:\n")
        f.write(f"  Total images processed: {original_count}\n")
        f.write(f"  After license filter: {license_mask.sum()} ({license_mask.sum()/original_count*100:.1f}%)\n")
        f.write(f"  After content filter: {len(final_filtered)} ({len(final_filtered)/original_count*100:.1f}%)\n")
        f.write(f"  Final usable images: {len(final_filtered)}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("REMOVED IMAGES BREAKDOWN\n")
        f.write("=" * 70 + "\n\n")
        
        removed_license = original_count - license_mask.sum()
        removed_content = license_mask.sum() - len(final_filtered)
        
        f.write(f"Removed by license restrictions: {removed_license}\n")
        f.write(f"Removed by content filter: {removed_content}\n\n")
        
        # Sample of final images
        f.write("=" * 70 + "\n")
        f.write("SAMPLE APPROVED IMAGES (Top 5)\n")
        f.write("=" * 70 + "\n\n")
        
        for idx, row in final_filtered.head(5).iterrows():
            f.write(f"Image ID: {row['Image ID']}\n")
            f.write(f"Title: {row['Title']}\n")
            f.write(f"Description: {row['Description'][:200]}...\n")
            f.write(f"Source: {row['Source']}\n\n")

    # ============================================================
    # CONSOLE OUTPUT
    # ============================================================
    print("\n" + "=" * 70)
    print("✅ FILTERING COMPLETE")
    print("=" * 70)
    print(f"📊 FINAL RESULTS:")
    print(f"  Original: {original_count} images")
    print(f"  Free use: {license_mask.sum()} images ({license_mask.sum()/original_count*100:.1f}%)")
    print(f"  Final filtered: {len(final_filtered)} images ({len(final_filtered)/original_count*100:.1f}%)")
    print(f"\n📁 Saved to: {output_file}")
    print(f"📊 Statistics: {stats_file}")
    print(f"\n✅ ALL ORIGINAL COLUMNS PRESERVED ({len(final_filtered.columns)} columns)")
    
    # Show column list
    print("\n" + "=" * 70)
    print("📋 COLUMNS IN OUTPUT:")
    print("=" * 70)
    for i, col in enumerate(final_filtered.columns, 1):
        print(f"  {i}. {col}")
    
    # Show top results with original data
    print("\n" + "=" * 70)
    print("📸 TOP 5 APPROVED IMAGES (Most Educational)")
    print("=" * 70)
    
    display_cols = ['Image ID', 'Title', 'Description']
    if 'image_id' in final_filtered.columns:
        display_cols[0] = 'image_id'
    
    available_cols = [col for col in display_cols if col in final_filtered.columns]
    
    for idx, row in final_filtered.head(5).iterrows():
        id_col = 'image_id' if 'image_id' in row else 'Image ID'
        title_col = 'Title' if 'Title' in row else 'picked_title'
        desc_col = 'Description' if 'Description' in row else 'description'
        
        if id_col in row:
            print(f"\n{row[id_col]}. {row[title_col] if title_col in row else 'N/A'}")
        if desc_col in row:
            print(f"   Description: {str(row[desc_col])[:150]}...")
        if 'Source' in row:
            print(f"   Source: {row['Source']}")
    
    print("\n" + "=" * 70 + "\n")
    
    return final_filtered

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Combined license and content filter for NIH images"
    )
    parser.add_argument(
        "--input", 
        default="data/extracted_metadata.csv", 
        help="Input CSV with scraped metadata (from attribution_scraper_v2.py)"
    )
    parser.add_argument(
        "--output", 
        default="data/filtered_images_final.csv", 
        help="Output file for filtered images (CSV or JSON)"
    )
    parser.add_argument(
        "--stats",
        default="data/filtering_stats.txt",
        help="Statistics report file"
    )
    
    args = parser.parse_args()
    
    filter_images(args.input, args.output, args.stats)