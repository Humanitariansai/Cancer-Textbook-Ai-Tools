import pandas as pd
import os
import json

def filter_images(input_file, output_file, stats_file):
    """
    Content filtering for NIH images
    NO LICENSE FILTERING - includes both public domain and copyrighted
    1. Filters for educational content (illustrations, diagrams, microscopy)
    2. Removes clinical scans (X-ray, CT, MRI)
    
    PRESERVES ALL ORIGINAL COLUMNS including License
    """
    
    # Load data
    if input_file.endswith('.json'):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    else:
        df = pd.read_csv(input_file)
    
    print("\n" + "=" * 70)
    print("🔍 CONTENT FILTERING (ALL LICENSES INCLUDED)")
    print("=" * 70)
    print(f"Loaded {len(df)} total image records")
    print(f"Input columns: {', '.join(df.columns.tolist())}\n")

    original_count = len(df)
    
    # Store original dataframe
    df_original = df.copy()

    # Create lowercase versions for filtering
    df_lower = df.copy()
    for col in ["Title", "Description", "License", "Credit"]:
        if col in df_lower.columns:
            df_lower[col + '_lower'] = df_lower[col].astype(str).str.lower()
        else:
            df_lower[col + '_lower'] = ""

    # ============================================================
    # LICENSE INFO (NO FILTERING - JUST REPORTING)
    # ============================================================
    print("=" * 70)
    print("LICENSE DISTRIBUTION (NOT FILTERING)")
    print("=" * 70)
    
    public_domain = df['License'].str.contains('public domain', case=False, na=False).sum()
    copyrighted = df['License'].str.contains('copyright', case=False, na=False).sum()
    
    print(f"Public domain: {public_domain}")
    print(f"Copyrighted: {copyrighted}")
    print(f"Other/Unknown: {len(df) - public_domain - copyrighted}")
    print("\n⚠️  Including ALL licenses - Evin will filter by license type")

    # ============================================================
    # CONTENT TYPE FILTERING
    # ============================================================
    print("\n" + "=" * 70)
    print("CONTENT TYPE FILTERING")
    print("=" * 70)
    
    # Keep illustrations, diagrams, and microscopy
    illustration_terms = [
        "illustration", "diagram", "infographic", "graphic", "schematic", 
        "drawing", "chart", "concept", "overview", "pathway",
        "microscopy", "microscope", "microscopic", "cells", "tissue"
    ]
    
    mask_relevant_content = (
        df_lower["Title_lower"].str.contains("|".join(illustration_terms), case=False, na=False) |
        df_lower["Description_lower"].str.contains("|".join(illustration_terms), case=False, na=False)
    )

    # Remove clinical scans
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

    # Combine filters (NO LICENSE FILTER)
    final_mask = mask_relevant_content & mask_not_clinical & mask_not_clinical_title
    
    print(f"After content type filter: {final_mask.sum()} images")
    print(f"  - Relevant content: {mask_relevant_content.sum()}")
    print(f"  - Non-clinical imaging: {mask_not_clinical.sum()}")

    # ============================================================
    # EDUCATIONAL CONTENT BOOST
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
    
    # Apply filter to original dataframe
    final_filtered = df_original[final_mask].copy()
    
    # Add educational score
    final_filtered['educational_score'] = df_lower.loc[final_mask, 'educational_score'].values
    
    # Sort
    sort_columns = []
    if 'chapter_id' in final_filtered.columns:
        sort_columns.append('chapter_id')
    if 'paragraph_id' in final_filtered.columns:
        sort_columns.append('paragraph_id')
    
    if sort_columns:
        for col in sort_columns:
            final_filtered[col] = pd.to_numeric(final_filtered[col], errors='coerce')
        sort_columns.append('educational_score')
        ascending_order = [True] * (len(sort_columns) - 1) + [False]
        final_filtered = final_filtered.sort_values(sort_columns, ascending=ascending_order)
    else:
        final_filtered = final_filtered.sort_values('educational_score', ascending=False)
    
    # Remove temp column
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
    # STATISTICS
    # ============================================================
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("NIH IMAGE FILTERING REPORT (ALL LICENSES)\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("SUMMARY:\n")
        f.write(f"  Total images processed: {original_count}\n")
        f.write(f"  After content filter: {len(final_filtered)} ({len(final_filtered)/original_count*100:.1f}%)\n")
        f.write(f"  Final usable images: {len(final_filtered)}\n\n")
        
        f.write("LICENSE BREAKDOWN (ALL INCLUDED):\n")
        f.write(f"  Public domain: {public_domain}\n")
        f.write(f"  Copyrighted: {copyrighted}\n\n")

    # ============================================================
    # CONSOLE OUTPUT
    # ============================================================
    print("\n" + "=" * 70)
    print("✅ FILTERING COMPLETE (ALL LICENSES INCLUDED)")
    print("=" * 70)
    print(f"📊 FINAL RESULTS:")
    print(f"  Original: {original_count} images")
    print(f"  Final filtered: {len(final_filtered)} images ({len(final_filtered)/original_count*100:.1f}%)")
    print(f"  Public domain: {final_filtered['License'].str.contains('public domain', case=False, na=False).sum()}")
    print(f"  Copyrighted: {final_filtered['License'].str.contains('copyright', case=False, na=False).sum()}")
    print(f"\n📁 Saved to: {output_file}")
    print(f"📊 Statistics: {stats_file}")
    print("=" * 70 + "\n")
    
    return final_filtered

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Content filter for NIH images (includes all licenses)"
    )
    parser.add_argument(
        "--input", 
        default="data/extracted_metadata.csv", 
        help="Input CSV with scraped metadata"
    )
    parser.add_argument(
        "--output", 
        default="data/filtered_images_all_licenses.csv", 
        help="Output file for filtered images"
    )
    parser.add_argument(
        "--stats",
        default="data/filtering_stats.txt",
        help="Statistics report file"
    )
    
    args = parser.parse_args()
    
    filter_images(args.input, args.output, args.stats)