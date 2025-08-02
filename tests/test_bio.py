import pytest

from arianna_core.bio import BioOrchestra, CellResonance, LoveField, PainMarker


def test_components_update_and_get() -> None:
    cr = CellResonance()
    pm = PainMarker()
    lf = LoveField()

    cr.update(0.5)
    pm.update(1.0)
    lf.update(2.5)

    assert cr.get() == pytest.approx(0.5)
    assert pm.get() == pytest.approx(1.0)
    assert lf.get() == pytest.approx(2.5)


def test_bio_orchestra_event_and_metrics() -> None:
    orch = BioOrchestra()
    event = {"cell": 0.1, "pain": 0.2, "love": 0.3}
    orch.update(event)
    orch.update({"cell": 0.2, "love": 0.1})

    metrics = orch.metrics()
    assert metrics["cell_resonance"] == pytest.approx(0.3)
    assert metrics["pain_marker"] == pytest.approx(0.2)
    assert metrics["love_field"] == pytest.approx(0.4)
