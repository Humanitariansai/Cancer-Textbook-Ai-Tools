"""
Content filtering + license validation layer.
Keeps only Public Domain / CC BY / CC BY-SA images,
and applies a semantic similarity threshold.
"""

import pandas as pd
import os

# Accepted license categories
ALLOWED_LICENSES = ["Public Domain", "CC BY", "CC BY-SA"]

def normalize_license(text: str) -> str:
    """Standardize license text into known formats."""
    if pd.isna(text):
        return "Unknown"
    text = str(text).strip().lower()

    if "public" in text and "domain" in text:
        return "Public Domain"
    if "cc" in text and "by-sa" in text:
        return "CC BY-SA"
    if "cc" in text and "by" in text:
        return "CC BY"
    return text.title()

def filter_dataset(input_csv: str, output_csv: str, min_score: float = 0.6) -> pd.DataFrame:
    """Filter images by license type and semantic score."""
    df = pd.read_csv(input_csv)

    # Normalize license text
    df["license_type"] = df["image_credit"].apply(normalize_license)

    # Apply filters
    allowed = df[
        (df["license_type"].isin(ALLOWED_LICENSES)) &
        (df["similarity_score"].fillna(0) >= min_score)
    ].copy()

    # Save filtered dataset
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    allowed.to_csv(output_csv, index=False)

    kept = len(allowed)
    total = len(df)
    dropped = total - kept
    print(f"✅ Filtered dataset saved → {output_csv}")
    print(f"📊 Kept {kept}/{total} images ({kept/total:.1%}), dropped {dropped} non-compliant entries.")
    print(f"🎯 License types kept: {sorted(set(allowed['license_type']))}")

    return allowed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Filter images by license and similarity score.")
    parser.add_argument("--input", required=True, help="Input attribution-joined CSV file")
    parser.add_argument("--out", default="data/paragraph_image_filtered.csv", help="Output filtered CSV path")
    parser.add_argument("--min-score", type=float, default=0.6, help="Minimum similarity score to keep")
    args = parser.parse_args()

    filter_dataset(args.input, args.out, args.min_score)
