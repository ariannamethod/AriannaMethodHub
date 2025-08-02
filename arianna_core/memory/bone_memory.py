from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class BoneMemory:
    """Track recent events and compute a metabolic push coefficient."""

    limit: int
    events: List[str] = field(default_factory=list)
    metabolic_push: float = 0.0

    def on_event(self, event_type: str) -> float:
        """Record an event and update ``metabolic_push``.

        The coefficient is the fraction of events of ``event_type`` in the
        current window defined by ``limit``.
        """
        self.events.append(event_type)
        if len(self.events) > self.limit:
            # keep only the most recent ``limit`` events
            self.events = self.events[-self.limit:]
        count = self.events.count(event_type)
        self.metabolic_push = count / len(self.events) if self.events else 0.0
        return self.metabolic_push
