from pathlib import Path
import sys

try:
    import arianna_core  # noqa: F401
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
