# src/paragraph_image_matcher.py
"""
Paragraph → NIH image matcher with semantic ranking, progress bar, and smart de-duplication.

Features:
- Builds lightweight keyword queries per paragraph
- Uses Selenium to fetch NIH Visuals Online results (JS-rendered)
- Ranks candidates via sentence-transformers (all-MiniLM-L6-v2)
- Saves top-K per paragraph above a min similarity threshold
- Progress bar over paragraphs
- Timestamped CSV output
- Smart duplicate policy: allow duplicates only if the new match is clearly stronger

Usage example:
  python src/paragraph_image_matcher.py --chapter 31 --topk 3 --min-score 0.40
"""

import os
import re
import time
import argparse
import datetime as dt
import pandas as pd
from bs4 import BeautifulSoup

# Embeddings
from sentence_transformers import SentenceTransformer, util

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from tqdm import tqdm

# NIH endpoints
NIH_BASE = "https://visualsonline.cancer.gov/"
SEARCH_URL_TPL = NIH_BASE + "searchaction.cfm?q={query}&sort=relevance"

# ---------------------------
# Query building
# ---------------------------
def build_query(text: str, max_terms: int = 6) -> str:
    """
    Lightweight keyword extractor to form a search string for NIH.
    Semantic ranking happens later with embeddings.
    """
    words = re.findall(r"[A-Za-z]+", text)
    stop = {
        "the","and","of","to","a","in","is","on","for","with","by","as","that",
        "this","from","an","or","at","be","are","it","we","was","were","but",
        "about","into","over","without","iii","ii","iv","i","figure","chapter",
        "introduction","section","subsection","system","systems"
    }
    kws = [w for w in words if w.lower() not in stop and len(w) > 2]
    # keep order, de-dup
    seen = set()
    uniq = []
    for w in kws:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            uniq.append(w)
    return "+".join(uniq[:max_terms]) if uniq else "cancer"


# ---------------------------
# Selenium driver
# ---------------------------
def get_selenium_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


# ---------------------------
# NIH search (Selenium)
# ---------------------------
def nih_search_candidates(driver, query: str, limit: int = 20, sleep_sec: float = 2.0):
    """
    Use Selenium to render NIH Visuals Online search results and collect candidates:
    Returns list of dicts: [{title, detail_url, thumbnail, snippet}]
    """
    search_url = SEARCH_URL_TPL.format(query=query)
    print(f"🔎 NIH URL: {search_url}")
    driver.get(search_url)
    time.sleep(sleep_sec)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    results = []
    containers = soup.find_all("div", class_="resultsitempic")

    for idx, c in enumerate(containers[:limit], 1):
        try:
            a = c.find("a")
            img = c.find("img")

            detail_url = a.get("href") if a else ""
            if detail_url and not detail_url.startswith("http"):
                detail_url = NIH_BASE + detail_url

            thumb = img.get("src") if img else ""
            if thumb and not thumb.startswith("http"):
                thumb = NIH_BASE + thumb

            desc_div = c.find_next_sibling("div", class_="resultsitemdesc")
            desc_text = desc_div.get_text(" ", strip=True) if desc_div else ""

            title = (img.get("alt") if img and img.get("alt") else "").strip()
            if not title:
                # fallback: first part of description or placeholder
                title = desc_text[:120] or "thumbnail"

            results.append({
                "title": title,
                "detail_url": detail_url,
                "thumbnail": thumb,
                "snippet": desc_text
            })
        except Exception:
            continue

    return results


# ---------------------------
# Utilities
# ---------------------------
def extract_image_id(detail_url: str) -> str:
    """
    NIH detail URLs look like: .../details.cfm?imageid=12345
    """
    if not detail_url:
        return ""
    m = re.search(r"imageid=(\d+)", detail_url)
    return m.group(1) if m else ""


def rank_candidates(model, paragraph_text: str, candidates: list):
    """
    Rank NIH candidates by semantic similarity (title + snippet) vs paragraph_text.
    Returns list of candidates with 'match_score' sorted descending.
    """
    if not candidates:
        return []

    para_emb = model.encode(paragraph_text, convert_to_tensor=True)
    cand_texts = [
        (c.get("title","") + " " + c.get("snippet","")).strip() for c in candidates
    ]
    cand_embs = model.encode(cand_texts, convert_to_tensor=True)

    sims = util.cos_sim(para_emb, cand_embs).cpu().numpy().flatten()

    scored = []
    for c, s in zip(candidates, sims):
        cc = dict(c)
        cc["match_score"] = float(s)
        cc["image_id"] = extract_image_id(c.get("detail_url",""))
        scored.append(cc)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored


def select_top_with_dedup(scored, topk: int, min_score: float, global_best: dict, bump: float = 0.05):
    """
    Smart duplicate policy:
    - Allow duplicates across paragraphs only if the new score is at least (prev_best + bump).
    - Always de-duplicate within a paragraph (unique image_id).
    """
    chosen = []
    used_ids = set()

    for c in scored:
        if len(chosen) >= topk:
            break
        if c["match_score"] < min_score:
            continue

        imgid = c.get("image_id", "")
        if imgid in used_ids:
            continue  # within-paragraph duplicate

        # Global duplicate rule
        prev = global_best.get(imgid, None)
        if prev is not None and c["match_score"] < (prev + bump):
            continue  # not strong enough to reuse globally

        chosen.append(c)
        used_ids.add(imgid)

    # Update global best scores
    for c in chosen:
        imgid = c.get("image_id", "")
        if not imgid:
            continue
        prev = global_best.get(imgid, None)
        if prev is None or c["match_score"] > prev:
            global_best[imgid] = c["match_score"]

    return chosen


# ---------------------------
# Main
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Paragraph → NIH image matcher (semantic ranking)")
    parser.add_argument("--chapter", required=True, type=str, help="Chapter ID (e.g., 31 or 31_)")
    parser.add_argument("--every", type=int, default=1, help="Use every Nth paragraph (default: 1)")
    parser.add_argument("--max-per-para", type=int, default=20, help="Max NIH candidates per paragraph")
    parser.add_argument("--topk", type=int, default=3, help="Save top-k matches per paragraph")
    parser.add_argument("--min-score", type=float, default=0.40, help="Minimum similarity score to keep")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to sleep after each search")
    args = parser.parse_args()

    os.makedirs("data", exist_ok=True)
    df = pd.read_csv("data/chapters_dataset.csv")

    # Normalize chapter id (accept "31" or "31_")
    chids = set(df["chapter_id"].astype(str).unique())
    if args.chapter not in chids:
        norm = args.chapter.rstrip("_")
        match = [c for c in chids if c.rstrip("_") == norm]
        if not match:
            print(f"⚠️ Chapter {args.chapter} not found. Available: {sorted(chids)}")
            return
        chapter_id = match[0]
    else:
        chapter_id = args.chapter

    dfc = df[df["chapter_id"].astype(str) == chapter_id].copy()
    if dfc.empty:
        print(f"⚠️ No rows for chapter {chapter_id}")
        return

    # Timestamped output
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"data/paragraph_image_map_{chapter_id}_{ts}.csv"

    print(f"📖 Processing chapter {chapter_id}: {len(dfc)} paragraphs")
    print(f"⚙️  Settings → topk={args.topk} | min_score={args.min_score:.2f} | max_per_para={args.max_per_para}")

    # Load model and driver
    model = SentenceTransformer("all-MiniLM-L6-v2")
    driver = get_selenium_driver()

    rows = []
    global_best_by_img = {}  # image_id -> best score seen so far (for smart duplicate policy)

    # Progress bar over selected rows
    work_df = dfc.iloc[::args.every]
    for _, row in tqdm(work_df.iterrows(), total=len(work_df), desc="Matching images"):
        para_id = int(row["paragraph_id"])
        text = str(row["text"])

        # Build + search
        query = build_query(text)
        candidates = nih_search_candidates(driver, query=query, limit=args.max_per_para, sleep_sec=args.sleep)

        # Rank
        scored = rank_candidates(model, text, candidates)

        # Select top with smart de-duplication
        best = select_top_with_dedup(scored, topk=args.topk, min_score=args.min_score, global_best=global_best_by_img)

        if not best:
            # Save an empty row (still useful for auditing)
            rows.append({
                "chapter_id": chapter_id,
                "paragraph_id": para_id,
                "query": query,
                "picked_title": "",
                "detail_url": "",
                "thumbnail": "",
                "image_id": "",
                "match_score": "",
                "candidate_count": len(candidates),
                "rank": ""
            })
        else:
            for rank, item in enumerate(best, 1):
                rows.append({
                    "chapter_id": chapter_id,
                    "paragraph_id": para_id,
                    "query": query,
                    "picked_title": item.get("title",""),
                    "detail_url": item.get("detail_url",""),
                    "thumbnail": item.get("thumbnail",""),
                    "image_id": item.get("image_id",""),
                    "match_score": round(item.get("match_score", 0.0), 4),
                    "candidate_count": len(candidates),
                    "rank": rank
                })

        # polite delay between different queries
        time.sleep(args.sleep)

    # Cleanup
    driver.quit()

    # Write results
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(out_df)} rows → {out_csv}")


if __name__ == "__main__":
    main()
