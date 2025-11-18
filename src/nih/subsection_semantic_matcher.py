"""
Subsection → NIH Image Matcher with Semantic Ranking
=====================================================
Uses subsection summaries + semantic similarity (MiniLM) to find best images

Features:
- Uses subsection queries instead of paragraphs
- Pre-computes NIH image embeddings (one-time)
- Calculates semantic similarity (match_score)
- Keeps only images with match_score ≥ threshold (e.g., 0.7)
- Smart deduplication across subsections

Usage:
    # Step 1: Create NIH image embeddings (one-time)
    python subsection_semantic_matcher.py --create-embeddings
    
    # Step 2: Match subsections to images
    python subsection_semantic_matcher.py --chapter 14 --min-score 0.7 --topk 10
"""

import os
import re
import pandas as pd
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
import argparse
import pickle

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def create_nih_embeddings(metadata_csv, embeddings_file):
    """
    Create and save embeddings for all NIH images (one-time setup)
    
    Args:
        metadata_csv: CSV with NIH image metadata (from attribution scraper)
        embeddings_file: Where to save the embeddings
    """
    
    print("\n" + "=" * 70)
    print("🧠 CREATING NIH IMAGE EMBEDDINGS (One-time setup)")
    print("=" * 70)
    
    # Load NIH metadata
    df = pd.read_csv(metadata_csv)
    
    print(f"Loaded {len(df)} NIH images")
    print(f"Model: {MODEL_NAME}")
    
    # Combine title + description for richer context
    df['combined_text'] = (
        df['Title'].fillna('') + '. ' + df['Description'].fillna('')
    )
    
    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    model = SentenceTransformer(MODEL_NAME, device=device)
    
    # Generate embeddings
    print("\n⚙️ Generating embeddings...")
    embeddings = model.encode(
        df['combined_text'].tolist(),
        convert_to_tensor=True,
        show_progress_bar=True,
        batch_size=32
    )
    
    # Save embeddings and metadata
    data = {
        'image_ids': df['image_id'].tolist(),
        'titles': df['Title'].tolist(),
        'descriptions': df['Description'].tolist(),
        'detail_urls': df['detail_url'].tolist() if 'detail_url' in df.columns else df['Source'].tolist(),
        'thumbnails': df['thumbnail'].tolist() if 'thumbnail' in df.columns else [''] * len(df),
        'credits': df['Credit'].tolist(),
        'licenses': df['License'].tolist(),
        'embeddings': embeddings.cpu()
    }
    
    os.makedirs(os.path.dirname(embeddings_file), exist_ok=True)
    with open(embeddings_file, 'wb') as f:
        pickle.dump(data, f)
    
    print(f"\n✅ Saved embeddings for {len(df)} images to: {embeddings_file}")
    print("=" * 70 + "\n")

def match_subsections_to_images(
    subsection_csv,
    embeddings_file,
    output_csv,
    min_score=0.7,
    topk=10
):
    """
    Match subsections to NIH images using semantic similarity
    
    Args:
        subsection_csv: CSV with subsection queries
        embeddings_file: Pre-computed NIH embeddings
        output_csv: Output file with matches
        min_score: Minimum similarity threshold
        topk: Maximum images per subsection
    """
    
    print("\n" + "=" * 70)
    print("🔗 SEMANTIC MATCHING: Subsections → NIH Images")
    print("=" * 70)
    
    # Load subsection queries
    subsections_df = pd.read_csv(subsection_csv)
    print(f"Subsections: {len(subsections_df)}")
    
    # Load NIH embeddings
    print(f"Loading embeddings from: {embeddings_file}")
    with open(embeddings_file, 'rb') as f:
        nih_data = pickle.load(f)
    
    print(f"NIH images: {len(nih_data['image_ids'])}")
    print(f"Min score threshold: {min_score}")
    print(f"Top-K per subsection: {topk}")
    print("=" * 70 + "\n")
    
    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)
    
    # Get NIH embeddings
    nih_embeddings = nih_data['embeddings'].to(device)
    
    # Match each subsection
    all_matches = []
    global_best = {}  # Track best score for each image globally
    
    for idx, row in tqdm(subsections_df.iterrows(), total=len(subsections_df), desc="Matching subsections"):
        chapter_id = row['chapter_id']
        subsection_id = row['subsection_id']
        subsection_name = row['subsection_name']
        query_text = row['query_final']
        
        # Generate embedding for this subsection
        subsection_emb = model.encode(query_text, convert_to_tensor=True)
        
        # Calculate similarities
        similarities = util.cos_sim(subsection_emb, nih_embeddings)[0]
        
        # Get top matches
        top_results = torch.topk(similarities, k=min(topk * 2, len(similarities)))  # Get extra for filtering
        
        # Process matches
        subsection_matches = []
        for score, img_idx in zip(top_results.values, top_results.indices):
            score_val = float(score)
            
            # Skip if below threshold
            if score_val < min_score:
                continue
            
            img_idx = int(img_idx)
            image_id = nih_data['image_ids'][img_idx]
            
            # Deduplication: check if we've seen this image with better score
            if image_id in global_best and score_val < global_best[image_id] + 0.05:
                continue
            
            match = {
                'chapter_id': chapter_id,
                'subsection_id': subsection_id,
                'subsection_name': subsection_name,
                'query': query_text[:500],
                'picked_title': nih_data['titles'][img_idx],
                'detail_url': nih_data['detail_urls'][img_idx],
                'thumbnail': nih_data['thumbnails'][img_idx],
                'image_id': image_id,
                'match_score': round(score_val, 4),
                'candidate_count': len(nih_data['image_ids']),
                'rank': len(subsection_matches) + 1
            }
            
            subsection_matches.append(match)
            global_best[image_id] = score_val
            
            # Stop when we have enough
            if len(subsection_matches) >= topk:
                break
        
        all_matches.extend(subsection_matches)
    
    # Save results
    df_matches = pd.DataFrame(all_matches)
    
    if len(df_matches) == 0:
        print("\n⚠️ No matches found! Try lowering --min-score")
        return
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_matches.to_csv(output_csv, index=False)
    
    print("\n" + "=" * 70)
    print("✅ MATCHING COMPLETE")
    print("=" * 70)
    print(f"Total matches: {len(df_matches)}")
    print(f"Unique images: {df_matches['image_id'].nunique()}")
    print(f"Average score: {df_matches['match_score'].mean():.3f}")
    print(f"Score range: {df_matches['match_score'].min():.3f} - {df_matches['match_score'].max():.3f}")
    print(f"\n📁 Saved to: {output_csv}")
    
    # Show distribution
    print("\n📊 Matches per subsection:")
    subsection_counts = df_matches.groupby(['subsection_id', 'subsection_name']).size()
    for (sub_id, sub_name), count in subsection_counts.items():
        avg_score = df_matches[df_matches['subsection_id'] == sub_id]['match_score'].mean()
        print(f"  {sub_id}. {sub_name[:50]}: {count} images (avg score: {avg_score:.3f})")
    
    print("=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Subsection semantic matcher for NIH images"
    )
    parser.add_argument(
        '--create-embeddings',
        action='store_true',
        help='Create NIH image embeddings (run once)'
    )
    parser.add_argument(
        '--metadata-csv',
        default='data/extracted_metadata.csv',
        help='NIH metadata CSV (for creating embeddings)'
    )
    parser.add_argument(
        '--embeddings-file',
        default='data/nih_image_embeddings.pkl',
        help='Where to save/load embeddings'
    )
    parser.add_argument(
        '--chapter',
        type=str,
        help='Chapter ID to process'
    )
    parser.add_argument(
        '--subsection-csv',
        help='Subsection queries CSV (auto-detected if not provided)'
    )
    parser.add_argument(
        '--output',
        help='Output CSV (auto-generated if not provided)'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.7,
        help='Minimum similarity score (default: 0.7)'
    )
    parser.add_argument(
        '--topk',
        type=int,
        default=10,
        help='Max images per subsection (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Mode 1: Create embeddings
    if args.create_embeddings:
        create_nih_embeddings(args.metadata_csv, args.embeddings_file)
        return
    
    # Mode 2: Match subsections
    if not args.chapter:
        print("❌ Please specify --chapter or --create-embeddings")
        print("\nExamples:")
        print("  # Create embeddings (run once)")
        print("  python subsection_semantic_matcher.py --create-embeddings")
        print("\n  # Match subsections")
        print("  python subsection_semantic_matcher.py --chapter 14 --min-score 0.7")
        return
    
    # Auto-detect files
    if not args.subsection_csv:
        args.subsection_csv = f"data/subsection_queries_chapter_{args.chapter}.csv"
    
    if not args.output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"data/subsection_image_map_semantic_{args.chapter}_{timestamp}.csv"
    
    # Check if embeddings exist
    if not os.path.exists(args.embeddings_file):
        print(f"❌ Embeddings not found: {args.embeddings_file}")
        print("\nRun this first:")
        print(f"  python subsection_semantic_matcher.py --create-embeddings")
        return
    
    # Run matching
    match_subsections_to_images(
        args.subsection_csv,
        args.embeddings_file,
        args.output,
        args.min_score,
        args.topk
    )

if __name__ == "__main__":
    main()