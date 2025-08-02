import math

import pytest

import arianna_core.memory.echo_lung as el


def test_echo_lung_decay_and_scaling(monkeypatch):
    t = [0.0]
    monkeypatch.setattr(el.time, "monotonic", lambda: t[0])
    lung = el.EchoLung(capacity=1.0)

    # first event at t=0
    chaos1 = lung.on_event(0.5)
    assert chaos1 == 0.25
    assert lung.breath == 0.5

    # second event after 1 second
    t[0] = 1.0
    chaos2 = lung.on_event(0.5)
    expected_breath = 0.5 * math.exp(-1) + 0.5
    assert lung.breath == pytest.approx(expected_breath)
    assert chaos2 == pytest.approx(0.5 * expected_breath)
