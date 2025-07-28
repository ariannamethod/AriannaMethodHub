from dataclasses import dataclass
import os
import pathlib
import tomllib

@dataclass
class Settings:
    """Project configuration settings."""

    n_gram_level: int = 2
    n_gram_size: int = 2  # backward compatibility
    use_nanogpt: bool = False

    def __post_init__(self) -> None:
        # load from pyproject if available
        project = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        if project.exists():
            with project.open("rb") as f:
                data = tomllib.load(f)
            tool_cfg = data.get("tool", {}).get("arianna", {})
            n = tool_cfg.get("n_gram_size", self.n_gram_size)
            level = tool_cfg.get("n_gram_level", self.n_gram_level)
            use_ngpt = tool_cfg.get("use_nanogpt", self.use_nanogpt)
            self.n_gram_level = int(os.getenv("ARIANNA_NGRAM_LEVEL", level))
            self.n_gram_size = int(os.getenv("ARIANNA_NGRAM_SIZE", n))
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(use_ngpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}
        else:
            self.n_gram_level = int(os.getenv("ARIANNA_NGRAM_LEVEL", self.n_gram_level))
            self.n_gram_size = int(os.getenv("ARIANNA_NGRAM_SIZE", self.n_gram_size))
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(self.use_nanogpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}

        # keep old parameter in sync
        if not self.n_gram_size:
            self.n_gram_size = self.n_gram_level


settings = Settings()
