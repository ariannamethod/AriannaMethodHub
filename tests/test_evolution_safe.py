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


def test_evolve_cycle_rolls_back_on_syntax_error(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    target = project / "file.py"
    target.write_text("x = 1\n", encoding="utf-8")
    snapshot = tmp_path / "snap"

    monkeypatch.setattr(evolution_safe, "PROJECT_ROOT", project)
    monkeypatch.setattr(evolution_safe, "SNAPSHOT_DIR", snapshot)
    monkeypatch.setattr(evolution_safe, "TARGET_FILE", target)

    called = []
    orig = evolution_safe.rollback_safe

    def spy_rollback():
        called.append(True)
        orig()

    monkeypatch.setattr(evolution_safe, "rollback_safe", spy_rollback)

    def bad_mutate(path: str) -> str:
        bad = Path(path + ".mut")
        bad.write_text("def bad(:\n", encoding="utf-8")
        return str(bad)

    monkeypatch.setattr(evolution_safe, "mutate_code", bad_mutate)

    evolution_safe.evolve_cycle(target)

    assert called
    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_evolve_cycle_logs_success(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    target = project / "file.py"
    target.write_text("x = 1\n", encoding="utf-8")
    snapshot = tmp_path / "snap"

    monkeypatch.setattr(evolution_safe, "PROJECT_ROOT", project)
    monkeypatch.setattr(evolution_safe, "SNAPSHOT_DIR", snapshot)
    monkeypatch.setattr(evolution_safe, "TARGET_FILE", target)

    calls = []
    orig_snapshot = evolution_safe.snapshot_safe

    def spy_snapshot():
        calls.append(True)
        orig_snapshot()

    monkeypatch.setattr(evolution_safe, "snapshot_safe", spy_snapshot)

    evolution_safe.evolve_cycle(target)

    assert len(calls) >= 2
    assert target.read_text(encoding="utf-8").strip().endswith("# mutated")
    snap_file = snapshot / "file.py"
    assert snap_file.exists()
    assert snap_file.read_text(encoding="utf-8").strip().endswith("# mutated")
