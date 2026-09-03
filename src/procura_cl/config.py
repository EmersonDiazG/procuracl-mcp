from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from procura_cl.domain.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    data_mode: str
    database_path: Path
    daily_request_limit: int
    cache_ttl_seconds: int
    api_timeout_seconds: float
    market_ticket: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(override=False)
        mode = os.getenv("PROCURA_DATA_MODE", "demo").strip().lower()
        if mode not in {"demo", "live"}:
            raise ConfigurationError("PROCURA_DATA_MODE must be 'demo' or 'live'")
        raw_limit = os.getenv("PROCURA_DAILY_REQUEST_LIMIT", "9500")
        try:
            daily_limit = int(raw_limit)
        except ValueError as error:
            raise ConfigurationError("PROCURA_DAILY_REQUEST_LIMIT must be an integer") from error
        if not 1 <= daily_limit <= 10_000:
            raise ConfigurationError("PROCURA_DAILY_REQUEST_LIMIT must be between 1 and 10000")
        raw_cache_ttl = os.getenv("PROCURA_CACHE_TTL_SECONDS", "300")
        try:
            cache_ttl = int(raw_cache_ttl)
        except ValueError as error:
            raise ConfigurationError("PROCURA_CACHE_TTL_SECONDS must be an integer") from error
        if not 1 <= cache_ttl <= 86_400:
            raise ConfigurationError("PROCURA_CACHE_TTL_SECONDS must be between 1 and 86400")
        raw_timeout = os.getenv("PROCURA_API_TIMEOUT_SECONDS", "30")
        try:
            api_timeout = float(raw_timeout)
        except ValueError as error:
            raise ConfigurationError("PROCURA_API_TIMEOUT_SECONDS must be numeric") from error
        if not 1 <= api_timeout <= 120:
            raise ConfigurationError("PROCURA_API_TIMEOUT_SECONDS must be between 1 and 120")
        market_ticket = os.getenv("CHILE_PUBLIC_MARKET_TICKET")
        if market_ticket is not None:
            market_ticket = market_ticket.strip() or None
        return cls(
            data_mode=mode,
            database_path=Path(os.getenv("PROCURA_DATABASE_PATH", "data/procura.db")),
            daily_request_limit=daily_limit,
            cache_ttl_seconds=cache_ttl,
            api_timeout_seconds=api_timeout,
            market_ticket=market_ticket,
        )
