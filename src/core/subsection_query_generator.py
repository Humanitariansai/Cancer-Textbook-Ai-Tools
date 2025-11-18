"""
Subsection-Based Query Generator
=================================
Instead of searching per paragraph, this groups paragraphs by subsection,
generates a summary for each subsection, and uses that for image search.

This creates more relevant, "elastic" queries rather than rigid paragraph-by-paragraph searches.
"""

import pandas as pd
import os
import re
from collections import defaultdict

def extract_subsection_headers(text):
    """
    Extract subsection headers from markdown text.
    Looks for lines starting with ## or ### (markdown headers)
    """
    lines = text.split('\n')
    headers = []
    
    for i, line in enumerate(lines):
        # Match markdown headers (## or ###)
        if re.match(r'^#{2,3}\s+', line):
            header = re.sub(r'^#{2,3}\s+', '', line).strip()
            headers.append((i, header))
    
    return headers

def group_paragraphs_by_subsection(chapter_file):
    """
    Read chapter file and group paragraphs by subsection headers.
    
    Returns:
        List of dicts with {'subsection': header, 'paragraphs': [list of paragraphs]}
    """
    with open(chapter_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    subsections = []
    current_subsection = {'subsection': 'Introduction', 'paragraphs': []}
    current_paragraph = []
    skip_next_line = False  # To skip figure descriptions
    
    for i, line in enumerate(lines):
        # Skip figure descriptions and image tags
        if 'Figure' in line and ':' in line:
            skip_next_line = True
            continue
        if skip_next_line and (line.startswith('Source:') or line.startswith('Creator:') or '<img' in line or '<div' in line):
            if 'Source:' in line or 'Creator:' in line:
                skip_next_line = False
            continue
        skip_next_line = False
        
        # Skip lines with HTML/markdown images
        if '<img' in line or '<div' in line or '</div>' in line:
            continue
            
        # Check if it's a subsection header (# or ##)
        if re.match(r'^#{1,4}\s+', line):
            # Save previous paragraph if exists
            if current_paragraph:
                para_text = '\n'.join(current_paragraph).strip()
                if para_text and len(para_text) > 50:  # Only keep substantial paragraphs
                    current_subsection['paragraphs'].append(para_text)
                current_paragraph = []
            
            # Save previous subsection if has content
            if current_subsection['paragraphs']:
                subsections.append(current_subsection)
            
            # Start new subsection
            header = re.sub(r'^#{1,4}\s+', '', line).strip()
            current_subsection = {'subsection': header, 'paragraphs': []}
        
        elif line.strip():  # Non-empty line
            current_paragraph.append(line)
        
        elif current_paragraph:  # Empty line - end of paragraph
            para_text = '\n'.join(current_paragraph).strip()
            if para_text and len(para_text) > 50:  # Only keep substantial paragraphs
                current_subsection['paragraphs'].append(para_text)
            current_paragraph = []
    
    # Don't forget the last paragraph and subsection
    if current_paragraph:
        para_text = '\n'.join(current_paragraph).strip()
        if para_text and len(para_text) > 50:
            current_subsection['paragraphs'].append(para_text)
    
    if current_subsection['paragraphs']:
        subsections.append(current_subsection)
    
    return subsections

def clean_text(text):
    """
    Clean markdown and HTML from text
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def generate_extractive_summary(paragraphs, max_sentences=5):
    """
    Generate an extractive summary by selecting the most important sentences.
    Simple approach: Take first sentence of each paragraph + key sentences.
    """
    summary_sentences = []
    
    for para in paragraphs:
        # Clean the paragraph first
        para = clean_text(para)
        
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', para)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
        
        if sentences:
            # Take first sentence of each paragraph (usually most important)
            summary_sentences.append(sentences[0])
    
    # Limit to max_sentences
    summary = '. '.join(summary_sentences[:max_sentences])
    
    # Clean up and ensure it ends with period
    summary = re.sub(r'\s+', ' ', summary).strip()
    if summary and not summary.endswith('.'):
        summary += '.'
    
    return summary

def generate_keyword_summary(paragraphs, max_keywords=15):
    """
    Generate a keyword-based summary by extracting most frequent meaningful terms.
    """
    from collections import Counter
    
    # Stop words to exclude
    stop_words = {
        'the', 'and', 'of', 'to', 'a', 'in', 'is', 'on', 'for', 'with', 'by', 
        'as', 'that', 'this', 'from', 'an', 'or', 'at', 'be', 'are', 'it', 
        'we', 'was', 'were', 'but', 'about', 'into', 'over', 'without'
    }
    
    # Combine all paragraphs and clean
    text = ' '.join(paragraphs)
    text = clean_text(text).lower()
    
    # Extract words
    words = re.findall(r'\b[a-z]{4,}\b', text)
    
    # Filter stop words
    words = [w for w in words if w not in stop_words]
    
    # Get most common keywords
    word_counts = Counter(words)
    top_keywords = [word for word, count in word_counts.most_common(max_keywords)]
    
    return ' '.join(top_keywords)

def process_chapter(chapter_id, chapters_dir='data/chapters', output_dir='data'):
    """
    Process a single chapter: extract subsections and generate queries.
    
    Returns:
        DataFrame with subsection-based queries
    """
    # Find chapter file
    chapter_files = [f for f in os.listdir(chapters_dir) if chapter_id in f]
    
    if not chapter_files:
        raise FileNotFoundError(f"Chapter {chapter_id} not found in {chapters_dir}")
    
    chapter_file = os.path.join(chapters_dir, chapter_files[0])
    
    print(f"Processing: {chapter_file}")
    
    # Group by subsections
    subsections = group_paragraphs_by_subsection(chapter_file)
    
    print(f"Found {len(subsections)} subsections")
    
    # Generate queries for each subsection
    queries_data = []
    
    for i, subsection in enumerate(subsections, 1):
        subsection_name = subsection['subsection']
        paragraphs = subsection['paragraphs']
        
        # Generate both extractive and keyword summaries
        extractive_summary = generate_extractive_summary(paragraphs, max_sentences=5)
        keyword_summary = generate_keyword_summary(paragraphs, max_keywords=15)
        
        # Combine for a hybrid query (extractive is usually better)
        query = extractive_summary
        
        queries_data.append({
            'chapter_id': chapter_id,
            'subsection_id': i,
            'subsection_name': subsection_name,
            'num_paragraphs': len(paragraphs),
            'query_extractive': extractive_summary,
            'query_keywords': keyword_summary,
            'query_final': query,
            'full_text': '\n\n'.join(paragraphs)
        })
        
        print(f"  Subsection {i}: {subsection_name} ({len(paragraphs)} paragraphs)")
        print(f"    Query: {query[:100]}...")
    
    df = pd.DataFrame(queries_data)
    
    # Save to CSV
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'subsection_queries_chapter_{chapter_id}.csv')
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Saved queries to: {output_file}")
    
    return df

def process_all_chapters(chapters_dir='data/chapters', output_dir='data'):
    """
    Process all chapters in the directory.
    """
    chapter_files = [f for f in os.listdir(chapters_dir) 
                     if f.endswith('.md') or f.endswith('.txt')]
    
    all_queries = []
    
    for chapter_file in sorted(chapter_files):
        # Extract chapter ID from filename
        parts = chapter_file.split()
        chapter_id = parts[1] if len(parts) > 1 else chapter_file.replace('.md', '').replace('.txt', '')
        
        print(f"\n{'='*70}")
        print(f"Processing Chapter {chapter_id}")
        print('='*70)
        
        try:
            df = process_chapter(chapter_id, chapters_dir, output_dir)
            all_queries.append(df)
        except Exception as e:
            print(f"❌ Error processing chapter {chapter_id}: {e}")
    
    # Combine all chapters
    if all_queries:
        combined_df = pd.concat(all_queries, ignore_index=True)
        combined_output = os.path.join(output_dir, 'subsection_queries_all_chapters.csv')
        combined_df.to_csv(combined_output, index=False)
        
        print(f"\n{'='*70}")
        print(f"✅ Combined queries saved to: {combined_output}")
        print(f"Total subsections: {len(combined_df)}")
        print('='*70)
        
        return combined_df
    
    return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate subsection-based queries for image search"
    )
    parser.add_argument(
        '--chapter',
        type=str,
        help='Specific chapter ID to process (e.g., "14")'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all chapters'
    )
    parser.add_argument(
        '--chapters-dir',
        default='data/chapters',
        help='Directory containing chapter markdown files'
    )
    parser.add_argument(
        '--output-dir',
        default='data',
        help='Output directory for query CSV files'
    )
    
    args = parser.parse_args()
    
    if args.chapter:
        df = process_chapter(args.chapter, args.chapters_dir, args.output_dir)
        
        print(f"\n📊 Generated {len(df)} subsection queries")
        print("\nSample queries:")
        print(df[['subsection_name', 'query_final']].head(3).to_string(index=False))
        
    elif args.all:
        df = process_all_chapters(args.chapters_dir, args.output_dir)
        
    else:
        print("❌ Please specify --chapter <id> or --all")
        print("Example: python subsection_query_generator.py --chapter 14")

if __name__ == "__main__":
    main()