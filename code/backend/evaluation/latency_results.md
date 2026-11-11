# Search latency

Scope: `SearchIndex.search(query, top_k=10)` — raw query in, top-10 hits (title / url / snippet) out. Excludes index loading, database, Flask/HTTP, frontend.

Samples: 500 (10 queries x 50 runs, 3 warm-up runs per query not counted). Index: 250 documents, 8087 terms. Python 3.10.12 on Linux-6.8.0-138-generic-aarch64-with-glibc2.35.

## Overall (ms)

| n | mean | median | stdev | min | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| 500 | 0.445 | 0.494 | 0.190 | 0.132 | 0.707 | 0.792 | 0.859 |

Index load (one-off, not part of query latency): 21.8 ms

## Per query (ms)

| id | query | mean | median | p95 | max |
|---|---|---|---|---|---|
| q01 | window functions | 0.579 | 0.572 | 0.631 | 0.674 |
| q02 | recursive common table expressions | 0.505 | 0.498 | 0.560 | 0.587 |
| q03 | transaction isolation levels | 0.149 | 0.143 | 0.181 | 0.244 |
| q04 | explicit table locks | 0.326 | 0.318 | 0.395 | 0.490 |
| q05 | how to get inserted rows back | 0.490 | 0.484 | 0.546 | 0.622 |
| q06 | array functions and operators | 0.727 | 0.707 | 0.825 | 0.859 |
| q07 | create view | 0.189 | 0.181 | 0.227 | 0.254 |
| q08 | reclaim storage from dead rows | 0.600 | 0.593 | 0.675 | 0.710 |
| q09 | sort rows order by | 0.607 | 0.598 | 0.670 | 0.685 |
| q10 | retry after serialization failure | 0.272 | 0.260 | 0.321 | 0.368 |
