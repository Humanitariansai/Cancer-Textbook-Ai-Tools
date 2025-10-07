# src/query_builder.py
import argparse
import pandas as pd
import sys
import os

DATA_FILE = "data/chapters_dataset.csv"
OUTPUT_QUERY_FILE = "data/query_text.txt"

def list_available_chapters():
    """List unique chapter IDs from the dataset"""
    try:
        df = pd.read_csv(DATA_FILE)
        chapters = sorted(df["chapter_id"].unique())
        print("\n📖 Available chapters in dataset:")
        for ch in chapters:
            print(f" - {ch}")
        print("\n👉 Run with: python src/query_builder.py --chapter <chapter_id>")
    except Exception as e:
        print(f"❌ Could not read dataset: {e}")

def main(chapter_id):
    try:
        df = pd.read_csv(DATA_FILE)
        df_chapter = df[df["chapter_id"].astype(str) == str(chapter_id)]
        if df_chapter.empty:
            print(f"⚠️ No data found for Chapter {chapter_id}")
            return

        # Join all paragraphs into one text
        full_text = " ".join(df_chapter["text"].tolist())

        # Save it for the next step
        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_QUERY_FILE, "w", encoding="utf-8") as f:
            f.write(full_text)

        print(f"✅ Saved Chapter {chapter_id} text ({len(df_chapter)} paragraphs) → {OUTPUT_QUERY_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=str, help="Chapter ID to search")
    args = parser.parse_args()

    if not args.chapter:
        list_available_chapters()
        sys.exit(0)

    main(args.chapter)
