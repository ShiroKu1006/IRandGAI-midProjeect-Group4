import argparse
import gc
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

from indexer import DEFAULT_INDEX_PATH, load_search_index

HERE = Path(__file__).parent
TOP_K = 10


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(sorted_values, p):
    """Linear-interpolated percentile (p in 0..100) of an ascending list."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def summarize(samples_ms):
    s = sorted(samples_ms)
    return {
        "n": len(s),
        "mean_ms": statistics.fmean(s),
        "median_ms": statistics.median(s),
        "stdev_ms": statistics.stdev(s) if len(s) > 1 else 0.0,
        "min_ms": s[0],
        "p95_ms": percentile(s, 95),
        "p99_ms": percentile(s, 99),
        "max_ms": s[-1],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--runs", type=int, default=50, help="timed runs per query")
    parser.add_argument("--warmup", type=int, default=3, help="untimed runs per query")
    args = parser.parse_args()

    queries_path = HERE / "queries.json"
    queries = json.loads(queries_path.read_text(encoding="utf-8"))["queries"]

    t0 = time.perf_counter_ns()
    search_index = load_search_index(args.index)
    load_ms = (time.perf_counter_ns() - t0) / 1e6

    per_query, all_samples = [], []
    for q in queries:
        for _ in range(args.warmup):
            search_index.search(q["query"], top_k=TOP_K)
        samples = []
        gc.disable()
        try:
            for _ in range(args.runs):
                start = time.perf_counter_ns()
                search_index.search(q["query"], top_k=TOP_K)
                samples.append((time.perf_counter_ns() - start) / 1e6)
        finally:
            gc.enable()
        per_query.append({"id": q["id"], "query": q["query"], **summarize(samples)})
        all_samples.extend(samples)

    overall = summarize(all_samples)
    result = {
        "scope": "SearchIndex.search(query, top_k=10): raw query string in, top-10 hits "
                 "(title/url/snippet) out. Excludes index loading, database, Flask/HTTP, frontend.",
        "method": {"warmup_runs_per_query": args.warmup, "timed_runs_per_query": args.runs,
                   "timer": "time.perf_counter_ns", "gc_paused_while_timing": True,
                   "queries": "evaluation/queries.json (same 10 frozen queries as Precision@5)"},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "machine": platform.machine(),
                        "indexed_documents": len(search_index.documents),
                        "indexed_terms": len(search_index.idf),
                        "index_sha256": sha256(args.index),
                        "queries_sha256": sha256(queries_path)},
        "index_load_ms": load_ms,
        "overall": overall,
        "per_query": per_query,
    }
    (HERE / "latency_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Search latency", "",
        "Scope: `SearchIndex.search(query, top_k=10)` - raw query in, top-10 hits "
        "(title / url / snippet) out. Excludes index loading, database, Flask/HTTP, frontend.", "",
        f"Samples: {overall['n']} ({len(queries)} queries x {args.runs} runs, "
        f"{args.warmup} warm-up runs per query not counted). "
        f"Index: {len(search_index.documents)} documents, {len(search_index.idf)} terms. "
        f"Python {result['environment']['python']} on {result['environment']['platform']}.", "",
        "## Overall (ms)", "",
        "| n | mean | median | stdev | min | p95 | p99 | max |",
        "|---|---|---|---|---|---|---|---|",
        "| {n} | {mean_ms:.3f} | {median_ms:.3f} | {stdev_ms:.3f} | {min_ms:.3f} | "
        "{p95_ms:.3f} | {p99_ms:.3f} | {max_ms:.3f} |".format(**overall), "",
        f"Index load (one-off, not part of query latency): {load_ms:.1f} ms", "",
        "## Per query (ms)", "",
        "| id | query | mean | median | p95 | max |", "|---|---|---|---|---|---|",
    ]
    for r in per_query:
        lines.append(f"| {r['id']} | {r['query']} | {r['mean_ms']:.3f} | "
                     f"{r['median_ms']:.3f} | {r['p95_ms']:.3f} | {r['max_ms']:.3f} |")
    (HERE / "latency_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
