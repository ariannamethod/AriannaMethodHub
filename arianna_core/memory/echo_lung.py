from __future__ import annotations

from dataclasses import dataclass, field
import math
import time


@dataclass
class EchoLung:
    """Model a decaying breath value influenced by event chaos."""

    capacity: float
    breath: float = 0.0
    last_event: float = field(default_factory=time.monotonic)

    def on_event(self, chaos: float) -> float:
        """Record a chaos event and update ``breath``.

        ``breath`` decays exponentially with the elapsed time since the last
        event using ``capacity`` as the time constant. The updated ``breath`` is
        clamped to the ``[0.0, 1.0]`` interval. The return value is ``chaos``
        scaled by the new ``breath`` value, allowing the caller to incorporate
        the respiratory state into its metrics.
        """
        now = time.monotonic()
        dt = now - self.last_event
        self.last_event = now

        if self.capacity > 0:
            decay = math.exp(-dt / self.capacity)
        else:
            decay = 0.0
        self.breath *= decay
        self.breath += chaos
        self.breath = min(1.0, max(0.0, self.breath))
        return chaos * self.breath
