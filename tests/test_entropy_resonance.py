from arianna_core import entropy_resonance


def test_entropy_mutation_deep_copy():
    model = {"model": {"a": {"b": 1}}}
    mutated = entropy_resonance.entropy_mutation(model, "b")
    assert mutated is not model
    assert mutated["model"] is not model["model"]
    assert mutated["model"]["a"] is not model["model"]["a"]
    assert model["model"]["a"]["b"] == 1
    assert mutated["model"]["a"]["b"] == 2
    mutated["model"]["a"]["b"] = 99
    assert model["model"]["a"]["b"] == 1
