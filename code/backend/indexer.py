import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

from database import DB_PATH
from preprocess import tokenize
from search import SearchIndex

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "documents.db"
DEFAULT_INDEX_PATH = BASE_DIR / "data" / "index.json"

INDEX_FORMAT_VERSION = 1
TF_SCHEME = "tf = raw term count"
IDF_SCHEME = "idf = ln((N + 1) / (df + 1)) + 1"


def idf_value(num_docs: int, df: int) -> float:
    """平滑 IDF：ln((N + 1) / (df + 1)) + 1。"""
    return math.log((num_docs + 1) / (df + 1)) + 1.0


def load_documents(db_path: Path) -> list[dict]:
    """以唯讀方式讀取爬蟲資料庫的 documents 表。"""
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT doc_id, url, title, text, fetch_time "
            "FROM documents ORDER BY doc_id"
        ).fetchall()
    return [dict(row) for row in rows]


def build_index(documents: Iterable[dict]) -> dict:
    """由文件（含 doc_id、url、title、text）建立索引。

    回傳的字典（鍵皆為原生型別，doc_id 是 int）：
        num_docs         被索引的文件數 N
        documents        {doc_id: {"title", "url", "text"}}，搜尋時顯示用
        postings         {term: {doc_id: tf}}
        df               {term: 文件頻率}
        idf              {term: IDF 值}
        doc_norms        {doc_id: 文件向量範數}
        skipped_doc_ids  未被索引的文件 ID
    """
    postings: dict[str, dict[int, int]] = defaultdict(dict)
    indexed: dict[int, dict] = {}
    skipped: list[int] = []
    seen_ids: set[int] = set()

    for document in sorted(documents, key=lambda item: item["doc_id"]):
        doc_id = document["doc_id"]
        if doc_id in seen_ids:
            raise ValueError(f"doc_id 重複：{doc_id}")
        seen_ids.add(doc_id)

        url = document.get("url") or ""
        title = document.get("title") or ""
        text = document.get("text") or ""
        tokens = tokenize(f"{title} {text}")
        if not url.startswith(("http://", "https://")) or not tokens:
            skipped.append(doc_id)
            continue

        indexed[doc_id] = {"title": title or url, "url": url, "text": text}
        for term, count in Counter(tokens).items():
            postings[term][doc_id] = count

    num_docs = len(indexed)
    df = {term: len(posting) for term, posting in postings.items()}
    idf = {term: idf_value(num_docs, df[term]) for term in postings}

    squared_sums = {doc_id: 0.0 for doc_id in indexed}
    for term, posting in postings.items():
        for doc_id, tf in posting.items():
            weight = tf * idf[term]
            squared_sums[doc_id] += weight * weight
    doc_norms = {doc_id: math.sqrt(total) for doc_id, total in squared_sums.items()}

    return {
        "num_docs": num_docs,
        "documents": indexed,
        "postings": dict(postings),
        "df": df,
        "idf": idf,
        "doc_norms": doc_norms,
        "skipped_doc_ids": skipped,
    }


def save_index(index: dict, out_path: Path) -> None:
    """存成 JSON。sort_keys 讓相同輸入每次產生完全相同的檔案（可重現）。"""
    payload = {
        "format_version": INDEX_FORMAT_VERSION,
        "tf_scheme": TF_SCHEME,
        "idf_scheme": IDF_SCHEME,
        "num_docs": index["num_docs"],
        "documents": {str(i): doc for i, doc in index["documents"].items()},
        "postings": {
            term: [[doc_id, tf] for doc_id, tf in sorted(posting.items())]
            for term, posting in index["postings"].items()
        },
        "df": index["df"],
        "idf": index["idf"],
        "doc_norms": {str(i): norm for i, norm in index["doc_norms"].items()},
        "skipped_doc_ids": index["skipped_doc_ids"],
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, sort_keys=True)


def load_index(index_path: Path) -> dict:
    """載入 save_index() 存的 JSON，還原成 build_index() 的結構（doc_id 為 int）。"""
    index_path = Path(index_path)
    if not index_path.exists():
        raise FileNotFoundError(
            f"找不到索引檔 {index_path}，請先在 code/backend 執行 python indexer.py"
        )
    with open(index_path, encoding="utf-8") as file:
        payload = json.load(file)
    if payload.get("format_version") != INDEX_FORMAT_VERSION:
        raise ValueError(f"不支援的索引格式版本：{payload.get('format_version')}")

    return {
        "num_docs": payload["num_docs"],
        "documents": {int(i): doc for i, doc in payload["documents"].items()},
        "postings": {
            term: {doc_id: tf for doc_id, tf in pairs}
            for term, pairs in payload["postings"].items()
        },
        "df": payload["df"],
        "idf": payload["idf"],
        "doc_norms": {int(i): norm for i, norm in payload["doc_norms"].items()},
        "skipped_doc_ids": payload["skipped_doc_ids"],
    }


def to_search_index(index: dict) -> SearchIndex:
    """把索引字典交給搜尋核心。"""
    return SearchIndex(
        index["documents"],
        index["postings"],
        index["idf"],
        index["doc_norms"],
        tokenize,
    )


def load_search_index(index_path: Path = DEFAULT_INDEX_PATH) -> SearchIndex:
    return to_search_index(load_index(index_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="由爬蟲資料庫建立倒排索引")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_INDEX_PATH)
    args = parser.parse_args()

    documents = load_documents(args.db)
    index = build_index(documents)
    if index["num_docs"] == 0:
        raise SystemExit(f"{args.db} 沒有可索引的文件")
    save_index(index, args.out)

    posting_count = sum(len(posting) for posting in index["postings"].values())
    print(f"讀入文件數        : {len(documents)}")
    print(f"被索引文件數 N    : {index['num_docs']}")
    print(f"略過文件數        : {len(index['skipped_doc_ids'])}")
    print(f"詞彙量            : {len(index['postings'])}")
    print(f"postings 總筆數   : {posting_count}")
    print(f"索引檔            : {args.out}（{Path(args.out).stat().st_size:,} bytes）")


if __name__ == "__main__":
    main()
