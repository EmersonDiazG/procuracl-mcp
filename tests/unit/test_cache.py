from pathlib import Path

from procura_cl.domain.models import OpportunitySearch
from procura_cl.infrastructure.budgeted_market import BudgetedMarketGateway
from procura_cl.infrastructure.cached_market import CachedMarketGateway
from procura_cl.infrastructure.demo_market import DemoMarketGateway
from procura_cl.infrastructure.sqlite_repository import SQLiteRepository


def test_cache_hit_does_not_consume_a_second_request(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "cache-test.db")
    budgeted = BudgetedMarketGateway(
        DemoMarketGateway(),
        repository,
        daily_limit=10,
    )
    cached = CachedMarketGateway(budgeted, repository, ttl_seconds=300)
    filters = OpportunitySearch(query="automatización")

    first = cached.search_agile_purchases(filters)
    second = cached.search_agile_purchases(filters)
    budget = repository.get_request_budget(daily_limit=10)

    assert first == second
    assert budget.used == 1
    assert budget.remaining == 9
