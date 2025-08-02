"""Simple retrieval-augmented generation utilities."""

from __future__ import annotations

import sqlite3
from typing import Dict, Iterable, List

import numpy as np

from .hashed_vector import cosine, hashed_vector

__all__ = ["load_corpus", "rag_search"]


def load_corpus(paths: Iterable[str], db_path: str = "rag_vectors.db", dim: int = 256) -> None:
    """Load text files and store hashed vectors in ``db_path``.

    Parameters
    ----------
    paths:
        Iterable of file paths.
    db_path:
        Location of the SQLite database to create or update.
    dim:
        Dimensionality of the hashed vectors.
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            line_start INTEGER,
            line_end INTEGER,
            snippet TEXT,
            vec BLOB
        )
        """
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    cur.execute("DELETE FROM vectors")
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('dim', ?)", (dim,))

    for path in paths:
        path = str(path)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        buffer: List[str] = []
        start: int | None = None
        for lineno, line in enumerate(lines, start=1):
            if line.strip():
                if start is None:
                    start = lineno
                buffer.append(line.rstrip("\n"))
            elif buffer:
                snippet = "\n".join(buffer)
                vec = hashed_vector(snippet, dim)
                cur.execute(
                    "INSERT INTO vectors(path, line_start, line_end, snippet, vec) VALUES (?, ?, ?, ?, ?)",
                    (path, start, lineno - 1, snippet, vec.tobytes()),
                )
                buffer = []
                start = None
        if buffer:
            snippet = "\n".join(buffer)
            vec = hashed_vector(snippet, dim)
            cur.execute(
                "INSERT INTO vectors(path, line_start, line_end, snippet, vec) VALUES (?, ?, ?, ?, ?)",
                (path, start or 1, len(lines), snippet, vec.tobytes()),
            )

    conn.commit()
    conn.close()


def rag_search(
    query: str,
    k: int,
    min_score: float,
    db_path: str = "rag_vectors.db",
) -> List[Dict[str, object]]:
    """Return top ``k`` fragments matching ``query`` above ``min_score``."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM meta WHERE key='dim'").fetchone()
    dim = int(row[0]) if row else 256
    qvec = hashed_vector(query, dim)

    results: List[Dict[str, object]] = []
    for path, lstart, lend, snippet, blob in cur.execute(
        "SELECT path, line_start, line_end, snippet, vec FROM vectors"
    ):
        vec = np.frombuffer(blob, dtype=np.float32)
        if np.random.random() < 0.01:
            vec = vec * np.random.normal(1, 0.015, size=vec.shape)
        score = cosine(qvec, vec)
        if score >= min_score:
            results.append(
                {
                    "path": path,
                    "lines": (lstart, lend),
                    "snippet": snippet,
                    "score": score,
                }
            )
    conn.close()
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]
