from pathlib import Path
from arianna_core import evolution_safe


def test_evolve_cycle_applies_mutation(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    target = project / "file.py"
    target.write_text("x = 1\n", encoding="utf-8")
    snapshot = tmp_path / "snap"

    monkeypatch.setattr(evolution_safe, "PROJECT_ROOT", project)
    monkeypatch.setattr(evolution_safe, "SNAPSHOT_DIR", snapshot)
    monkeypatch.setattr(evolution_safe, "TARGET_FILE", target)

    evolution_safe.evolve_cycle(target)

    assert snapshot.exists()
    assert target.read_text(encoding="utf-8").strip().endswith("# mutated")


def test_evolve_cycle_rolls_back(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    target = project / "file.py"
    target.write_text("x = 1\n", encoding="utf-8")
    snapshot = tmp_path / "snap"

    monkeypatch.setattr(evolution_safe, "PROJECT_ROOT", project)
    monkeypatch.setattr(evolution_safe, "SNAPSHOT_DIR", snapshot)
    monkeypatch.setattr(evolution_safe, "TARGET_FILE", target)

    def bad_mutate(path: str) -> str:
        bad = Path(path + ".mut")
        bad.write_text("def bad(:\n", encoding="utf-8")
        return str(bad)

    monkeypatch.setattr(evolution_safe, "mutate_code", bad_mutate)

    evolution_safe.evolve_cycle(target)

    assert target.read_text(encoding="utf-8") == "x = 1\n"
