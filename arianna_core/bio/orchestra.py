"""Biological state aggregator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .cell_resonance import CellResonance
from .pain_marker import PainMarker
from .love_field import LoveField


@dataclass
class BioOrchestra:
    """Coordinate updates to biological state components."""

    cell_resonance: CellResonance = field(default_factory=CellResonance)
    pain_marker: PainMarker = field(default_factory=PainMarker)
    love_field: LoveField = field(default_factory=LoveField)

    def update(self, event: Dict[str, float]) -> None:
        """Update all components based on ``event`` mapping."""
        self.cell_resonance.update(event.get("cell", 0.0))
        self.pain_marker.update(event.get("pain", 0.0))
        self.love_field.update(event.get("love", 0.0))

    def metrics(self) -> Dict[str, float]:
        """Return aggregated metrics from all components."""
        return {
            "cell_resonance": self.cell_resonance.get(),
            "pain_marker": self.pain_marker.get(),
            "love_field": self.love_field.get(),
        }
