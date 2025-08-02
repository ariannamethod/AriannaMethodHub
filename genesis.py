import os
import json
import random
import argparse
from arianna_core.mini_le import get_mini_le
from arianna_core import entropy_resonance


le = get_mini_le()


def load_logs():
    text = ""
    for path in [le.log_file, le.human_log]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
    return text


def main(chaos: bool = False, entropy: bool = False):
    base = le.load_data()
    logs = load_logs()
    if chaos:
        lines = logs.splitlines()
        random.shuffle(lines)
        logs = "\n".join(lines)
    model = le.train(base + logs)
    if entropy:
        model = le.reproduction_cycle()
        model, ent, changed = entropy_resonance.entropy_resonance_mutate(model)
        if changed:
            with open(le.model_file, "w", encoding="utf-8") as f:
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
