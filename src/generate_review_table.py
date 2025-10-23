import pandas as pd
import os

def generate_review_table(attrib_file, chapter_file, out_file):
    # Load matched images + attribution file
    attrib_df = pd.read_csv(attrib_file)
    chapter_df = pd.read_csv(chapter_file)

    # Normalize and fix data types
    attrib_df["chapter_id"] = attrib_df["chapter_id"].astype(str).str.strip()
    chapter_df["chapter_id"] = chapter_df["chapter_id"].astype(str).str.strip()

    attrib_df["paragraph_id"] = attrib_df["paragraph_id"].astype(float).astype(int)
    chapter_df["paragraph_id"] = chapter_df["paragraph_id"].astype(float).astype(int)

    # Rename for clarity
    attrib_df = attrib_df.rename(columns={
        "picked_title_x": "image_title",
        "thumbnail_x": "thumbnail",
        "caption": "image_caption",
        "credit": "image_credit",
        "fullres_url": "image_url",
        "match_score": "similarity_score"
    })

    # Select relevant fields
    attrib_df = attrib_df[[
        "chapter_id", "paragraph_id", "rank", "query", "image_title",
        "detail_url", "image_url", "image_caption", "image_credit", "similarity_score"
    ]]

    # Merge with paragraph text
    merged = attrib_df.merge(
        chapter_df[["chapter_id", "paragraph_id", "text"]],
        on=["chapter_id", "paragraph_id"],
        how="left",
        indicator=True
    )

    matched = (merged["_merge"] == "both").sum()
    total = len(merged)
    print(f"🔍 Matched {matched} of {total} rows with paragraph text ({matched/total:.1%} success rate)")
    merged = merged.drop(columns=["_merge"])

    # Add human review fields
    merged["review_decision"] = ""
    merged["review_notes"] = ""

    # Reorder for clarity
    merged = merged[[
        "chapter_id", "paragraph_id", "rank", "text", "query", "image_title",
        "image_url", "image_caption", "image_credit", "similarity_score",
        "review_decision", "review_notes"
    ]]

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    merged.to_csv(out_file, index=False)
    print(f"✅ Review table saved to → {out_file}")
    print(f"📊 Total rows: {len(merged)}")

    # ✅ Safe inline preview after save
    print("\n📄 Sample of merged rows (top 3):")
    print(merged[["paragraph_id", "text", "image_title", "similarity_score"]]
          .head(3)
          .to_string(index=False))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate review table for paragraph → images")
    parser.add_argument("--attrib", required=True)
    parser.add_argument("--chapters", default="data/chapters_dataset.csv")
    parser.add_argument("--out", default="data/paragraph_image_review_ready.csv")
    args = parser.parse_args()
    generate_review_table(args.attrib, args.chapters, args.out)
