import unittest

from evaluation.compare_bm25 import compare_rankings, review_rows, score_row


def result(method, rank, doc_id="", query_id="q01"):
    return {
        "method": method, "query_id": query_id, "query": "sql", "rank": rank,
        "doc_id": doc_id, "url": f"https://example.com/{doc_id}" if doc_id else "",
        "title": f"Doc {doc_id}" if doc_id else "", "score": "1.0" if doc_id else "",
    }


class BM25ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.queries = [{"id": "q01", "query": "sql", "need": "SQL basics"}]
        self.rankings = [
            result("tfidf", 1, "1"), result("tfidf", 2),
            result("bm25", 1, "2"), result("bm25", 2, "1"),
        ]
        self.baseline = {("q01", "1"): {"relevant": "1", "reason": "SQL basics"}}

    def test_reuses_judgment_at_different_rank_and_keeps_denominator(self):
        pending = review_rows(self.queries, self.rankings, self.baseline)
        self.assertEqual([(row["doc_id"], row["need"]) for row in pending], [("2", "SQL basics")])
        confirmed = [dict(pending[0], relevant="1", reason="SQL tutorial", status="confirmed")]
        rows, scores = compare_rankings(self.rankings, self.baseline, pending, confirmed)
        self.assertEqual(rows[-1]["reason"], "SQL basics")
        self.assertEqual(rows[1]["relevant"], "0")
        self.assertEqual(scores[0]["tfidf_p_at_5"], "0.20")
        self.assertEqual(scores[0]["bm25_p_at_5"], "0.40")
        self.assertEqual(scores[0]["delta_p_at_5"], "0.20")
        self.assertEqual(scores[-1]["bm25_p_at_5"], "0.400")

    def test_draft_and_missing_judgments_block_comparison(self):
        pending = review_rows(self.queries, self.rankings, self.baseline)
        draft = [dict(pending[0], relevant="0", reason="Mentions SQL", status="draft")]
        for supplied in (draft, []):
            with self.subTest(supplied=supplied):
                with self.assertRaisesRegex(ValueError, "q01/2"):
                    compare_rankings(self.rankings, self.baseline, pending, supplied)

    def test_rejects_repeated_or_stale_supplemental_judgments(self):
        pending = review_rows(self.queries, self.rankings, self.baseline)
        confirmed = dict(pending[0], relevant="1", reason="SQL tutorial", status="confirmed")
        for supplied in ([confirmed, confirmed], [dict(confirmed, url="https://example.com/old")]):
            with self.subTest(supplied=supplied):
                with self.assertRaisesRegex(ValueError, "q01/2"):
                    compare_rankings(self.rankings, self.baseline, pending, supplied)

    def test_equal_means_display_unsigned_zero_delta(self):
        row = score_row("mean", "", 0.24000000000000005, 0.24, 3)
        self.assertEqual(row["delta_p_at_5"], "0.000")
