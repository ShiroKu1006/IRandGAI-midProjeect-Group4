"""Evaluation metrics. Precision@k always divides by k (missing results count as non-relevant)."""
import re


def precision_at_k(relevance, k=5):
    """relevance: list of 0/1 for ranked results (may be shorter than k)."""
    if k <= 0:
        raise ValueError("k must be positive")
    return sum(1 for r in relevance[:k] if r) / k


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def page_key(url):
    """Page identity ignoring the docs version: /docs/<version>/x.html -> x.html."""
    match = re.search(r"/docs/[^/]+/(.*)$", url)
    return match.group(1) if match else url


def distinct_pages(urls):
    return len({page_key(u) for u in urls})
