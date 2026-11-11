# Search latency

Scope: `SearchIndex.search(query, top_k=10)` — raw query in, top-10 hits (title / url / snippet) out. Excludes index loading, database, Flask/HTTP, frontend.

Samples: 500 (10 queries x 50 runs, 3 warm-up runs per query not counted). Index: 250 documents, 8087 terms. Python 3.14.9 on macOS-26.6-arm64-arm-64bit-Mach-O.

## Overall (ms)

| n | mean | median | stdev | min | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| 500 | 0.490 | 0.516 | 0.259 | 0.127 | 1.007 | 1.169 | 1.242 |

Index load (one-off, not part of query latency): 20.0 ms

## Per query (ms)

| id | query | mean | median | p95 | max |
|---|---|---|---|---|---|
| q01 | window functions | 0.623 | 0.618 | 0.699 | 0.713 |
| q02 | recursive common table expressions | 0.534 | 0.525 | 0.577 | 0.613 |
| q03 | transaction isolation levels | 0.136 | 0.131 | 0.154 | 0.187 |
| q04 | explicit table locks | 0.305 | 0.304 | 0.320 | 0.351 |
| q05 | how to get inserted rows back | 0.500 | 0.492 | 0.543 | 0.560 |
| q06 | array functions and operators | 0.954 | 0.983 | 1.182 | 1.242 |
| q07 | create view | 0.195 | 0.187 | 0.248 | 0.287 |
| q08 | reclaim storage from dead rows | 0.759 | 0.691 | 1.079 | 1.208 |
| q09 | sort rows order by | 0.618 | 0.611 | 0.678 | 0.693 |
| q10 | retry after serialization failure | 0.273 | 0.270 | 0.305 | 0.347 |
