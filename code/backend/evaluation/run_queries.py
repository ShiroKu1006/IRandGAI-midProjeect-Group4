"""Run the frozen query set against data/index.json and dump top-5 for manual labeling.

Usage (from code/backend): python -m evaluation.run_queries [--force]
Writes evaluation/judgments.csv (fill `relevant` with 1/0 and `reason`),
evaluation/review.md (readable view) and evaluation/run_info.json (hashes).
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from indexer import DEFAULT_INDEX_PATH, load_search_index

HERE = Path(__file__).parent
TOP_K = 5


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--force", action="store_true", help="overwrite existing judgments.csv")
    args = parser.parse_args()

    out_csv = HERE / "judgments.csv"
    if out_csv.exists() and not args.force:
        raise SystemExit("judgments.csv exists (labels would be lost); use --force to overwrite.")

    spec = json.loads((HERE / "queries.json").read_text(encoding="utf-8"))
    search_index = load_search_index(args.index)

    rows, review = [], ["# Top-5 review", ""]
    for q in spec["queries"]:
        _, hits = search_index.search(q["query"], top_k=TOP_K)
        review += [f"## {q['id']}: {q['query']}", f"Need: {q['need']}", ""]
        for rank in range(1, TOP_K + 1):
            hit = hits[rank - 1] if rank <= len(hits) else None
            rows.append({
                "query_id": q["id"], "query": q["query"], "rank": rank,
                "doc_id": hit["doc_id"] if hit else "",
                "url": hit["url"] if hit else "",
                "title": hit["title"] if hit else "",
                "score": f"{hit['score']:.4f}" if hit else "",
                "relevant": "", "reason": "",
            })
            if hit:
                review.append(f"{rank}. [{hit['title']}]({hit['url']}) score={hit['score']:.4f}")
            else:
                review.append(f"{rank}. (no result)")
        review.append("")

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (HERE / "review.md").write_text("\n".join(review), encoding="utf-8")
    (HERE / "run_info.json").write_text(json.dumps({
        "index_sha256": sha256(args.index),
        "queries_sha256": sha256(HERE / "queries.json"),
        "queries_status": spec.get("status"),
        "top_k": TOP_K,
    }, indent=2), encoding="utf-8")
    print(f"wrote {out_csv}, review.md, run_info.json")


if __name__ == "__main__":
    main()
