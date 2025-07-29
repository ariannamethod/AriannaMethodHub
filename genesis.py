import os
import json
import random
import argparse
from arianna_core import mini_le, entropy_resonance


def load_logs():
    text = ""
    for path in [mini_le.LOG_FILE, mini_le.HUMAN_LOG]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
    return text


def main(chaos: bool = False, entropy: bool = False):
    logs = load_logs()
    if chaos:
        lines = logs.splitlines()
        random.shuffle(lines)
        logs = "\n".join(lines)
    model = mini_le.reproduction_cycle(logs)
    if entropy:
        model, ent, changed = entropy_resonance.entropy_resonance_mutate(model)
        if changed:
            with open(mini_le.MODEL_FILE, "w", encoding="utf-8") as f:
                json.dump(model, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate model with logs")
    parser.add_argument(
        "--chaos",
        action="store_true",
        help="shuffle log lines before training",
    )
    parser.add_argument(
        "--entropy",
        action="store_true",
        help="apply entropy resonance mutation",
    )
    args = parser.parse_args()
    main(args.chaos, args.entropy)
