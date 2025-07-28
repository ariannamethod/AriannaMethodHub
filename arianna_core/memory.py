import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS patterns (pattern TEXT PRIMARY KEY, count INTEGER)"
    )
    conn.commit()
    conn.close()


def update_patterns(model: dict, db_path: str = DB_PATH) -> None:
    """Persist pattern frequencies from ``model`` into the SQLite database."""
    if not model:
        return
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for pattern, freq in model.items():
        if pattern.startswith("_"):
            continue
        total = sum(freq.values())
        cur.execute(
            "INSERT INTO patterns(pattern, count) VALUES (?, ?) "
            "ON CONFLICT(pattern) DO UPDATE SET count = count + excluded.count",
            (pattern, total),
        )
    conn.commit()
    conn.close()


def top_patterns(limit: int = 5, db_path: str = DB_PATH):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT pattern, count FROM patterns ORDER BY count DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
