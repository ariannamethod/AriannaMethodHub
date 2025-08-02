import importlib
from typing import Any
from .config import settings

mini_le: Any = importlib.import_module("arianna_core.mini_le")
server = importlib.import_module("arianna_core.server")
evolution_steps = importlib.import_module("arianna_core.evolution_steps")
bio = importlib.import_module("arianna_core.bio")

__all__ = ["mini_le", "server", "evolution_steps", "settings", "bio"]
