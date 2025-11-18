import os, re, time, argparse, datetime as dt
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

API = "https://commons.wikimedia.org/w/api.php"

MEDICAL_KEYWORDS = {
    "tumor", "carcinoma", "cancer", "neoplasm", "lesion", "biopsy", "metastasis",
    "melanoma", "sarcoma", "adenocarcinoma", "pathology", "histology",
    "epithelium", "cytology", "microscopy", "oncology", "radiology"
}

def html_to_text(s):
    return BeautifulSoup(str(s or ""), "html.parser").get_text(" ", strip=True)

def wikimedia_search_files(query, limit=20):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo|info",
        "inprop": "url",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 640,
    }
    headers = {"User-Agent": "CancerTextbookAI/1.0 (contact: kalyankumar194@gmail.com)"}
    r = requests.get(API, params=params, headers=headers, timeout=10)
    if r.status_code != 200 or "query" not in r.json():
        return []
    results = []
    for _, p in r.json()["query"]["pages"].items():
        info = p.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})
        results.append({
            "title": p.get("title", ""),
            "page_url": p.get("fullurl", ""),
            "image_url": info.get("thumburl", ""),
            "description": html_to_text(meta.get("ImageDescription", {}).get("value", "")),
            "credit": html_to_text(meta.get("Credit", {}).get("value", "")),
            "license": meta.get("LicenseShortName", {}).get("value", "Unknown"),
        })
    return results

def build_query(text, max_terms=6):
    words = re.findall(r"[A-Za-z]+", text)
    stop = {"the","and","of","to","a","in","is","on","for","with","by","as","that",
            "this","from","an","or","at","be","are","it","we","was","were","but",
            "about","into","over","without","iii","ii","iv","i","figure","chapter",
            "introduction","section","subsection","system","systems"}
    kws = [w for w in words if w.lower() not in stop and len(w) > 2]
    uniq = []
    seen = set()
    for w in kws:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            uniq.append(w)
    return " ".join(uniq[:max_terms]) if uniq else "cancer"

def compute_hybrid_score(model, paragraph_text, cand):
    base_text = " ".join([cand.get("title",""), cand.get("description",""), cand.get("credit","")])
    sem_score = util.cos_sim(
        model.encode(paragraph_text, convert_to_tensor=True),
        model.encode(base_text, convert_to_tensor=True)
    ).item()
    kw_bonus = sum(1 for kw in MEDICAL_KEYWORDS if kw.lower() in base_text.lower()) * 0.05
    return min(1.0, sem_score + kw_bonus)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--model", choices=["all-MiniLM-L6-v2","biomed"], default="all-MiniLM-L6-v2")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--min-score", type=float, default=0.4)
    ap.add_argument("--limit-per-para", type=int, default=40)
    args = ap.parse_args()

    df = pd.read_csv("data/chapters_dataset.csv")
    dfc = df[df["chapter_id"].astype(str) == str(args.chapter)]
    if dfc.empty:
        print(f"⚠️ No rows found for chapter {args.chapter}")
        return

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"data/wikimedia_hybrid_matches_{args.chapter}_{ts}.csv"

    model_name = "all-MiniLM-L6-v2" if args.model == "all-MiniLM-L6-v2" else "gsarti/biobert-nli"
    print(f"🔤 Using model: {model_name}")
    model = SentenceTransformer(model_name)

    rows = []
    for _, r in tqdm(dfc.iterrows(), total=len(dfc), desc="Wikimedia hybrid search"):
        para_id = int(r["paragraph_id"])
        text = str(r["text"])
        query = build_query(text)
        cands = wikimedia_search_files(query, limit=args.limit_per_para)

        scored = []
        for c in cands:
            s = compute_hybrid_score(model, text, c)
            if s >= args.min_score:
                scored.append((s, c))
        scored.sort(reverse=True, key=lambda x: x[0])
        for rank, (score, c) in enumerate(scored[:args.topk], 1):
            rows.append({
                "source": "wikimedia",
                "chapter_id": args.chapter,
                "paragraph_id": para_id,
                "rank": rank,
                "query": query.replace(" ", "+"),
                "image_title": c.get("title",""),
                "detail_url": c.get("page_url",""),
                "image_url": c.get("image_url",""),
                "image_caption": c.get("description",""),
                "image_credit": c.get("credit",""),
                "license": c.get("license",""),
                "similarity_score": round(score,4),
            })

    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(out)} Wikimedia hybrid matches → {out_csv}")

if __name__ == "__main__":
    main()

