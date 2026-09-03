from __future__ import annotations

from datetime import datetime
from typing import Protocol

from procura_cl.domain.models import (
    Buyer,
    ChangeKind,
    DataSource,
    Opportunity,
    OpportunitySearch,
    RequestBudgetStatus,
    Supplier,
    SyncResult,
    Watchlist,
    WatchlistChange,
)


class MarketGateway(Protocol):
    """Data-source boundary used by application services."""

    source: DataSource

    def search_tenders(self, filters: OpportunitySearch) -> list[Opportunity]: ...

    def get_tender(self, code: str) -> Opportunity: ...

    def search_agile_purchases(self, filters: OpportunitySearch) -> list[Opportunity]: ...

    def get_agile_purchase(self, code: str) -> Opportunity: ...

    def find_supplier(self, rut: str) -> Supplier: ...

    def list_buyers(self, limit: int) -> list[Buyer]: ...


class WatchlistRepository(Protocol):
    def create_watchlist(self, watchlist: Watchlist) -> Watchlist: ...

    def list_watchlists(self) -> list[Watchlist]: ...

    def get_watchlist(self, watchlist_id: str) -> Watchlist: ...

    def delete_watchlist(self, watchlist_id: str) -> bool: ...

    def save_snapshot(self, watchlist_id: str, opportunity: Opportunity) -> ChangeKind: ...

    def list_changes(
        self, watchlist_id: str, *, since: datetime | None, limit: int
    ) -> list[WatchlistChange]: ...

    def save_sync_result(self, result: SyncResult) -> None: ...

    def consume_request(self, *, daily_limit: int) -> RequestBudgetStatus: ...

    def get_request_budget(self, *, daily_limit: int) -> RequestBudgetStatus: ...

    def get_cache(self, key: str) -> str | None: ...

    def set_cache(self, key: str, payload: str, *, ttl_seconds: int) -> None: ...
