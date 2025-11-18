import pandas as pd
import os

def generate_review_table(attrib_file, chapter_file, out_file):
    attrib_df = pd.read_csv(attrib_file)
    chapter_df = pd.read_csv(chapter_file)

    # Normalize and fix types
    attrib_df["chapter_id"] = attrib_df["chapter_id"].astype(str).str.strip()
    chapter_df["chapter_id"] = chapter_df["chapter_id"].astype(str).str.strip()
    attrib_df["paragraph_id"] = attrib_df["paragraph_id"].astype(float).astype(int)
    chapter_df["paragraph_id"] = chapter_df["paragraph_id"].astype(float).astype(int)

    # Map any variant column names safely
    col_map = {
        "picked_title_x": "image_title",
        "thumbnail_x": "thumbnail",
        "caption": "image_caption",
        "credit": "image_credit",
        "match_score": "similarity_score",
        "fullres_url": "image_url",
        "download_path": "image_url",          # fallback if fullres_url missing
        "detail_url": "image_page_url"
    }

    # Only rename if the column exists
    for old, new in col_map.items():
        if old in attrib_df.columns and new not in attrib_df.columns:
            attrib_df = attrib_df.rename(columns={old: new})

    # Ensure missing optional columns are added as empty
    for col in ["image_page_url", "image_url", "license"]:
        if col not in attrib_df.columns:
            attrib_df[col] = ""

    # Select relevant columns safely (intersection of existing + expected)
    expected_cols = [
        "chapter_id", "paragraph_id", "rank", "query", "image_title",
        "image_page_url", "image_url", "image_caption", "image_credit",
        "similarity_score", "license"
    ]
    existing_cols = [c for c in expected_cols if c in attrib_df.columns]
    attrib_df = attrib_df[existing_cols]

    # Merge with paragraph text
    merged = attrib_df.merge(
        chapter_df[["chapter_id", "paragraph_id", "text"]],
        on=["chapter_id", "paragraph_id"],
        how="left",
        indicator=True
    )

    matched = (merged["_merge"] == "both").sum()
    print(f"🔍 Matched {matched}/{len(merged)} rows ({matched/len(merged):.1%})")
    merged = merged.drop(columns=["_merge"])

    # Add review columns
    merged["review_decision"] = ""
    merged["review_notes"] = ""

    # Reorder for clarity
    order = [
        "chapter_id", "paragraph_id", "rank", "text", "query", "image_title",
        "image_page_url", "image_url", "image_caption", "image_credit",
        "similarity_score", "license", "review_decision", "review_notes"
    ]
    merged = merged[[c for c in order if c in merged.columns]]

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    merged.to_csv(out_file, index=False)
    print(f"✅ Saved review table → {out_file}")
    print(f"📊 Total rows: {len(merged)}")
    print("\n📄 Sample rows:")
    print(merged.head(3).to_string(index=False))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate review table for paragraph → images")
    parser.add_argument("--attrib", required=True)
    parser.add_argument("--chapters", default="data/chapters_dataset.csv")
    parser.add_argument("--out", default="data/paragraph_image_review_ready.csv")
    args = parser.parse_args()
    generate_review_table(args.attrib, args.chapters, args.out)
