from procura_cl.domain.models import (
    Buyer,
    DataSource,
    Opportunity,
    OpportunitySearch,
    Supplier,
)
from procura_cl.domain.ports import MarketGateway, WatchlistRepository


class BudgetedMarketGateway:
    """Counts every upstream SDK operation before it is attempted."""

    def __init__(
        self,
        gateway: MarketGateway,
        repository: WatchlistRepository,
        *,
        daily_limit: int,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._daily_limit = daily_limit
        self.source = DataSource.MERCADO_PUBLICO

    def _consume(self) -> None:
        self._repository.consume_request(daily_limit=self._daily_limit)

    def search_tenders(self, filters: OpportunitySearch) -> list[Opportunity]:
        self._consume()
        return self._gateway.search_tenders(filters)

    def get_tender(self, code: str) -> Opportunity:
        self._consume()
        return self._gateway.get_tender(code)

    def search_agile_purchases(self, filters: OpportunitySearch) -> list[Opportunity]:
        self._consume()
        return self._gateway.search_agile_purchases(filters)

    def get_agile_purchase(self, code: str) -> Opportunity:
        self._consume()
        return self._gateway.get_agile_purchase(code)

    def find_supplier(self, rut: str) -> Supplier:
        self._consume()
        return self._gateway.find_supplier(rut)

    def list_buyers(self, limit: int) -> list[Buyer]:
        self._consume()
        return self._gateway.list_buyers(limit)
