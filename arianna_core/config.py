from dataclasses import dataclass
import os
import pathlib
import tomllib

@dataclass
class Settings:
    """Project configuration settings."""

    n_gram_level: int = 2
    use_nanogpt: bool = False
    reproduction_throttle: int = 3600

    def __post_init__(self) -> None:
        # load from pyproject if available
        project = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        if project.exists():
            with project.open("rb") as f:
                data = tomllib.load(f)
            tool_cfg = data.get("tool", {}).get("arianna", {})
            n = tool_cfg.get("n_gram_level", self.n_gram_level)
            use_ngpt = tool_cfg.get("use_nanogpt", self.use_nanogpt)
            throttle = tool_cfg.get("reproduction_throttle", self.reproduction_throttle)
            self.n_gram_level = int(
                os.getenv("ARIANNA_NGRAM_LEVEL", os.getenv("ARIANNA_NGRAM_SIZE", n))
            )
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(use_ngpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}
            self.reproduction_throttle = int(os.getenv("ARIANNA_REPRODUCTION_THROTTLE", throttle))
        else:
            self.n_gram_level = int(
                os.getenv("ARIANNA_NGRAM_LEVEL", os.getenv("ARIANNA_NGRAM_SIZE", self.n_gram_level))
            )
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(self.use_nanogpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}
            self.reproduction_throttle = int(os.getenv("ARIANNA_REPRODUCTION_THROTTLE", self.reproduction_throttle))


settings = Settings()
