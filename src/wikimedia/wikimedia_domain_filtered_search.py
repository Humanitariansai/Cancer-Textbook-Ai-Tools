import os, re, time, argparse, datetime as dt
import requests, pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

API = "https://commons.wikimedia.org/w/api.php"

def clean_text(s):
    if not s:
        return ""
    return BeautifulSoup(str(s), "html.parser").get_text(" ", strip=True)

def wikimedia_search_files(query, limit=20):
    url = "https://commons.wikimedia.org/w/api.php"
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
    r = requests.get(url, params=params, headers=headers, timeout=10)
    if r.status_code == 429:
        time.sleep(5)
        return wikimedia_search_files(query, limit)
    r.raise_for_status()
    data = r.json()
    if "query" not in data:
        return []
    pages = data["query"]["pages"]
    results = []
    for _, page in pages.items():
        info = page.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})
        results.append({
            "title": page.get("title"),
            "page_url": page.get("fullurl"),
            "image_url": info.get("thumburl"),
            "width": info.get("width"),
            "height": info.get("height"),
            "license": clean_text(meta.get("LicenseShortName", {}).get("value", "Unknown")),
            "credit": clean_text(meta.get("Credit", {}).get("value", "")),
            "desc": clean_text(meta.get("ImageDescription", {}).get("value", "")),
        })
    return results

def keyword_overlap_score(a, b):
    aw, bw = set(a.lower().split()), set(b.lower().split())
    return len(aw & bw) / max(1, len(aw | bw))

def build_domain_query(text):
    base_terms = re.findall(r"[A-Za-z]+", text)
    stop = {"the","and","of","to","a","in","on","for","with","by","as","from","is","are"}
    words = [w for w in base_terms if w.lower() not in stop and len(w) > 2]
    core = " ".join(words[:6])
    # add biomedical focus
    domain_terms = "pathology histology tumor cancer biopsy tissue cell microscopy"
    return f"({core}) ({domain_terms})"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--model", choices=["all-MiniLM-L6-v2","biomed"], default="biomed")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--min-score", type=float, default=0.35)
    ap.add_argument("--limit-per-para", type=int, default=30)
    args = ap.parse_args()

    df = pd.read_csv("data/chapters_dataset.csv")
    df = df[df["chapter_id"].astype(str) == str(args.chapter)]
    if df.empty:
        print(f"⚠️ No rows for chapter {args.chapter}")
        return

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"data/wikimedia_domain_matches_{args.chapter}_{ts}.csv"

    model_name = "all-MiniLM-L6-v2" if args.model == "all-MiniLM-L6-v2" else "gsarti/biobert-nli"
    print(f"🔤 Using model: {model_name}")
    model = SentenceTransformer(model_name)

    all_rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Wikimedia domain search"):
        para_id, text = int(row["paragraph_id"]), str(row["text"])
        query = build_domain_query(text)
        candidates = wikimedia_search_files(query, limit=args.limit_per_para)
        if not candidates:
            continue

        # semantic scoring
        para_emb = model.encode(text, convert_to_tensor=True)
        descs = [f"{c['title']} {c['desc']} {c['credit']}" for c in candidates]
        cand_emb = model.encode(descs, convert_to_tensor=True)
        sims = util.cos_sim(para_emb, cand_emb).cpu().numpy().flatten()

        for cand, sim in zip(candidates, sims):
            kw_score = keyword_overlap_score(text, cand["desc"])
            final_score = 0.7 * float(sim) + 0.3 * kw_score
            if final_score >= args.min_score:
                all_rows.append({
                    "chapter_id": args.chapter,
                    "paragraph_id": para_id,
                    "query": query,
                    "title": cand["title"],
                    "image_url": cand["image_url"],
                    "page_url": cand["page_url"],
                    "license": cand["license"],
                    "credit": cand["credit"],
                    "desc": cand["desc"],
                    "semantic_score": round(float(sim), 4),
                    "keyword_score": round(kw_score, 4),
                    "final_score": round(final_score, 4)
                })

    out = pd.DataFrame(all_rows).sort_values("final_score", ascending=False)
    out.to_csv(out_csv, index=False)
    print(f"✅ Saved {len(out)} Wikimedia domain-filtered matches → {out_csv}")

if __name__ == "__main__":
    main()
