from bs4 import BeautifulSoup
import os

# Read the first HTML file we saved
html_file = "data/html_cache/12496.html"

if not os.path.exists(html_file):
    print(f"File not found: {html_file}")
    print("\nAvailable files:")
    for f in os.listdir("data/html_cache/")[:5]:
        print(f"  - {f}")
else:
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    
    print(f"HTML file size: {len(html)} characters")
    print("=" * 70)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check for common title locations
    print("\n🔍 Looking for TITLE:")
    print("-" * 70)
    if soup.find('title'):
        print(f"<title> tag: {soup.find('title').get_text(strip=True)}")
    if soup.find('h1'):
        print(f"<h1> tag: {soup.find('h1').get_text(strip=True)}")
    if soup.find('h2'):
        print(f"<h2> tag: {soup.find('h2').get_text(strip=True)}")
    
    # Look for divs with class containing 'title'
    title_divs = soup.find_all('div', class_=lambda x: x and 'title' in x.lower())
    if title_divs:
        print(f"\nDivs with 'title' in class ({len(title_divs)} found):")
        for div in title_divs[:3]:
            print(f"  Class: {div.get('class')}")
            print(f"  Text: {div.get_text(strip=True)[:100]}")
    
    # Show all unique div classes
    print("\n" + "=" * 70)
    print("📦 ALL DIV CLASSES found in HTML:")
    print("-" * 70)
    all_classes = set()
    for div in soup.find_all('div'):
        if div.get('class'):
            all_classes.update(div.get('class'))
    
    for cls in sorted(all_classes)[:30]:
        print(f"  - {cls}")
    
    if len(all_classes) > 30:
        print(f"  ... and {len(all_classes) - 30} more")
    
    # Show structure of main content
    print("\n" + "=" * 70)
    print("📄 FIRST 2000 CHARACTERS OF HTML:")
    print("-" * 70)
    print(html[:2000])
    
    print("\n" + "=" * 70)
    print("📄 ALL TEXT CONTENT (first 1000 chars):")
    print("-" * 70)
    text = soup.get_text(separator=' ', strip=True)
    print(text[:1000])