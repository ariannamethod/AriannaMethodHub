from dataclasses import dataclass
import os
import pathlib
import tomllib

@dataclass
class Settings:
    """Project configuration settings."""

    n_gram_size: int = 2

    def __post_init__(self) -> None:
        # load from pyproject if available
        project = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        if project.exists():
            with project.open("rb") as f:
                data = tomllib.load(f)
            n = (
                data.get("tool", {})
                .get("arianna", {})
                .get("n_gram_size", self.n_gram_size)
            )
            self.n_gram_size = int(os.getenv("ARIANNA_NGRAM_SIZE", n))
        else:
            self.n_gram_size = int(os.getenv("ARIANNA_NGRAM_SIZE", self.n_gram_size))


settings = Settings()
