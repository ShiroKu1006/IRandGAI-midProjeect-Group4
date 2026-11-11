import re
from collections import Counter, defaultdict
from functools import cached_property
from math import hypot, log1p

from preprocess import tokenize


BM25_K1 = 1.2
BM25_B = 0.75


class SearchIndex:
    """Search an in-memory snapshot prepared by the offline indexer."""

    def __init__(self, documents, postings, idf, document_norms, tokenize):
        self.documents = documents
        self.postings = postings
        self.idf = idf
        self.document_norms = document_norms
        self.tokenize = tokenize

    def search(self, query, top_k=10):
        indexed_count = len(self.documents)
        quoted = re.fullmatch(r'"([^"]*)"', query.strip())
        terms = Counter(tokenize(quoted[1]) if quoted else self.tokenize(query))
        query_weights = {
            term: frequency * self.idf[term]
            for term, frequency in terms.items()
            if term in self.idf
        }
        query_norm = hypot(*query_weights.values())
        if query_norm == 0 or top_k <= 0:
            return indexed_count, []

        phrase_matches = None
        if quoted:
            phrase_matches = self._phrase_matches(quoted[1], terms)
            if not phrase_matches:
                return indexed_count, []

        dot_products = defaultdict(float)
        for term, query_weight in query_weights.items():
            for doc_id, frequency in self.postings.get(term, {}).items():
                if phrase_matches is not None and doc_id not in phrase_matches:
                    continue
                document_weight = frequency * self.idf[term]
                dot_products[doc_id] += query_weight * document_weight

        ranked = []
        for doc_id, dot_product in dot_products.items():
            document_norm = self.document_norms[doc_id]
            if dot_product > 0 and document_norm > 0:
                score = dot_product / (query_norm * document_norm)
                ranked.append((doc_id, score))
        return indexed_count, self._top_hits(ranked, top_k)

    def _phrase_matches(self, phrase, terms):
        phrase_tokens = tokenize(phrase, keep_stopwords=True)
        width = len(phrase_tokens)
        postings = [self.postings.get(term, {}) for term in terms]
        matches = set()
        for doc_id in min(postings, key=len):
            if not all(doc_id in posting for posting in postings):
                continue
            tokens = tokenize(self.documents[doc_id]["text"], keep_stopwords=True)
            if any(
                tokens[start:start + width] == phrase_tokens
                for start in range(len(tokens) - width + 1)
            ):
                matches.add(doc_id)
        return matches

    @cached_property
    def _bm25_statistics(self):
        lengths = dict.fromkeys(self.documents, 0)
        for posting in self.postings.values():
            for doc_id, frequency in posting.items():
                lengths[doc_id] += frequency
        count = len(lengths)
        avg_length = sum(lengths.values()) / count if count else 0
        idf = {
            term: log1p((count - len(posting) + 0.5) / (len(posting) + 0.5))
            for term, posting in self.postings.items()
        }
        return lengths, avg_length, idf

    def search_bm25(self, query, top_k=10):
        indexed_count = len(self.documents)
        terms = dict.fromkeys(self.tokenize(query))
        if not terms or top_k <= 0 or not indexed_count:
            return indexed_count, []

        lengths, avg_length, idf = self._bm25_statistics
        if not avg_length:
            return indexed_count, []

        scores = defaultdict(float)
        for term in terms:
            for doc_id, frequency in self.postings.get(term, {}).items():
                normalization = BM25_K1 * (1 - BM25_B + BM25_B * lengths[doc_id] / avg_length)
                scores[doc_id] += idf[term] * frequency * (BM25_K1 + 1) / (
                    frequency + normalization
                )
        ranked = [(doc_id, score) for doc_id, score in scores.items() if score > 0]
        return indexed_count, self._top_hits(ranked, top_k)

    def _top_hits(self, ranked, top_k):
        ranked.sort(key=lambda hit: (-hit[1], hit[0]))
        hits = []
        for doc_id, score in ranked[:min(top_k, 10)]:
            document = self.documents[doc_id]
            hits.append({
                "doc_id": doc_id,
                "title": document["title"],
                "url": document["url"],
                "snippet": " ".join(document["text"].split()[:75]),
                "score": score,
            })
        return hits
