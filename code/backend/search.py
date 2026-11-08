from collections import Counter, defaultdict
from math import hypot


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
        query_weights = {
            term: frequency * self.idf[term]
            for term, frequency in Counter(self.tokenize(query)).items()
            if term in self.idf
        }
        query_norm = hypot(*query_weights.values())
        if query_norm == 0 or top_k <= 0:
            return indexed_count, []

        dot_products = defaultdict(float)
        for term, query_weight in query_weights.items():
            for doc_id, frequency in self.postings.get(term, {}).items():
                document_weight = frequency * self.idf[term]
                dot_products[doc_id] += query_weight * document_weight

        ranked = []
        for doc_id, dot_product in dot_products.items():
            document_norm = self.document_norms[doc_id]
            if dot_product > 0 and document_norm > 0:
                score = dot_product / (query_norm * document_norm)
                ranked.append((doc_id, score))
        ranked.sort(key=lambda hit: (-hit[1], hit[0]))

        hits = []
        for doc_id, score in ranked[:min(top_k, 10)]:
            document = self.documents[doc_id]
            hits.append({
                "doc_id": doc_id,
                "title": document["title"],
                "url": document["url"],
                "snippet": " ".join(document["text"].split())[:160],
                "score": score,
            })
        return indexed_count, hits
