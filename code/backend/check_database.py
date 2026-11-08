import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "documents.db"


def check_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 1. 文件基本統計
        stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE
                    WHEN title IS NULL OR TRIM(title) = ''
                    THEN 1 ELSE 0
                END) AS empty_titles,
                SUM(CASE
                    WHEN text IS NULL OR TRIM(text) = ''
                    THEN 1 ELSE 0
                END) AS empty_texts,
                AVG(LENGTH(text)) AS avg_length,
                MIN(LENGTH(text)) AS min_length,
                MAX(LENGTH(text)) AS max_length
            FROM documents
        """).fetchone()

        print("========== Database Summary ==========")
        print(f"Total documents: {stats['total']}")
        print(f"Empty titles: {stats['empty_titles']}")
        print(f"Empty texts: {stats['empty_texts']}")
        print(f"Average text length: {stats['avg_length']:.2f}")
        print(f"Minimum text length: {stats['min_length']}")
        print(f"Maximum text length: {stats['max_length']}")

        # 2. 正文最短的 10 篇文件
        print("\n========== Shortest Documents ==========")

        rows = conn.execute("""
            SELECT title, url, LENGTH(text) AS text_length
            FROM documents
            ORDER BY text_length ASC
            LIMIT 10
        """).fetchall()

        for row in rows:
            print(f"\nTitle: {row['title']}")
            print(f"Length: {row['text_length']}")
            print(f"URL: {row['url']}")

        # 3. 出現最多次的標題
        print("\n========== Most Repeated Titles ==========")

        rows = conn.execute("""
            SELECT title, COUNT(*) AS count
            FROM documents
            GROUP BY title
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        for row in rows:
            print(f"{row['title']}: {row['count']}")


if __name__ == "__main__":
    check_database()