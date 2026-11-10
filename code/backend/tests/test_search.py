import math
import re
import unittest

import app


class SearchApiTests(unittest.TestCase):
    def test_health(self):
        response = app.app.test_client().get("/api/health")
        self.assertEqual((response.status_code, response.json), (200, {"status": "ok"}))

    def test_invalid_query(self):
        client = app.app.test_client()
        for path in ("/api/search", "/api/search?q=", "/api/search?q=%20%09"):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(
                    (response.status_code, response.json),
                    (400, {"error": "invalid_query"}),
                )

    def test_search_unavailable(self):
        response = app.app.test_client().get("/api/search?q=SQL")
        self.assertEqual(
            (response.status_code, response.json),
            (503, {"error": "search_unavailable"}),
        )

    def test_success_projects_public_fields(self):
        hit = {
            "title": "PostgreSQL Indexes",
            "url": "https://www.postgresql.org/docs/18/indexes.html",
            "snippet": "Indexes can help retrieve rows faster.",
            "score": 0.82,
        }

        def fixed_search(query, top_k):
            self.assertEqual((query, top_k), ("SQL", 10))
            return 3, [{"doc_id": 1, **hit}]

        response = app.create_app(search=fixed_search).test_client().get(
            "/api/search?q=%20SQL%20"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"indexed_count": 3, "results": [hit]})


def tokenize(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def document(text):
    return {
        "title": "PostgreSQL",
        "url": "https://www.postgresql.org/docs/18/",
        "text": text,
    }


class SearchIndexTests(unittest.TestCase):
    def test_rank_and_scores_through_api(self):
        from search import SearchIndex

        a = 1 + math.log(4 / 3)
        b = 1 + math.log(4 / 2)
        index = SearchIndex(
            {
                1: document("SQL  SQL\nindex"),
                2: document("SQL join"),
                3: document("join"),
            },
            {"sql": {1: 2, 2: 1}, "index": {1: 1}, "join": {2: 1, 3: 1}},
            {"sql": a, "join": a, "index": b},
            {1: math.hypot(2 * a, b), 2: math.hypot(a, a), 3: a},
            tokenize,
        )
        client = app.create_app(search=index.search).test_client()
        response = client.get("/api/search?q=SQL")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["indexed_count"], 3)
        hits = response.json["results"]
        self.assertEqual([hit["snippet"] for hit in hits], ["SQL SQL index", "SQL join"])
        self.assertAlmostEqual(hits[0]["score"], 2 * a / math.sqrt(4 * a**2 + b**2))
        self.assertAlmostEqual(hits[1]["score"], 1 / math.sqrt(2))
        self.assertEqual(client.get("/api/search?q=sql+unknown").json, response.json)

        combined = client.get("/api/search?q=sql+sql+join").json["results"]
        self.assertEqual(
            [hit["snippet"] for hit in combined],
            ["SQL join", "SQL SQL index", "join"],
        )
        self.assertAlmostEqual(combined[0]["score"], 3 / math.sqrt(10))
        self.assertAlmostEqual(
            combined[1]["score"], 4 * a / math.sqrt(5 * (4 * a**2 + b**2))
        )
        self.assertAlmostEqual(combined[2]["score"], 1 / math.sqrt(5))

        no_match = client.get("/api/search?q=unknown")
        self.assertEqual(no_match.status_code, 200)
        self.assertEqual(no_match.json, {"indexed_count": 3, "results": []})

    def test_ties_top_k_and_snippet_length(self):
        from search import SearchIndex

        ids = range(12, 0, -1)
        text = "sql" + " " * 3 + "x" * 200
        index = SearchIndex(
            {doc_id: document(text) for doc_id in ids},
            {"sql": dict.fromkeys(ids, 1)},
            {"sql": 1.0},
            dict.fromkeys(ids, 1.0),
            tokenize,
        )
        count, hits = index.search("sql", top_k=20)
        self.assertEqual(count, 12)
        self.assertEqual([hit["doc_id"] for hit in hits], list(range(1, 11)))
        self.assertEqual(hits[0]["snippet"], "sql " + "x" * 200)
        self.assertEqual(len(index.search("sql", top_k=2)[1]), 2)

    def test_zero_weight_query_returns_no_hits(self):
        from search import SearchIndex

        index = SearchIndex(
            {1: document("sql")},
            {"sql": {1: 1}},
            {"sql": 0.0},
            {1: 0.0},
            tokenize,
        )
        self.assertEqual(index.search("sql"), (1, []))
