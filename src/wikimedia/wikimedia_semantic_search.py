import os, re, time, argparse, datetime as dt
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

API = "https://commons.wikimedia.org/w/api.php"

def html_to_text(s: str) -> str:
    if not s:
        return ""
    return BeautifulSoup(str(s), "html.parser").get_text(" ", strip=True)

def extval(meta: dict, key: str) -> str:
    try:
        return html_to_text(meta.get(key, {}).get("value", "")).strip()
    except Exception:
        return ""

MEDICAL_SYNONYMS = {
    "tumor": ["neoplasm", "carcinoma", "malignancy", "cancer"],
    "cancer": ["carcinoma", "neoplasm", "tumor", "malignant"],
    "breast": ["mammary", "ductal", "lobular"],
    "lung": ["pulmonary", "bronchial"],
    "colon": ["colorectal", "intestinal"],
    "liver": ["hepatic"],
    "stomach": ["gastric"],
    "kidney": ["renal"],
    "skin": ["dermal", "cutaneous", "melanoma"],
}

def expand_query_terms(query: str) -> str:
    terms = query.split()
    expanded = []
    for t in terms:
        expanded.append(t)
        if t.lower() in MEDICAL_SYNONYMS:
            expanded.extend(MEDICAL_SYNONYMS[t.lower()])
    return " ".join(sorted(set(expanded)))

def wikimedia_search_files(query, limit=10, categories=None):
    if categories is None:
        categories = ["Medical_illustrations", "Histopathology", "Oncology", "Anatomy"]
    joined_cats = " OR ".join([f'incategory:"{c}"' for c in categories])
    final_query = f"{query} ({joined_cats})"

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": final_query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo|info",
        "inprop": "url",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 640,
    }

    headers = {"User-Agent": "CancerTextbookAI/2.0 (contact: kalyankumar194@gmail.com)"}

    try:
        r = requests.get(API, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"⚠️ Wikimedia API error: {e}")
        return []

    if "query" not in data:
        return []

    pages = data["query"]["pages"]
    results = []
    for _, page in pages.items():
        info = page.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})
        results.append({
            "title": page.get("title", ""),
            "page_url": page.get("fullurl", ""),
            "image_url": info.get("thumburl", ""),
            "description": extval(meta, "ImageDescription"),
            "credit": extval(meta, "Credit"),
            "license": extval(meta, "LicenseShortName"),
            "mime": info.get("mime", ""),
            "width": info.get("width", 0),
            "height": info.get("height", 0)
        })
    return results

def build_query(text: str, max_terms: int = 6):
    words = re.findall(r"[A-Za-z]+", text)
    stop = {"the","and","of","to","a","in","is","on","for","with","by","as","that","this","from","an","or","at","be","are","it","we"}
    kws = [w for w in words if w.lower() not in stop and len(w) > 2]
    uniq = []
    seen = set()
    for w in kws:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            uniq.append(w)
    return " ".join(uniq[:max_terms]) if uniq else "cancer"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True, help="Chapter ID, e.g. 31_")
    ap.add_argument("--every", type=int, default=1, help="Use every Nth paragraph")
    ap.add_argument("--limit-per-para", type=int, default=25, help="Max Wikimedia candidates per paragraph")
    ap.add_argument("--topk", type=int, default=5, help="Top-k to keep per paragraph")
    ap.add_argument("--min-score", type=float, default=0.55, help="Minimum similarity score")
    ap.add_argument("--model", choices=["all-MiniLM-L6-v2", "biomed"], default="all-MiniLM-L6-v2")
    args = ap.parse_args()

    os.makedirs("data", exist_ok=True)
    df = pd.read_csv("data/chapters_dataset.csv")
    dfc = df[df["chapter_id"].astype(str) == str(args.chapter)].copy()
    if dfc.empty:
        print(f"⚠️ No rows for chapter {args.chapter}")
        return

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"data/wikimedia_semantic_matches_{args.chapter}_{ts}.csv"

    model_name = "all-MiniLM-L6-v2" if args.model == "all-MiniLM-L6-v2" else "gsarti/biobert-nli"
    print(f"🔤 Embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    rows = []
    work_df = dfc.iloc[::args.every]
    for _, r in tqdm(work_df.iterrows(), total=len(work_df), desc="Wikimedia search"):
        para_id = int(r["paragraph_id"])
        text = str(r["text"])
        base_query = build_query(text)
        expanded_query = expand_query_terms(base_query)

        candidates = wikimedia_search_files(expanded_query, limit=args.limit_per_para)
        if not candidates:
            continue

        para_emb = model.encode(text, convert_to_tensor=True)
        cand_texts = [f"{c['title']} {c['description']} {c['credit']}" for c in candidates]
        cand_emb = model.encode(cand_texts, convert_to_tensor=True)
        sims = util.cos_sim(para_emb, cand_emb).cpu().numpy().flatten()

        for c, s in zip(candidates, sims):
            c["similarity_score"] = float(s)
        ranked = sorted(candidates, key=lambda x: x["similarity_score"], reverse=True)
        top = [x for x in ranked if x["similarity_score"] >= args.min_score][:args.topk]

        for rank, c in enumerate(top, 1):
            rows.append({
                "source": "wikimedia",
                "chapter_id": args.chapter,
                "paragraph_id": para_id,
                "rank": rank,
                "query": expanded_query.replace(" ", "+"),
                "image_title": c.get("title",""),
                "image_url": c.get("image_url",""),
                "image_caption": c.get("description",""),
                "image_credit": c.get("credit",""),
                "license": c.get("license",""),
                "similarity_score": round(float(c["similarity_score"]), 4),
            })

    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(out)} Wikimedia rows → {out_csv}")

if __name__ == "__main__":
    main()
