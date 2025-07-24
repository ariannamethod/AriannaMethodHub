import os
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "mini_le", str(Path("arianna-core/mini_le.py"))
)
mini_le = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mini_le)


def load_logs():
    text = ""
    for path in [mini_le.LOG_FILE, mini_le.HUMAN_LOG]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
    return text


def main():
    base = mini_le.load_data()
    logs = load_logs()
    mini_le.train(base + logs)


if __name__ == "__main__":
    main()
