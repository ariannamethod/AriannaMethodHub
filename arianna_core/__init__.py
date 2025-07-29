import importlib
from typing import Any
from .config import settings

mini_le: Any = importlib.import_module("arianna_core.mini_le")
server = importlib.import_module("arianna_core.server")

__all__ = ["mini_le", "server", "settings"]
