import os
import json
import random
import gzip
import sqlite3
from datetime import datetime


LOG_MAX_BYTES = 1_000_000
LOG_KEEP = 3
NGRAM_LEVEL = 2


class MiniLE:
    """Encapsulates the minimal language engine state and operations."""

    def __init__(
        self,
        data_dir: str | None = None,
        model_file: str | None = None,
        log_file: str | None = None,
        human_log: str | None = None,
        db_file: str | None = None,
        last_repro_file: str | None = None,
        ngram_level: int = NGRAM_LEVEL,
        log_max_bytes: int = LOG_MAX_BYTES,
        log_keep: int = LOG_KEEP,
        bad_words: set[str] | None = None,
    ) -> None:
        root = os.path.dirname(__file__)
        self.data_dir = data_dir or os.path.join(root, "..", "datasets")
        self.model_file = model_file or os.path.join(root, "model.txt")
        self.log_file = log_file or os.path.join(root, "log.txt")
        self.human_log = human_log or os.path.join(root, "humanbridge.log")
        self.db_file = db_file or os.path.join(root, "memory.db")
        self.last_repro_file = last_repro_file or os.path.join(
            root, "last_reproduction.txt"
        )
        self.ngram_level = ngram_level
        self.log_max_bytes = log_max_bytes
        self.log_keep = log_keep
        self.bad_words = bad_words or {"badword", "curse"}
        self.last_entropy: float = 0.0
        self.blocked_messages = 0
        self.last_novelty = 0.0

    # ------------------------------------------------------------------
    # Utility helpers
    def rotate_log(
        self, path: str, max_bytes: int | None = None, keep: int | None = None
    ) -> None:
        """Archive ``path`` when it exceeds ``max_bytes`` and prune old archives."""
        max_b = max_bytes or self.log_max_bytes
        keep_n = keep or self.log_keep
        if not os.path.exists(path) or os.path.getsize(path) < max_b:
            return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive = f"{path}.{ts}.gz"
        with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
            dst.write(src.read())
        os.remove(path)

        base = os.path.basename(path)
        dir_path = os.path.dirname(path)
        archives = sorted(
            [
                f
                for f in os.listdir(dir_path)
                if f.startswith(base) and f.endswith(".gz")
            ],
            reverse=True,
        )
        for old in archives[keep_n:]:
            os.remove(os.path.join(dir_path, old))

    # ------------------------------------------------------------------
    # Core model operations
    def load_data(self) -> str:
        """Return concatenated text from files in ``data_dir``."""
        chunks: list[str] = []
        if os.path.isdir(self.data_dir):
            for name in os.listdir(self.data_dir):
                path = os.path.join(self.data_dir, name)
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as f:
                        chunks.append(f.read())
        return "\n".join(chunks)

    def train(self, text: str, n: int | None = None) -> dict:
        """Train an n-gram model from ``text`` and write it to ``model_file``."""
        n = n or self.ngram_level
        model: dict[str, dict[str, int]] = {}
        for i in range(len(text) - n + 1):
            ctx = text[i : i + n - 1]
            ch = text[i + n - 1]
            freq = model.setdefault(ctx, {})
            freq[ch] = freq.get(ch, 0) + 1
        data = {"n": n, "model": model}
        with open(self.model_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data

    def load_model(self) -> dict | None:
        if not os.path.exists(self.model_file):
            return None
        with open(self.model_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate(
        self, model: dict, length: int = 80, seed: str | None = None
    ) -> str:
        """Generate ``length`` characters from ``model``."""
        if not model:
            return ""
        n = model.get("n", 2)
        m = model.get("model", {})
        rng = random
        if not m:
            return ""
        context = seed[-(n - 1) :] if seed else rng.choice(list(m.keys()))
        output = context
        for _ in range(length - len(context)):
            freq = m.get(context)
            if not freq:
                context = rng.choice(list(m.keys()))
                output += context
                if len(output) >= length:
                    break
                continue
            chars = list(freq.keys())
            weights = list(freq.values())
            ch = rng.choices(chars, weights=weights)[0]
            output += ch
            context = output[-(n - 1) :]
        return output[:length]

    def chat_response(self, message: str) -> str:
        """Return a generated reply to ``message`` using the saved model."""
        model = self.load_model()
        if model is None:
            model = self.train(self.load_data(), n=self.ngram_level)
        return self.generate(model, length=60, seed=message)

    # ------------------------------------------------------------------
    # Pattern memory operations
    def _init_db(self) -> sqlite3.Connection:
        """Return a connection to the pattern memory database."""
        conn = sqlite3.connect(self.db_file)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS patterns (pattern TEXT PRIMARY KEY, count INTEGER)"
        )
        return conn

    def update_pattern_memory(self, text: str, n: int | None = None) -> None:
        """Add n-gram patterns from ``text`` to ``memory.db``."""
        n = n or self.ngram_level
        conn = self._init_db()
        rows: list[str] = []
        for i in range(len(text) - n + 1):
            rows.append(text[i : i + n])
        with conn:
            for pat in rows:
                conn.execute(
                    "INSERT INTO patterns(pattern, count) VALUES(?,1) "
                    "ON CONFLICT(pattern) DO UPDATE SET count = count + 1",
                    (pat,),
                )
        conn.close()

    def maintain_pattern_memory(
        self, threshold: int = 1, max_rows: int = 1000
    ) -> None:
        """Prune low-frequency patterns and cap table size."""
        conn = self._init_db()
        with conn:
            conn.execute("DELETE FROM patterns WHERE count < ?", (threshold,))
            cur = conn.execute(
                "SELECT pattern, count FROM patterns ORDER BY count DESC"
            )
            rows = cur.fetchall()
            if len(rows) > max_rows:
                for pat, _ in rows[max_rows:]:
                    conn.execute(
                        "DELETE FROM patterns WHERE pattern = ?", (pat,)
                    )
        conn.close()

    def metabolize_input(self, text: str, n: int | None = None) -> float:
        """Return novelty score between 0 and 1 for ``text``."""
        n = n or self.ngram_level
        conn = self._init_db()
        unseen = 0
        total = 0
        for i in range(len(text) - n + 1):
            pat = text[i : i + n]
            total += 1
            cur = conn.execute(
                "SELECT 1 FROM patterns WHERE pattern = ? LIMIT 1", (pat,)
            )
            if cur.fetchone() is None:
                unseen += 1
        conn.close()
        score = unseen / total if total else 0.0
        self.last_novelty = score
        return score

    def immune_filter(self, text: str) -> str:
        """Return ``""`` if ``text`` contains banned words."""
        tokens = [t.lower() for t in text.split()]
        if any(t in self.bad_words for t in tokens):
            self.blocked_messages += 1
            return ""
        return text

    def adaptive_mutation(self, model: dict) -> dict:
        """Randomly tweak model weights if novelty improves."""
        if not model or not model.get("model"):
            return model
        before = self.generate(model, length=40)
        score_before = self.metabolize_input(before)
        ctx = random.choice(list(model["model"].keys()))
        freq = model["model"][ctx]
        ch = random.choice(list(freq.keys()))
        old = freq[ch]
        freq[ch] = max(1, old + random.choice([-1, 1]))
        after = self.generate(model, length=40)
        score_after = self.metabolize_input(after)
        if score_after < score_before:
            freq[ch] = old
        return model

    def reproduction_cycle(
        self, threshold: int = 1, max_rows: int = 1000
    ) -> dict:
        """Retrain model, update memory and apply mutation."""
        text = self.load_data()
        model = self.train(text, n=self.ngram_level)
        self.update_pattern_memory(text)
        self.maintain_pattern_memory(
            threshold=threshold, max_rows=max_rows
        )
        model = self.adaptive_mutation(model)
        ts = datetime.utcnow().isoformat()
        with open(self.last_repro_file, "w", encoding="utf-8") as f:
            f.write(ts)
        return model

    def health_report(self) -> dict:
        """Return health metrics about the system."""
        conn = self._init_db()
        cur = conn.execute("SELECT COUNT(*) FROM patterns")
        mem_rows = cur.fetchone()[0]
        conn.close()
        model = self.load_model()
        model_size = len(model.get("model", {})) if model else 0
        last_rep = None
        if os.path.exists(self.last_repro_file):
            with open(self.last_repro_file, "r", encoding="utf-8") as f:
                last_rep = f.read().strip()
        return {
            "model_size": model_size,
            "pattern_memory": mem_rows,
            "blocked_messages": self.blocked_messages,
            "novelty": self.last_novelty,
            "last_reproduction": last_rep,
        }


_INSTANCE: MiniLE | None = None


def get_mini_le() -> MiniLE:
    """Return a module-wide ``MiniLE`` instance."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = MiniLE()
    return _INSTANCE


# ----------------------------------------------------------------------
# Backwards-compatible function wrappers


def rotate_log(path: str, max_bytes: int = LOG_MAX_BYTES, keep: int = LOG_KEEP) -> None:
    get_mini_le().rotate_log(path, max_bytes=max_bytes, keep=keep)


def load_data() -> str:
    return get_mini_le().load_data()


def train(text: str, n: int = NGRAM_LEVEL) -> dict:
    return get_mini_le().train(text, n=n)


def load_model() -> dict | None:
    return get_mini_le().load_model()


def generate(model: dict, length: int = 80, seed: str | None = None) -> str:
    return get_mini_le().generate(model, length=length, seed=seed)


def chat_response(message: str) -> str:
    return get_mini_le().chat_response(message)


def update_pattern_memory(text: str, n: int = NGRAM_LEVEL) -> None:
    get_mini_le().update_pattern_memory(text, n=n)


def maintain_pattern_memory(threshold: int = 1, max_rows: int = 1000) -> None:
    get_mini_le().maintain_pattern_memory(threshold=threshold, max_rows=max_rows)


def metabolize_input(text: str, n: int = NGRAM_LEVEL) -> float:
    return get_mini_le().metabolize_input(text, n=n)


def immune_filter(text: str) -> str:
    return get_mini_le().immune_filter(text)


def adaptive_mutation(model: dict) -> dict:
    return get_mini_le().adaptive_mutation(model)


def reproduction_cycle(threshold: int = 1, max_rows: int = 1000) -> dict:
    return get_mini_le().reproduction_cycle(
        threshold=threshold, max_rows=max_rows
    )


def health_report() -> dict:
    return get_mini_le().health_report()

