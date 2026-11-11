"""Compare TF-IDF and BM25 on the frozen evaluation snapshot."""

import argparse
import csv
import hashlib
import json

from evaluation.metrics import mean, precision_at_k
from evaluation.run_queries import HERE, TOP_K, sha256
from indexer import DEFAULT_INDEX_PATH, load_search_index


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fields, *, mode="w"):
    with path.open(mode, encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def collect_rankings(queries, index):
    rows = []
    for query in queries:
        for method, search in (("tfidf", index.search), ("bm25", index.search_bm25)):
            _, hits = search(query["query"], top_k=TOP_K)
            for rank in range(1, TOP_K + 1):
                hit = hits[rank - 1] if rank <= len(hits) else {}
                rows.append({
                    "method": method, "query_id": query["id"], "query": query["query"],
                    "rank": rank, "doc_id": str(hit.get("doc_id", "")),
                    "url": hit.get("url", ""), "title": hit.get("title", ""),
                    "score": hit.get("score", ""),
                })
    return rows


def doc_key(row):
    return row["query_id"], row["doc_id"]


def review_rows(queries, rankings, baseline):
    needs = {query["id"]: query["need"] for query in queries}
    rows = []
    for row in rankings:
        if row["method"] == "bm25" and row["doc_id"] and doc_key(row) not in baseline:
            rows.append({
                "query_id": row["query_id"], "query": row["query"],
                "need": needs[row["query_id"]], "rank": row["rank"],
                "doc_id": row["doc_id"], "url": row["url"], "title": row["title"],
                "relevant": "", "reason": "", "status": "pending",
            })
    return rows


def compare_rankings(rankings, baseline, expected, supplemental):
    expected_urls = {doc_key(row): row["url"] for row in expected}
    judgments = baseline.copy()
    seen = set()
    for row in supplemental:
        key = doc_key(row)
        if key in seen or key not in expected_urls or row["url"] != expected_urls[key]:
            raise ValueError(f"重複或與目前快照排名不符的補充判定：{'/'.join(key)}")
        seen.add(key)
        if row["status"] == "confirmed" and valid_judgment(row):
            judgments[key] = row
    missing = expected_urls.keys() - judgments.keys()
    if missing:
        keys = ", ".join("/".join(key) for key in sorted(missing))
        raise ValueError(f"尚未確認相關性或缺少 0/1 與判定理由：{keys}")

    rows = []
    by_query = {}
    for row in rankings:
        judgment = judgments[doc_key(row)] if row["doc_id"] else {
            "relevant": "0", "reason": "無回傳結果",
        }
        rows.append(dict(row, relevant=judgment["relevant"], reason=judgment["reason"]))
        query = by_query.setdefault(row["query_id"], {"query": row["query"], "tfidf": [], "bm25": []})
        query[row["method"]].append(int(judgment["relevant"]))

    scores = []
    for query_id, query in by_query.items():
        tfidf = precision_at_k(query["tfidf"], TOP_K)
        bm25 = precision_at_k(query["bm25"], TOP_K)
        scores.append(score_row(query_id, query["query"], tfidf, bm25, 2))
    tfidf_mean = mean(precision_at_k(query["tfidf"], TOP_K) for query in by_query.values())
    bm25_mean = mean(precision_at_k(query["bm25"], TOP_K) for query in by_query.values())
    scores.append(score_row("mean", "", tfidf_mean, bm25_mean, 3))
    return rows, scores


def score_row(query_id, query, tfidf, bm25, decimals):
    delta = round(bm25 - tfidf, decimals) or 0.0
    return {
        "query_id": query_id, "query": query, "tfidf_p_at_5": f"{tfidf:.{decimals}f}",
        "bm25_p_at_5": f"{bm25:.{decimals}f}", "delta_p_at_5": f"{delta:.{decimals}f}",
    }


def valid_judgment(row):
    return row["relevant"] in ("0", "1") and bool(row["reason"].strip())


def load_comparison():
    queries_text = (HERE / "queries.json").read_text(encoding="utf-8")
    spec = json.loads(queries_text)
    run = json.loads((HERE / "run_info.json").read_text(encoding="utf-8"))
    # Older baseline runs hashed the file bytes, which may contain CRLF.
    query_hashes = {
        hashlib.sha256(queries_text.replace("\n", newline).encode("utf-8")).hexdigest()
        for newline in ("\n", "\r\n")
    }
    if (
        spec["status"] != "frozen" or len(spec["queries"]) != 10
        or run["top_k"] != TOP_K or sha256(DEFAULT_INDEX_PATH) != run["index_sha256"]
        or run["queries_sha256"] not in query_hashes
    ):
        raise ValueError("索引、固定查詢或評估設定與既有 run_info.json 不符。")

    rankings = collect_rankings(spec["queries"], load_search_index())
    original = read_csv(HERE / "judgments.csv")

    def identity(row):
        return row["query_id"], row["query"], int(row["rank"]), row["doc_id"], row["url"]

    if sorted(map(identity, original)) != sorted(
        identity(row) for row in rankings if row["method"] == "tfidf"
    ):
        raise ValueError("TF-IDF 前五名與既有 judgments.csv 不符。")
    baseline = {}
    for row in original:
        if row["doc_id"]:
            key = doc_key(row)
            if key in baseline or not valid_judgment(row):
                raise ValueError(f"既有判定重複或不完整：{'/'.join(key)}")
            baseline[key] = row
    return rankings, baseline, review_rows(spec["queries"], rankings, baseline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "compare"))
    args = parser.parse_args()
    out = HERE / "bm25"
    review = out / "new_judgments.csv"
    try:
        rankings, baseline, pending = load_comparison()
        if args.command == "prepare":
            out.mkdir(exist_ok=True)
            fields = (
                "query_id", "query", "need", "rank", "doc_id", "url", "title",
                "relevant", "reason", "status",
            )
            try:
                write_csv(review, pending, fields, mode="x")
            except FileExistsError:
                print(f"保留既有判定清單 {review}")
            else:
                print(f"已建立 {len(pending)} 筆待判定資料於 {review}")
            return
        supplemental = read_csv(review) if review.exists() else []
        rows, scores = compare_rankings(rankings, baseline, pending, supplemental)
        out.mkdir(exist_ok=True)
        write_csv(out / "rankings.csv", rows, rows[0])
        write_csv(out / "comparison.csv", scores, scores[0])
        summary = scores[-1]
        print(f"平均 P@5：TF-IDF {summary['tfidf_p_at_5']}，BM25 {summary['bm25_p_at_5']}")
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
