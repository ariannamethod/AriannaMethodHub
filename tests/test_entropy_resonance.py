from arianna_core.entropy_resonance import entropy_mutation


def test_entropy_mutation_preserves_structure_and_types() -> None:
    model = {"model": {"ctx": {"a": 1}, 1: {"b": 2}}}
    sample = "ab"
    mutated = entropy_mutation(model, sample)

    # Original model should remain unchanged
    assert model == {"model": {"ctx": {"a": 1}, 1: {"b": 2}}}

    # Mutated model should have incremented counts
    assert mutated["model"]["ctx"]["a"] == 2
    assert mutated["model"][1]["b"] == 3

    # Key types should be preserved
    assert 1 in mutated["model"]
    assert "1" not in mutated["model"]

    # Ensure deep copy (inner dicts are different objects)
    assert mutated is not model
    assert mutated["model"] is not model["model"]
