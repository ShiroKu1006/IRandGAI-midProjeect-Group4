
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone


# 資料庫位置
DB_PATH = Path(__file__).resolve().parent / "data" / "documents.db"


def init_database():
    """初始化資料庫與 documents 資料表"""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                text TEXT NOT NULL,
                fetch_time TEXT NOT NULL
            )
        """)




def save_document(document):
    """新增或更新一筆文件"""

    fetch_time = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO documents (url, title, text, fetch_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                text = excluded.text,
                fetch_time = excluded.fetch_time
        """, (
            document["url"],
            document["title"],
            document["text"],
            fetch_time
        ))



def get_document_count():
    """取得目前資料庫中的文件數量"""

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM documents"
        )
        return cursor.fetchone()[0]

def get_all_documents():
    """取得資料庫中的所有文件"""

    with closing(sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT doc_id, url, title, text, fetch_time
            FROM documents
            ORDER BY doc_id
        """)

        return [dict(row) for row in cursor.fetchall()]