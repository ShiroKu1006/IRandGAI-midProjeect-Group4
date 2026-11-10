from os import environ

from app import create_app
from indexer import DEFAULT_INDEX_PATH, load_search_index


def create_indexed_app(index_path=None):
    if index_path is None:
        index_path = environ.get("SEARCH_INDEX_PATH") or DEFAULT_INDEX_PATH
    return create_app(search=load_search_index(index_path).search)
