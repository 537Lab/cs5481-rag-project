"""Load config.toml (non-secret) and .env (secret) into one Settings object.

WHY: keeping parameters in a toml file means a beginner can change chunk size
without touching Python, and keeping secrets in .env means they can never be
committed by accident. `os.environ.setdefault` gives real shell variables
priority, which is what CI expects.

No third-party dependency: Python 3.11+ ships `tomllib`, and our tiny .env
reader handles the simple KEY=VALUE format we use.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.toml"


@dataclass(frozen=True)
class Settings:
    root: Path
    raw_dir: Path
    manifest: Path
    index_dir: Path
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    embedding_provider: str
    local_model: str
    local_dimension: int
    api_model: str
    api_dimension: int
    llm_model: str
    temperature: float
    max_tokens: int
    top_k: int
    min_score: float

    @property
    def collection_name(self) -> str:
        """Separate collections per strategy so experiments never mix index data."""
        return f"chunks_{self.chunk_strategy}"

    @property
    def embedding_dimension(self) -> int:
        return (
            self.local_dimension if self.embedding_provider == "local" else self.api_dimension
        )


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines, '#' comments, no shell expansion."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def load_settings(path: str | Path | None = None) -> Settings:
    _load_dotenv(ROOT / ".env")

    config_path = Path(path or os.environ.get("RAGKIT_CONFIG", DEFAULT_CONFIG))
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not config_path.is_file():
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("rb") as fh:
        cfg = tomllib.load(fh)

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    paths, chunking = cfg["paths"], cfg["chunking"]
    embedding, llm, retrieval = cfg["embedding"], cfg["llm"], cfg["retrieval"]

    if embedding["provider"] not in {"local", "api"}:
        raise ValueError("embedding.provider must be 'local' or 'api'")
    if chunking["strategy"] not in {"fixed", "paragraph"}:
        raise ValueError("chunking.strategy must be 'fixed' or 'paragraph'")
    if chunking["overlap"] >= chunking["size"]:
        raise ValueError("chunking.overlap must be smaller than chunking.size")

    return Settings(
        root=ROOT,
        raw_dir=resolve(paths["raw_dir"]),
        manifest=resolve(paths["manifest"]),
        index_dir=resolve(paths["index_dir"]),
        chunk_strategy=chunking["strategy"],
        chunk_size=int(chunking["size"]),
        chunk_overlap=int(chunking["overlap"]),
        embedding_provider=embedding["provider"],
        local_model=embedding["local_model"],
        local_dimension=int(embedding["local_dimension"]),
        api_model=embedding["api_model"],
        api_dimension=int(embedding["api_dimension"]),
        llm_model=os.environ.get("LLM_MODEL", llm["model"]),
        temperature=float(llm["temperature"]),
        max_tokens=int(llm["max_tokens"]),
        top_k=int(retrieval["top_k"]),
        min_score=float(retrieval["min_score"]),
    )


def require_api_key() -> str:
    """Return the key or fail with an actionable message. Never logs the key."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or export OPENAI_API_KEY in your shell. "
            "For a key-free walkthrough use: python -m ragkit.cli offline-demo"
        )
    return key
