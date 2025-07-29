import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = PROJECT_ROOT.with_name(PROJECT_ROOT.name + "_snapshot")
TARGET_FILE = PROJECT_ROOT / "arianna_core" / "evolution_steps.py"


def snapshot_safe() -> None:
    """Copy the project to ``SNAPSHOT_DIR``."""
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    shutil.copytree(PROJECT_ROOT, SNAPSHOT_DIR)


def rollback_safe() -> None:
    """Restore files from ``SNAPSHOT_DIR``."""
    if SNAPSHOT_DIR.exists():
        shutil.copytree(SNAPSHOT_DIR, PROJECT_ROOT, dirs_exist_ok=True)


def mutate_code(path: str) -> str:
    """Write a simple mutation of ``path`` and return the new file path."""
    mutated_path = path + ".mut"
    with open(path, "r", encoding="utf-8") as src:
        content = src.read()
    with open(mutated_path, "w", encoding="utf-8") as dst:
        dst.write(content)
        dst.write("\n# mutated\n")
    return mutated_path


def test_mutation(mutated_path: str) -> bool:
    """Return ``True`` if ``mutated_path`` parses without syntax errors."""
    cmd = [
        sys.executable,
        "-c",
        "import ast,sys; ast.parse(open(sys.argv[1]).read())",
        mutated_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def apply_mutation(mutated_path: str) -> None:
    """Replace the original file with ``mutated_path`` and refresh the
    snapshot."""
    original = (
        mutated_path[:-4] if mutated_path.endswith(".mut") else mutated_path
    )
    shutil.move(mutated_path, original)
    snapshot_safe()


def evolve_cycle(path: Path = TARGET_FILE) -> None:
    """Perform a safe mutation cycle on ``path``."""
    snapshot_safe()
    mutated = mutate_code(str(path))
    if test_mutation(mutated):
        apply_mutation(mutated)
    else:
        rollback_safe()
