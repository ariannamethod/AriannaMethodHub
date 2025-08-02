"""Pain marker state tracker."""


class PainMarker:
    """Track accumulated pain levels."""

    def __init__(self) -> None:
        self._level = 0.0

    def update(self, delta: float) -> None:
        """Increase pain level by ``delta`` (cannot drop below zero)."""
        self._level = max(0.0, self._level + float(delta))

    def get(self) -> float:
        """Return current pain level."""
        return self._level
