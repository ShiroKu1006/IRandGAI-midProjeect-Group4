import re
from collections import Counter, defaultdict
from math import hypot, log

from app import create_app
from database import get_all_documents
from search import SearchIndex


def tokenize(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def create_preview_app():
    """Build a temporary search snapshot from the crawler's SQLite dataset."""
    documents = {}
    postings = defaultdict(dict)
    for document in get_all_documents():
        frequencies = Counter(tokenize(document["text"]))
        if not document["url"].startswith(("http://", "https://")) or not frequencies:
            continue

        doc_id = document["doc_id"]
        documents[doc_id] = {**document, "title": document["title"] or document["url"]}
        for term, count in frequencies.items():
            postings[term][doc_id] = count

    idf = {
        term: log((len(documents) + 1) / (len(posting) + 1)) + 1
        for term, posting in postings.items()
    }
    weights = defaultdict(list)
    for term, posting in postings.items():
        for doc_id, frequency in posting.items():
            weights[doc_id].append(frequency * idf[term])
    norms = {doc_id: hypot(*values) for doc_id, values in weights.items()}

    index = SearchIndex(documents, postings, idf, norms, tokenize)
    return create_app(search=index.search)
