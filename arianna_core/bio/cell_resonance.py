"""Cell resonance state tracker."""


class CellResonance:
    """Track resonance level within a cell-like system."""

    def __init__(self) -> None:
        self._level = 0.0

    def update(self, delta: float) -> None:
        """Adjust resonance by ``delta``."""
        self._level += float(delta)

    def get(self) -> float:
        """Return current resonance level."""
        return self._level
