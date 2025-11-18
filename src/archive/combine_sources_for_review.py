# src/combine_sources_for_review.py
import os, argparse
import pandas as pd

def normalize_from_nih(df):
    # NIH "joined" file columns from your scraper + matcher
    # Rename to review schema
    rename_map = {
        "picked_title_x": "image_title",
        "thumbnail_x": "thumbnail",
        "caption": "image_caption",
        "credit": "image_credit",
        "fullres_url": "image_url",
        "match_score": "similarity_score",
        "detail_url": "detail_url",
        "query": "query",
        "chapter_id": "chapter_id",
        "paragraph_id": "paragraph_id",
        "rank": "rank"
    }
    cols = [c for c in rename_map if c in df.columns]
    out = df[cols].rename(columns=rename_map).copy()
    out["source"] = "nih"
    return out

def normalize_from_wikimedia(df):
    # Already in review schema from the new script
    need = ["chapter_id","paragraph_id","rank","query","image_title",
            "detail_url","image_url","image_caption","image_credit",
            "similarity_score","thumbnail","source","license","license_url"]
    for n in need:
        if n not in df.columns:
            df[n] = "" if n not in ["similarity_score","rank","paragraph_id"] else None
    return df[need].copy()

def main():
    ap = argparse.ArgumentParser(description="Combine NIH + Wikimedia into a single review table.")
    ap.add_argument("--nih", help="NIH joined CSV (data/paragraph_image_attributions_joined.csv)")
    ap.add_argument("--wikimedia", help="Wikimedia matches CSV (data/wikimedia_matches_*.csv)")
    ap.add_argument("--chapters", default="data/chapters_dataset.csv", help="Chapter dataset CSV")
    ap.add_argument("--out", default="data/paragraph_image_review_ready.csv", help="Output review CSV")
    args = ap.parse_args()

    frames = []

    if args.nih and os.path.exists(args.nih):
        nih = pd.read_csv(args.nih)
        frames.append(normalize_from_nih(nih))

    if args.wikimedia and os.path.exists(args.wikimedia):
        wiki = pd.read_csv(args.wikimedia)
        frames.append(normalize_from_wikimedia(wiki))

    if not frames:
        print("⚠️ No valid inputs provided.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # types + clean
    combined["chapter_id"] = combined["chapter_id"].astype(str)
    combined["paragraph_id"] = pd.to_numeric(combined["paragraph_id"], errors="coerce").astype("Int64")
    combined["rank"] = pd.to_numeric(combined["rank"], errors="coerce").astype("Int64")
    combined["similarity_score"] = pd.to_numeric(combined["similarity_score"], errors="coerce")

    # Merge paragraph text
    chapters = pd.read_csv(args.chapters)
    chapters["chapter_id"] = chapters["chapter_id"].astype(str)
    chapters["paragraph_id"] = pd.to_numeric(chapters["paragraph_id"], errors="coerce").astype("Int64")

    merged = combined.merge(
        chapters[["chapter_id","paragraph_id","text"]],
        on=["chapter_id","paragraph_id"],
        how="left"
    )

    # Add review columns
    if "review_decision" not in merged.columns:
        merged["review_decision"] = ""
    if "review_notes" not in merged.columns:
        merged["review_notes"] = ""

    # Order columns
    order = ["source","chapter_id","paragraph_id","rank","text","query","image_title",
             "image_url","image_caption","image_credit","similarity_score","license",
             "license_url","detail_url","thumbnail","review_decision","review_notes"]
    for col in order:
        if col not in merged.columns:
            merged[col] = ""

    merged = merged[order]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(f"✅ Review table saved → {args.out}")
    print(f"📊 Total rows: {len(merged)}")

    # Quick sanity
    ok = merged["text"].notna().sum()
    print(f"🔎 Paragraph text attached for {ok}/{len(merged)} rows ({ok/len(merged):.1%})")

if __name__ == "__main__":
    main()
