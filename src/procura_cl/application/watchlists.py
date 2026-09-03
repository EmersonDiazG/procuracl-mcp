from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from procura_cl.domain.models import (
    ChangeKind,
    Opportunity,
    OpportunitySearch,
    RequestBudgetStatus,
    SyncResult,
    SyncStatus,
    Watchlist,
    WatchlistChange,
    WatchlistKind,
)
from procura_cl.domain.ports import MarketGateway, WatchlistRepository


class WatchlistService:
    def __init__(
        self,
        gateway: MarketGateway,
        repository: WatchlistRepository,
        *,
        daily_request_limit: int,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._daily_request_limit = daily_request_limit

    def create_watchlist(
        self,
        *,
        name: str,
        terms: list[str],
        kind: WatchlistKind = WatchlistKind.ALL,
        region: str | None = None,
        status: str | None = None,
    ) -> Watchlist:
        normalized_terms = list(dict.fromkeys(term.strip() for term in terms if term.strip()))
        watchlist = Watchlist(
            name=name.strip(),
            terms=normalized_terms,
            kind=kind,
            region=region.strip() if region else None,
            status=status.strip() if status else None,
        )
        return self._repository.create_watchlist(watchlist)

    def list_watchlists(self) -> list[Watchlist]:
        return self._repository.list_watchlists()

    def delete_watchlist(self, watchlist_id: str) -> bool:
        return self._repository.delete_watchlist(watchlist_id.strip())

    def sync_watchlist(self, watchlist_id: str) -> SyncResult:
        watchlist = self._repository.get_watchlist(watchlist_id.strip())
        sync_id = uuid4().hex
        started_at = datetime.now(UTC)
        try:
            opportunities = self._search(watchlist)
            counts = {change: 0 for change in ChangeKind}
            for opportunity in opportunities:
                change = self._repository.save_snapshot(watchlist.id, opportunity)
                counts[change] += 1
            result = SyncResult(
                sync_id=sync_id,
                watchlist_id=watchlist.id,
                status=SyncStatus.SUCCEEDED,
                records_received=len(opportunities),
                records_new=counts[ChangeKind.NEW],
                records_updated=counts[ChangeKind.UPDATED],
                records_unchanged=counts[ChangeKind.UNCHANGED],
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        except Exception as error:
            result = SyncResult(
                sync_id=sync_id,
                watchlist_id=watchlist.id,
                status=SyncStatus.FAILED,
                records_received=0,
                records_new=0,
                records_updated=0,
                records_unchanged=0,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                error=type(error).__name__,
            )
            self._repository.save_sync_result(result)
            raise
        self._repository.save_sync_result(result)
        return result

    def _search(self, watchlist: Watchlist) -> list[Opportunity]:
        opportunities: dict[str, Opportunity] = {}
        for term in watchlist.terms:
            filters = OpportunitySearch(
                query=term,
                region=watchlist.region,
                status=watchlist.status,
                limit=50,
            )
            if watchlist.kind in (WatchlistKind.ALL, WatchlistKind.TENDERS):
                for opportunity in self._gateway.search_tenders(filters):
                    opportunities[opportunity.code] = opportunity
            if watchlist.kind in (WatchlistKind.ALL, WatchlistKind.AGILE_PURCHASES):
                for opportunity in self._gateway.search_agile_purchases(filters):
                    opportunities[opportunity.code] = opportunity
        return list(opportunities.values())

    def list_changes(
        self,
        watchlist_id: str,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[WatchlistChange]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        return self._repository.list_changes(watchlist_id.strip(), since=since, limit=limit)

    def request_budget(self) -> RequestBudgetStatus:
        return self._repository.get_request_budget(daily_limit=self._daily_request_limit)
