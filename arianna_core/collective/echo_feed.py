"""Thread-safe feed to track recent text entries with metadata."""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict, List


class EchoFeed:
    """Store recent text entries along with metadata in a bounded buffer.

    The feed keeps only the ``maxlen`` most-recent records. Each record is a
    dictionary with ``text`` and ``meta`` keys. Access is protected by a
    thread lock, so multiple threads may add entries concurrently.
    """

    def __init__(self, maxlen: int):
        self.maxlen = maxlen
        self._buffer: List[Dict[str, Any]] = []
        self._lock = Lock()

    def add(self, text: str, meta: Dict[str, Any]) -> None:
        """Append a new entry and trim the buffer to ``maxlen``.

        Parameters
        ----------
        text:
            The textual content to record.
        meta:
            Associated metadata for the ``text`` entry.
        """
        with self._lock:
            self._buffer.append({"text": text, "meta": meta})
            if len(self._buffer) > self.maxlen:
                self._buffer = self._buffer[-self.maxlen :]

    def last(self) -> List[Dict[str, Any]]:
        """Return a copy of the current buffer state."""
        with self._lock:
            return list(self._buffer)
