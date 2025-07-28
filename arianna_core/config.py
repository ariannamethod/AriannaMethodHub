from dataclasses import dataclass
import os
import pathlib
import tomllib

@dataclass
class Settings:
    """Project configuration settings."""

    n_gram_level: int = 2
    use_nanogpt: bool = False
    reproduction_interval: int = 3600  # seconds

    def __post_init__(self) -> None:
        # load from pyproject if available
        project = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        if project.exists():
            with project.open("rb") as f:
                data = tomllib.load(f)
            n = (
                data.get("tool", {})
                .get("arianna", {})
                .get("n_gram_level", self.n_gram_level)
            )
            use_ngpt = (
                data.get("tool", {})
                .get("arianna", {})
                .get("use_nanogpt", self.use_nanogpt)
            )
            self.n_gram_level = int(
                os.getenv("ARIANNA_NGRAM_LEVEL", os.getenv("ARIANNA_NGRAM_SIZE", n))
            )
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(use_ngpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}
            interval = (
                data.get("tool", {})
                .get("arianna", {})
                .get("reproduction_interval", self.reproduction_interval)
            )
            self.reproduction_interval = int(
                os.getenv("ARIANNA_REPRO_INTERVAL", str(interval))
            )
        else:
            self.n_gram_level = int(
                os.getenv("ARIANNA_NGRAM_LEVEL", os.getenv("ARIANNA_NGRAM_SIZE", self.n_gram_level))
            )
            flag = os.getenv("ARIANNA_USE_NANOGPT", str(self.use_nanogpt))
            self.use_nanogpt = flag.lower() in {"1", "true", "yes"}
            self.reproduction_interval = int(
                os.getenv("ARIANNA_REPRO_INTERVAL", str(self.reproduction_interval))
            )


settings = Settings()
