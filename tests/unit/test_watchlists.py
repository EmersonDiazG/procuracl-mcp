from pathlib import Path

import pytest

from procura_cl.application.watchlists import WatchlistService
from procura_cl.domain.errors import DuplicateWatchlistError, RequestBudgetExceededError
from procura_cl.domain.models import WatchlistKind
from procura_cl.infrastructure.demo_market import DemoMarketGateway
from procura_cl.infrastructure.sqlite_repository import SQLiteRepository


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteRepository:
    return SQLiteRepository(tmp_path / "procura-test.db")


@pytest.fixture
def service(repository: SQLiteRepository) -> WatchlistService:
    return WatchlistService(DemoMarketGateway(), repository, daily_request_limit=10)


def test_watchlist_sync_is_idempotent(service: WatchlistService) -> None:
    watchlist = service.create_watchlist(
        name="Automatización",
        terms=["automatización", "automatización"],
        kind=WatchlistKind.AGILE_PURCHASES,
        region="Metropolitana",
    )

    first = service.sync_watchlist(watchlist.id)
    second = service.sync_watchlist(watchlist.id)
    changes = service.list_changes(watchlist.id)

    assert watchlist.terms == ["automatización"]
    assert first.records_new == 1
    assert first.records_unchanged == 0
    assert second.records_new == 0
    assert second.records_unchanged == 1
    assert len(changes) == 1
    assert changes[0].change == "new"
    assert changes[0].opportunity.code == "DEMO-202-AG26"


def test_duplicate_name_is_rejected(service: WatchlistService) -> None:
    service.create_watchlist(name="Python", terms=["Python"])

    with pytest.raises(DuplicateWatchlistError, match="already exists"):
        service.create_watchlist(name="python", terms=["integración"])


def test_delete_watchlist_cascades_local_data(service: WatchlistService) -> None:
    watchlist = service.create_watchlist(name="Seguridad", terms=["seguridad"])
    service.sync_watchlist(watchlist.id)

    assert service.delete_watchlist(watchlist.id) is True
    assert service.delete_watchlist(watchlist.id) is False


def test_request_budget_fails_closed(repository: SQLiteRepository) -> None:
    first = repository.consume_request(daily_limit=2)
    second = repository.consume_request(daily_limit=2)

    assert first.remaining == 1
    assert second.remaining == 0
    with pytest.raises(RequestBudgetExceededError, match="has been exhausted"):
        repository.consume_request(daily_limit=2)
