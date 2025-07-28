import os
import random
import argparse
from arianna_core import mini_le


def load_logs():
    text = ""
    for path in [mini_le.LOG_FILE, mini_le.HUMAN_LOG]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
    return text


def main(chaos: bool = False):
    base = mini_le.load_data()
    logs = load_logs()
    if chaos:
        lines = logs.splitlines()
        random.shuffle(lines)
        logs = "\n".join(lines)
    mini_le.train(base + logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate model with logs")
    parser.add_argument(
        "--chaos",
        action="store_true",
        help="shuffle log lines before training",
    )
    args = parser.parse_args()
    main(args.chaos)
