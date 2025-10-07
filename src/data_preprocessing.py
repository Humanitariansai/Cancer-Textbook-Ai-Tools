import os
import pandas as pd

CHAPTERS_DIR = "data/chapters"
OUTPUT_FILE = "data/chapters_dataset.csv"

def preprocess_chapters():
    data = []
    for fname in os.listdir(CHAPTERS_DIR):
        if fname.endswith(".md") or fname.endswith(".txt"):
            parts = fname.split()
            chapter_id = parts[1] if len(parts) > 1 else fname
            with open(os.path.join(CHAPTERS_DIR, fname), "r", encoding="utf-8") as f:
                text = f.read().strip()
            paragraphs = text.split("\n\n")
            for pid, para in enumerate(paragraphs, 1):
                if para.strip():
                    data.append({
                        "chapter_id": chapter_id,
                        "paragraph_id": pid,
                        "text": para.strip()
                    })
    df = pd.DataFrame(data)
    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Saved {len(df)} paragraphs → {OUTPUT_FILE}")
    return df

if __name__ == "__main__":
    preprocess_chapters()
