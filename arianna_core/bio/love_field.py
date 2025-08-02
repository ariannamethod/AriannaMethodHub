"""Love field state tracker."""


class LoveField:
    """Track diffused love energy."""

    def __init__(self) -> None:
        self._intensity = 0.0

    def update(self, delta: float) -> None:
        """Increase love intensity by ``delta``."""
        self._intensity += float(delta)

    def get(self) -> float:
        """Return current love intensity."""
        return self._intensity
