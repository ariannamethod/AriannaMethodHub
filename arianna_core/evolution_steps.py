"""Registry of micro-evolution actions.

Each list contains minimal templates executed by the corresponding
subsystem.  Strings are intentionally short but should represent
complete actions.
"""

from typing import Dict, List


evolution_steps: Dict[str, List[str]] = {
    "chat": [
        "init->start conversation",
        "echo->repeat user input",
        "mutate->run safe cycle",
        "log->store interaction",
    ]
}
