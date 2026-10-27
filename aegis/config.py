import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    home: Path = field(default_factory=lambda: Path(os.getenv("AEGIS_HOME", ".runtime")))
    mode: str = field(default_factory=lambda: os.getenv("AEGIS_MODE", "simulated"))
    embed_model: str = field(
        default_factory=lambda: os.getenv("AEGIS_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    primary_url: str = field(
        default_factory=lambda: os.getenv("AEGIS_PRIMARY_URL", "http://127.0.0.1:11435/v1")
    )
    secondary_url: str = field(
        default_factory=lambda: os.getenv("AEGIS_SECONDARY_URL", "http://127.0.0.1:11435/v1")
    )
    primary_model: str = field(default_factory=lambda: os.getenv("AEGIS_PRIMARY_MODEL", "qwen3:1.7b"))
    secondary_model: str = field(default_factory=lambda: os.getenv("AEGIS_SECONDARY_MODEL", "qwen3:1.7b"))
    primary_key: str = field(default_factory=lambda: os.getenv("AEGIS_PRIMARY_KEY", ""))
    secondary_key: str = field(default_factory=lambda: os.getenv("AEGIS_SECONDARY_KEY", ""))
    admin_key: str = field(default_factory=lambda: os.getenv("AEGIS_ADMIN_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("AEGIS_REDIS_URL", ""))
    timeout: float = 30.0
    deadline: float = 90.0
    retries: int = 1
    rpm: int = 20
    concurrency: int = 3
    budget: float = 1.0
    # Configured ceiling for this local single-user lab, NOT an invoicing guarantee.
    input_per_million: float = field(default_factory=lambda: float(os.getenv("AEGIS_INPUT_PER_MILLION", "0")))
    output_per_million: float = field(
        default_factory=lambda: float(os.getenv("AEGIS_OUTPUT_PER_MILLION", "0"))
    )
    max_tokens: int = 320
    cache_threshold: float = 0.94
    cache_ttl: int = 3600
    breaker_threshold: int = 2
    breaker_cooldown: float = 15.0

    def __post_init__(self):
        if self.mode not in {"simulated", "live", "proxy"}:
            raise ValueError("AEGIS_MODE must be simulated, live or proxy")
        if min(self.input_per_million, self.output_per_million) < 0:
            raise ValueError("Prices must be non-negative")
        self.home.mkdir(parents=True, exist_ok=True)
