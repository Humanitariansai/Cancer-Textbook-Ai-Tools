import pandas as pd
import os

def generate_attribution_text(row):
    """
    Generate proper attribution text for an image
    
    Returns a formatted string with:
    - Title
    - Credit/Creator
    - License information
    - Source URL
    """
    
    title = row.get('Title', 'Unknown')
    credit = row.get('Credit', 'Unknown')
    license_text = row.get('License', '')
    source = row.get('Source', '')
    image_id = row.get('image_id') or row.get('Image ID', '')
    
    # Build attribution text
    attribution_parts = []
    
    # Title
    if title and title != 'Unknown':
        attribution_parts.append(f'"{title}"')
    
    # Credit
    if credit and credit != 'Unknown' and credit.lower() != 'nan':
        attribution_parts.append(f"Credit: {credit}")
    
    # License summary
    if 'public domain' in license_text.lower():
        attribution_parts.append("License: Public Domain")
    elif 'cc-by' in license_text.lower() or 'creative commons' in license_text.lower():
        attribution_parts.append("License: Creative Commons")
    
    # Source link
    if source:
        attribution_parts.append(f"Source: {source}")
    
    return " | ".join(attribution_parts)

def generate_caption_text(row):
    """
    Generate a caption for use in the textbook
    Shorter version for figure captions
    """
    title = row.get('Title', '')
    credit = row.get('Credit', '')
    
    # Simple format: "Title. Credit: Creator."
    parts = []
    
    if title:
        parts.append(title)
    
    if credit and credit.lower() not in ['unknown', 'nan', '']:
        parts.append(f"Credit: {credit}")
    
    return ". ".join(parts) + "." if parts else ""

def generate_html_attribution(row):
    """
    Generate HTML-formatted attribution for web use
    """
    title = row.get('Title', 'Unknown')
    credit = row.get('Credit', 'Unknown')
    source = row.get('Source', '')
    
    html = f'<figure>\n'
    html += f'  <img src="images/{row.get("image_id")}.jpg" alt="{title}">\n'
    html += f'  <figcaption>\n'
    html += f'    <strong>{title}</strong><br>\n'
    
    if credit and credit.lower() not in ['unknown', 'nan']:
        html += f'    Credit: {credit}<br>\n'
    
    if source:
        html += f'    <a href="{source}" target="_blank">View source</a>\n'
    
    html += f'  </figcaption>\n'
    html += f'</figure>'
    
    return html

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate attribution text for images")
    parser.add_argument(
        "--input",
        default="data/filtered_images_final.csv",
        help="Input CSV with filtered images"
    )
    parser.add_argument(
        "--output",
        default="data/image_attributions.csv",
        help="Output CSV with attribution text"
    )
    parser.add_argument(
        "--format",
        default="all",
        choices=['all', 'text', 'caption', 'html'],
        help="Attribution format to generate"
    )
    
    args = parser.parse_args()
    
    # Load images
    df = pd.read_csv(args.input)
    
    print("\n" + "=" * 70)
    print("📝 GENERATING ATTRIBUTIONS")
    print("=" * 70)
    print(f"Images: {len(df)}")
    print(f"Format: {args.format}")
    print("=" * 70 + "\n")
    
    # Generate attribution text
    if args.format in ['all', 'text']:
        df['attribution_text'] = df.apply(generate_attribution_text, axis=1)
    
    if args.format in ['all', 'caption']:
        df['caption_text'] = df.apply(generate_caption_text, axis=1)
    
    if args.format in ['all', 'html']:
        df['html_attribution'] = df.apply(generate_html_attribution, axis=1)
    
    # Save output
    df.to_csv(args.output, index=False)
    
    print(f"✅ Saved attributions to: {args.output}\n")
    
    # Show samples
    print("=" * 70)
    print("📸 SAMPLE ATTRIBUTIONS (First 3 images)")
    print("=" * 70 + "\n")
    
    for idx, row in df.head(3).iterrows():
        image_id = row.get('image_id') or row.get('Image ID')
        print(f"Image ID: {image_id}")
        print(f"Title: {row.get('Title', 'N/A')}")
        
        if 'attribution_text' in row:
            print(f"\nFull Attribution:")
            print(f"{row['attribution_text']}")
        
        if 'caption_text' in row:
            print(f"\nCaption:")
            print(f"{row['caption_text']}")
        
        print("\n" + "-" * 70 + "\n")
    
    # Generate a separate attribution file for easy reference
    attribution_file = "data/ATTRIBUTIONS.txt"
    with open(attribution_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("IMAGE ATTRIBUTIONS FOR CANCER TEXTBOOK\n")
        f.write("=" * 70 + "\n\n")
        
        for idx, row in df.iterrows():
            image_id = row.get('image_id') or row.get('Image ID')
            f.write(f"Image ID: {image_id}\n")
            f.write(f"File: {image_id}.jpg\n")
            
            if 'attribution_text' in row:
                f.write(f"Attribution: {row['attribution_text']}\n")
            
            if 'caption_text' in row:
                f.write(f"Caption: {row['caption_text']}\n")
            
            f.write("\n" + "-" * 70 + "\n\n")
    
    print(f"✅ Full attribution list saved to: {attribution_file}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()