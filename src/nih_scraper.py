import time, requests, os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://visualsonline.cancer.gov/"

def search_nih_images(query, limit=10):
    search_url = f"{BASE_URL}searchaction.cfm?q={query}&sort=relevance"
    print(f"\n🔎 NIH URL: {search_url}")
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(search_url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    results = []
    containers = soup.find_all("div", class_="resultsitempic")
    print(f"✅ Found {len(containers)} result containers")

    for idx, c in enumerate(containers[:limit], 1):
        try:
            img_tag, link_tag = c.find("img"), c.find("a")
            img_url = BASE_URL + img_tag["src"] if img_tag and not img_tag["src"].startswith("http") else (img_tag["src"] if img_tag else "")
            detail_url = BASE_URL + link_tag["href"] if link_tag and not link_tag["href"].startswith("http") else (link_tag["href"] if link_tag else "")
            title = img_tag.get("alt", f"Image {idx}")
            results.append({"title": title, "url": detail_url, "thumbnail": img_url, "score": 1.0})
        except Exception as e:
            print(f"⚠️ Error parsing {idx}: {e}")
    return results

def get_full_resolution_image(detail_url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(detail_url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    img = soup.find("img", class_="previewlg")
    if img:
        return BASE_URL + img["src"] if not img["src"].startswith("http") else img["src"]
    return None
