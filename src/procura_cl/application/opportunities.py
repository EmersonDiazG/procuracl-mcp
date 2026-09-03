from procura_cl.domain.models import (
    Buyer,
    Opportunity,
    OpportunitySearch,
    SearchResult,
    Supplier,
)
from procura_cl.domain.ports import MarketGateway


class OpportunityService:
    def __init__(self, gateway: MarketGateway) -> None:
        self._gateway = gateway

    def search_tenders(self, filters: OpportunitySearch) -> SearchResult:
        items = self._gateway.search_tenders(filters)
        return SearchResult(items=items, count=len(items), source=self._gateway.source)

    def get_tender(self, code: str) -> Opportunity:
        return self._gateway.get_tender(code.strip())

    def search_agile_purchases(self, filters: OpportunitySearch) -> SearchResult:
        items = self._gateway.search_agile_purchases(filters)
        return SearchResult(items=items, count=len(items), source=self._gateway.source)

    def get_agile_purchase(self, code: str) -> Opportunity:
        return self._gateway.get_agile_purchase(code.strip())

    def find_supplier(self, rut: str) -> Supplier:
        return self._gateway.find_supplier(rut.strip())

    def list_buyers(self, limit: int = 20) -> list[Buyer]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self._gateway.list_buyers(limit)
