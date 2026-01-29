"""
Filter Out NCI Promotional Poster Images
=========================================
Removes poster-like promotional materials that don't fit textbook context
"""
import pandas as pd
import argparse

def is_promotional_poster(title, description):
    """
    Identify NCI promotional/poster images that aren't educational
    
    Returns True if image appears to be promotional material
    """
    title_lower = str(title).lower()
    desc_lower = str(description).lower()
    
    # Title indicators of promotional content
    promotional_title_keywords = [
        'quote',
        'message from dr.',
        'scientific opportunity',
        'factoid',
        'fueling progress',
        'revolutionizing',
        'disrupting',
        'leading progress',
        'ending cancer as we know it',
        'imagine if',
        'investments in',
        'new cases and deaths',
        'cancer deaths',
        'early signage',
        'national cancer plan',
    ]
    
    # Description indicators (budget/policy documents)
    promotional_desc_keywords = [
        'fiscal year 2025',
        'fiscal year 2026',
        'professional judgment budget',
        'leading progress against cancer',
        'screen to save initiative',
        'center to reduce cancer health',
        'this infographic shows',
        '100% lifetime risk',
        '95 percent of',
        '% of all human cancers',
        'have the potential to',
        'has the potential to',
        'would end cancer as we know it',
        'additional investments in',
        'additional funding will',  # NEW: Funding requests
    ]
    
    # Check title
    for keyword in promotional_title_keywords:
        if keyword in title_lower:
            return True
    
    # Check description
    for keyword in promotional_desc_keywords:
        if keyword in desc_lower:
            return True
    
    # Specific patterns for factoids
    if '(factoid)' in title_lower:
        return True
    
    # Pattern: Titles that are just statistics
    title_words = title_lower.split()
    if len(title_words) <= 4 and ('deaths' in title_words or 'cases' in title_words):
        if not title_lower.startswith('what '):
            return True
    
    # Filter out lab equipment photos
    if 'photo taken at' in desc_lower or 'lab technician' in desc_lower:
        return True
    
    # Filter out pedigree charts
    if 'classic' in title_lower and 'pedigree' in title_lower:
        return True
    
    # Filter out cancer risk infographics
    if 'cancer risk' in title_lower and ('lifetime risk' in desc_lower or '100%' in desc_lower):
        return True
    
    return False

def filter_promotional_images(input_csv, output_csv):
    """
    Remove promotional poster images from results
    """
    df = pd.read_csv(input_csv)
    
    print(f'\n📊 Original images: {len(df)}')
    
    # Identify promotional images
    df['is_promotional'] = df.apply(
        lambda row: is_promotional_poster(row['Title'], row['Description']),
        axis=1
    )
    
    promotional_count = df['is_promotional'].sum()
    
    # Filter out promotional
    df_filtered = df[df['is_promotional'] == False].copy()
    df_filtered = df_filtered.drop('is_promotional', axis=1)
    
    # Save
    df_filtered.to_csv(output_csv, index=False)
    
    print(f'🚫 Promotional images removed: {promotional_count}')
    print(f'✅ Educational images kept: {len(df_filtered)}')
    print(f'\n📁 Saved to: {output_csv}')
    
    # Show what was removed
    print('\n🗑️  REMOVED (Promotional/Poster Images):')
    promotional_images = df[df['is_promotional'] == True]
    for idx, row in promotional_images.iterrows():
        print(f'  - {row["image_id"]}: {row["Title"][:60]}')
    
    return df_filtered

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter out promotional poster images")
    parser.add_argument('--input', required=True, help='Input CSV file path')
    parser.add_argument('--output', required=True, help='Output CSV file path')
    
    args = parser.parse_args()
    
    filter_promotional_images(args.input, args.output)