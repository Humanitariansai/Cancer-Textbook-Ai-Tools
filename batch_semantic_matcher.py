import sys
sys.path.append('src')
from nih.subsection_semantic_matcher import process_chapter

# Load model once
print("Loading embedding model (this takes time)...")

# Process chapters
chapters = [3, 4, 5, 7, 8, 9, 10]  # Batch 1

for ch in chapters:
    print(f"\n{'='*60}")
    print(f"Processing Chapter {ch}")
    print('='*60)
    try:
        process_chapter(ch, threshold=0.50)
        print(f"✅ Chapter {ch} complete")
    except Exception as e:
        print(f"❌ Chapter {ch} failed: {e}")

print("\n✅ Batch 1 complete!")
