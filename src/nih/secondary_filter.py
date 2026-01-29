"""
Rule-Based Secondary Filter - Keywords as Filter (Not Penalty)
===============================================================
Filters semantic matches using keyword verification as pass/fail filter.
Preserves high semantic scores instead of penalizing them.
"""

import pandas as pd
import re
from collections import Counter
import os

def extract_key_terms(text, top_n=10):
    """
    Extract most important terms from subsection text
    """
    # Common stop words
    stop_words = {
        'the', 'and', 'of', 'to', 'a', 'in', 'is', 'that', 'for', 'with',
        'as', 'on', 'by', 'this', 'are', 'from', 'or', 'an', 'be', 'at',
        'cancer', 'cells', 'cell', 'tumor', 'can', 'may', 'also', 'been',
        'these', 'their', 'which', 'been', 'has', 'have', 'into', 'such',
        'what', 'how', 'when', 'where', 'why', 'who'
    }
    
    # Extract words
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    
    # Filter stop words
    filtered = [w for w in words if w not in stop_words]
    
    # Get most frequent
    word_counts = Counter(filtered)
    key_terms = [word for word, count in word_counts.most_common(top_n)]
    
    return key_terms

def count_keyword_matches(key_terms, image_title, image_description):
    """
    Count how many key terms appear in image metadata
    Returns INTEGER count, not a score
    """
    title_lower = image_title.lower()
    desc_lower = image_description.lower()
    
    match_count = 0
    
    for term in key_terms:
        # Handle singular/plural
        term_root = re.sub(r'(s|es|ing|ed)$', '', term)
        
        # Check if term appears anywhere
        if term in title_lower or term_root in title_lower or term in desc_lower or term_root in desc_lower:
            match_count += 1
    
    return match_count

def has_title_relevance(subsection_name, image_title):
    """
    Check if image title has strong relevance to subsection
    Returns True/False
    """
    subsection_lower = subsection_name.lower()
    title_lower = image_title.lower()
    
    # Extract key concepts from subsection name
    subsection_concepts = re.sub(r'^\d+\.[\d.]*\s*', '', subsection_lower)
    concepts = subsection_concepts.split()
    
    # Count meaningful concept matches (words longer than 4 chars)
    matches = sum(1 for concept in concepts if len(concept) > 4 and concept in title_lower)
    
    # Strong match if 2+ concepts appear in title
    return matches >= 2

def classify_image_type(title, description):
    """
    Classify image type based on keywords in metadata
    Returns: 'diagram', 'microscopy', 'clinical', 'other'
    """
    text = (title + " " + description).lower()
    
    # Diagram/Illustration indicators
    if any(term in text for term in ['illustration', 'diagram', 'infographic', 'schematic', 'graphic', 'chart', 'pathway']):
        return 'diagram'
    
    # Microscopy indicators
    if any(term in text for term in ['microscopy', 'microscope', 'microscopic', 'confocal', 'fluorescence', 'stain', 'stained']):
        return 'microscopy'
    
    # Clinical indicators
    if any(term in text for term in ['patient', 'biopsy', 'stage', 'grade', 'clinical', 'specimen']):
        return 'clinical'
    
    return 'other'

def apply_secondary_filter(input_csv, output_csv, min_semantic_score=0.50, min_keyword_matches=1):
    """
    Apply rule-based secondary filtering
    Keywords act as FILTER not PENALTY - preserves high semantic scores
    
    Args:
        input_csv: Semantic matching results
        output_csv: Filtered output
        min_semantic_score: Minimum semantic score (default: 0.50)
        min_keyword_matches: Minimum keyword matches required (default: 1)
    """
    
    df = pd.read_csv(input_csv)
    
    print("\n" + "=" * 70)
    print("🔬 SECONDARY FILTERING (Keywords as Filter)")
    print("=" * 70)
    print(f"Input images: {len(df)}")
    print(f"Min semantic score: {min_semantic_score}")
    print(f"Min keyword matches: {min_keyword_matches}")
    print("=" * 70 + "\n")
    
    # Process each row
    results = []
    
    for idx, row in df.iterrows():
        subsection_text = row['query']
        subsection_name = row['subsection_name']
        image_title = str(row['Title'])
        image_desc = str(row['Description'])
        semantic_score = float(row['match_score'])
        
        # Extract key terms from subsection
        key_terms = extract_key_terms(subsection_text, top_n=10)
        
        # Count how many keywords match (not a score, just count)
        keyword_matches = count_keyword_matches(key_terms, image_title, image_desc)
        
        # Classify image type
        image_type = classify_image_type(image_title, image_desc)
        
        # Check title relevance
        title_match = has_title_relevance(subsection_name, image_title)
        
        # FILTERING LOGIC: Use keywords as pass/fail
        # Pass if: (semantic >= threshold) AND (has keyword matches OR title match)
        passes_keyword_filter = (keyword_matches >= min_keyword_matches) or title_match
        
        # Final score is just semantic score (no penalty!)
        final_score = semantic_score
        
        # Store result
        results.append({
            **row.to_dict(),
            'keyword_matches': keyword_matches,
            'has_title_match': title_match,
            'passes_keyword_filter': passes_keyword_filter,
            'image_type': image_type,
            'final_score': round(final_score, 3),
            'key_terms': ', '.join(key_terms[:5])
        })
    
    df_scored = pd.DataFrame(results)
    
    # Filter: semantic score AND keyword filter
    df_filtered = df_scored[(df_scored['match_score'] >= min_semantic_score) & (df_scored['passes_keyword_filter'] == True)].copy()
    
    # Sort by semantic score (best first)
    df_filtered = df_filtered.sort_values(['subsection_id', 'final_score'], ascending=[True, False])
    
    # Save
    os.makedirs(os.path.dirname(output_csv) if os.path.dirname(output_csv) else '.', exist_ok=True)
    df_filtered.to_csv(output_csv, index=False)
    
    # Statistics
    print("=" * 70)
    print("📊 FILTERING RESULTS")
    print("=" * 70)
    print(f"Original images: {len(df)}")
    print(f"After secondary filter: {len(df_filtered)} ({len(df_filtered)/len(df)*100:.1f}%)")
    print(f"Removed: {len(df) - len(df_filtered)}")
    print(f"\nFiltering breakdown:")
    print(f"  Passed semantic threshold (≥{min_semantic_score}): {len(df[df['match_score'] >= min_semantic_score])}")
    print(f"  Passed keyword filter: {len(df_scored[df_scored['passes_keyword_filter']])}")
    print(f"  Passed BOTH: {len(df_filtered)}")
    print(f"\nScore range:")
    print(f"  Avg semantic score: {df_filtered['match_score'].mean():.3f}")
    print(f"  Min semantic score: {df_filtered['match_score'].min():.3f}")
    print(f"  Max semantic score: {df_filtered['match_score'].max():.3f}")
    print(f"\nKeyword matches distribution:")
    print(df_filtered['keyword_matches'].value_counts().sort_index())
    print(f"\nImage type distribution:")
    print(df_filtered['image_type'].value_counts())
    print(f"\n📁 Saved to: {output_csv}")
    print("=" * 70 + "\n")
    
    return df_filtered

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply rule-based secondary filtering (keywords as filter)")
    parser.add_argument('--input', required=True, help='Input CSV with semantic matches')
    parser.add_argument('--output', required=True, help='Output CSV with secondary filtering applied')
    parser.add_argument('--min-score', type=float, default=0.50, help='Minimum semantic score (default: 0.50)')
    parser.add_argument('--min-keywords', type=int, default=1, help='Minimum keyword matches required (default: 1)')
    
    args = parser.parse_args()
    
    apply_secondary_filter(args.input, args.output, args.min_score, args.min_keywords)

if __name__ == "__main__":
    main()
