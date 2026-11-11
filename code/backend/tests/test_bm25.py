import math
import unittest

from search import SearchIndex


def make_index(postings, count):
    documents = {
        i: {"title": str(i), "url": f"https://example.com/{i}", "text": " example "}
        for i in range(count, 0, -1)
    }
    return SearchIndex(documents, postings, {}, {}, str.split)


class BM25Tests(unittest.TestCase):
    def test_score_accounts_for_length_and_saturates_term_frequency(self):
        index = make_index({"x": {1: 1, 2: 4, 3: 1}, "y": {2: 6, 3: 4}}, 3)
        count, hits = index.search_bm25("x")
        self.assertEqual(count, 3)
        self.assertEqual([hit["doc_id"] for hit in hits], [1, 2, 3])
        # Lengths 1, 10, 5, avgdl 16/3. The denominators are 1.46875,
        # 5.9875, and 2.14375 for the respective ranked documents.
        idf = math.log(8 / 7)
        for hit, expected_factor in zip(hits, (2.2 / 1.46875, 8.8 / 5.9875, 2.2 / 2.14375)):
            self.assertAlmostEqual(hit["score"], idf * expected_factor)
        self.assertEqual(hits[0]["snippet"], "example")
        self.assertEqual(index.search_bm25("x x unknown"), (count, hits))

    def test_ties_and_top_k(self):
        index = make_index({"x": dict.fromkeys(range(12, 0, -1), 1)}, 12)
        self.assertEqual([hit["doc_id"] for hit in index.search_bm25("x", 2)[1]], [1, 2])
        self.assertEqual(len(index.search_bm25("x", 20)[1]), 10)

    def test_no_matches(self):
        index = make_index({"x": {1: 1}}, 1)
        for query, top_k in [(" ", 10), ("unknown", 10), ("x", 0)]:
            with self.subTest(query=query, top_k=top_k):
                self.assertEqual(index.search_bm25(query, top_k), (1, []))
        self.assertEqual(make_index({}, 0).search_bm25("x"), (0, []))
