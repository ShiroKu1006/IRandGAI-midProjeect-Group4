"""Compute Precision@5 from the hand-labeled judgments.csv.

Usage (from code/backend): python -m evaluation.compute_metrics
"""
import csv
import json
from collections import OrderedDict
from pathlib import Path

from evaluation.metrics import distinct_pages, mean, precision_at_k

HERE = Path(__file__).parent


def load_judgments(path):
    by_query = OrderedDict()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_query.setdefault(row["query_id"], []).append(row)
    return by_query


def evaluate(by_query):
    results = []
    for qid, rows in by_query.items():
        rows = sorted(rows, key=lambda r: int(r["rank"]))
        rel = []
        for r in rows:
            if r["url"] and r["relevant"] not in ("0", "1"):
                raise ValueError(f"{qid} rank {r['rank']}: `relevant` must be 0 or 1")
            rel.append(1 if r["relevant"] == "1" and r["url"] else 0)
        urls = [r["url"] for r in rows if r["url"]]
        results.append({
            "query_id": qid, "query": rows[0]["query"],
            "p_at_5": precision_at_k(rel, 5),
            "relevant": sum(rel), "returned": len(urls),
            "distinct_pages": distinct_pages(urls),
        })
    return results


def main():
    spec = json.loads((HERE / "queries.json").read_text(encoding="utf-8"))
    if spec.get("status") != "frozen":
        print("WARNING: queries.json status is not 'frozen'; results are provisional.")
    results = evaluate(load_judgments(HERE / "judgments.csv"))
    lines = ["| id | query | P@5 | relevant | distinct pages in top 5 |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['query_id']} | {r['query']} | {r['p_at_5']:.2f} | {r['relevant']}/{r['returned']} | {r['distinct_pages']} |")
    avg = mean(r["p_at_5"] for r in results)
    lines.append(f"| | **mean** | **{avg:.3f}** | | |")
    text = "\n".join(lines)
    (HERE / "results.md").write_text(text + "\n", encoding="utf-8")
    with open(HERE / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    print(text)


if __name__ == "__main__":
    main()
