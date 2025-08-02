from arianna_core.memory.bone_memory import BoneMemory
from arianna_core import mini_le


def test_bone_memory_window_and_push():
    mem = BoneMemory(limit=2)
    assert mem.on_event("x") == 1.0
    assert mem.on_event("y") == 0.5
    assert mem.on_event("y") == 1.0
    assert mem.events == ["y", "y"]


def test_chat_response_uses_bone_memory(tmp_path, monkeypatch):
    mem = BoneMemory(limit=5)
    monkeypatch.setattr(mini_le, "bone_memory", mem)
    monkeypatch.setattr(
        mini_le,
        "_cached_model",
        {"n": 2, "model": {"a": {"a": 1}}},
    )
    db_file = tmp_path / "memory.db"
    monkeypatch.setattr(mini_le, "DB_FILE", str(db_file))
    reply = mini_le.chat_response("aa")
    assert reply
    assert mem.events == ["chat"]
    assert mini_le.last_metabolic_push == 1.0
