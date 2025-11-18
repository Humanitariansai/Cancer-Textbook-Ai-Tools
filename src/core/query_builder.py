# src/query_builder.py
import argparse
import pandas as pd
import sys
import os
import re
from collections import Counter

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

def clean_and_extract_keywords(text, max_terms=10):
    """Extract top frequent meaningful words from the text."""
    stop = {
        "the","and","of","to","a","in","is","on","for","with","by","as","that","this",
        "from","an","or","at","be","are","it","we","was","were","but","about","into",
        "over","without","figure","chapter","introduction","section","system","systems",
        "cells","cell","study","shown","figure","fig","data"
    }
    words = re.findall(r"[A-Za-z]+", text.lower())
    words = [w for w in words if w not in stop and len(w) > 3]
    common = [w for w, _ in Counter(words).most_common(max_terms)]
    return " ".join(common)

def main(chapter_id, short_mode=False):
    try:
        df = pd.read_csv(DATA_FILE)
        df_chapter = df[df["chapter_id"].astype(str) == str(chapter_id)]
        if df_chapter.empty:
            print(f"⚠️ No data found for Chapter {chapter_id}")
            return

        # Join all paragraphs
        full_text = " ".join(df_chapter["text"].tolist())

        # If short mode, generate keyword query
        query_text = (
            clean_and_extract_keywords(full_text, max_terms=12)
            if short_mode else full_text
        )

        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_QUERY_FILE, "w", encoding="utf-8") as f:
            f.write(query_text)

        mode_str = "short keyword query" if short_mode else "full text"
        print(f"✅ Saved Chapter {chapter_id} {mode_str} → {OUTPUT_QUERY_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=str, help="Chapter ID to search")
    parser.add_argument("--short", action="store_true", help="Generate short keyword query")
    args = parser.parse_args()

    if not args.chapter:
        list_available_chapters()
        sys.exit(0)

    main(args.chapter, short_mode=args.short)
