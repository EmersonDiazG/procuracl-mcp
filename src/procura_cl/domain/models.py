from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class OpportunityKind(StrEnum):
    TENDER = "tender"
    AGILE_PURCHASE = "agile_purchase"


class DataSource(StrEnum):
    DEMO = "demo"
    MERCADO_PUBLICO = "mercado_publico"


class Buyer(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    name: str


class Supplier(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    rut: str | None = None


class Opportunity(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    title: str
    kind: OpportunityKind
    status: str
    buyer: Buyer
    published_at: datetime | None = None
    closing_at: datetime | None = None
    amount_clp: int | None = Field(default=None, ge=0)
    region: str | None = None
    description: str | None = None
    source: DataSource
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OpportunitySearch(BaseModel):
    query: str | None = Field(default=None, max_length=200)
    published_on: date | None = None
    status: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    items: list[Opportunity]
    count: int = Field(ge=0)
    source: DataSource


class WatchlistKind(StrEnum):
    ALL = "all"
    TENDERS = "tenders"
    AGILE_PURCHASES = "agile_purchases"


class ChangeKind(StrEnum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class SyncStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Watchlist(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1, max_length=120)
    terms: list[str] = Field(min_length=1, max_length=10)
    kind: WatchlistKind = WatchlistKind.ALL
    region: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=80)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WatchlistChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    watchlist_id: str
    change: ChangeKind
    opportunity: Opportunity
    changed_at: datetime


class SyncResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sync_id: str
    watchlist_id: str
    status: SyncStatus
    records_received: int = Field(ge=0)
    records_new: int = Field(ge=0)
    records_updated: int = Field(ge=0)
    records_unchanged: int = Field(ge=0)
    started_at: datetime
    finished_at: datetime
    error: str | None = None


class RequestBudgetStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    used: int = Field(ge=0)
    limit: int = Field(gt=0)
    remaining: int = Field(ge=0)


class DataSourceStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str
    source: DataSource
    ticket_configured: bool
    api_v1_url: str
    api_v2_url: str
    api_timeout_seconds: float = Field(gt=0)
    cache_ttl_seconds: int = Field(gt=0)
    attribution: str
    request_budget: RequestBudgetStatus
