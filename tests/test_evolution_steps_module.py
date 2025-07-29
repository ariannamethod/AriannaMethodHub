from arianna_core import evolution_steps


def test_append():
    orig_len = len(evolution_steps.evolution_steps["chat"])
    evolution_steps.evolution_steps["chat"].append("new step")
    assert evolution_steps.evolution_steps["chat"][-1] == "new step"
    evolution_steps.evolution_steps["chat"].pop()
    assert len(evolution_steps.evolution_steps["chat"]) == orig_len
