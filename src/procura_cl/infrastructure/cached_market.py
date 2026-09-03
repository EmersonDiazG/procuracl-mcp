from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from procura_cl.domain.models import (
    Buyer,
    DataSource,
    Opportunity,
    OpportunitySearch,
    Supplier,
)
from procura_cl.domain.ports import MarketGateway, WatchlistRepository

ModelT = TypeVar("ModelT", bound=BaseModel)
OPPORTUNITY_LIST_ADAPTER: TypeAdapter[list[Opportunity]] = TypeAdapter(list[Opportunity])
BUYER_LIST_ADAPTER: TypeAdapter[list[Buyer]] = TypeAdapter(list[Buyer])


class CachedMarketGateway:
    """Read-through SQLite cache placed outside the request-budget wrapper."""

    def __init__(
        self,
        gateway: MarketGateway,
        repository: WatchlistRepository,
        *,
        ttl_seconds: int,
    ) -> None:
        self._gateway = gateway
        self._repository = repository
        self._ttl_seconds = ttl_seconds
        self.source = DataSource.MERCADO_PUBLICO

    @staticmethod
    def _key(operation: str, arguments: object) -> str:
        canonical = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(f"{operation}:{canonical}".encode()).hexdigest()

    def _one(
        self,
        key: str,
        model: type[ModelT],
        loader: Callable[[], ModelT],
    ) -> ModelT:
        cached = self._repository.get_cache(key)
        if cached is not None:
            return model.model_validate_json(cached)
        result = loader()
        self._repository.set_cache(key, result.model_dump_json(), ttl_seconds=self._ttl_seconds)
        return result

    def _many(
        self,
        key: str,
        adapter: TypeAdapter[list[ModelT]],
        loader: Callable[[], list[ModelT]],
    ) -> list[ModelT]:
        cached = self._repository.get_cache(key)
        if cached is not None:
            return adapter.validate_json(cached)
        result = loader()
        payload = adapter.dump_json(result).decode()
        self._repository.set_cache(key, payload, ttl_seconds=self._ttl_seconds)
        return result

    def search_tenders(self, filters: OpportunitySearch) -> list[Opportunity]:
        key = self._key("search_tenders", filters.model_dump(mode="json"))
        return self._many(
            key,
            OPPORTUNITY_LIST_ADAPTER,
            lambda: self._gateway.search_tenders(filters),
        )

    def get_tender(self, code: str) -> Opportunity:
        key = self._key("get_tender", code)
        return self._one(key, Opportunity, lambda: self._gateway.get_tender(code))

    def search_agile_purchases(self, filters: OpportunitySearch) -> list[Opportunity]:
        key = self._key("search_agile_purchases", filters.model_dump(mode="json"))
        return self._many(
            key,
            OPPORTUNITY_LIST_ADAPTER,
            lambda: self._gateway.search_agile_purchases(filters),
        )

    def get_agile_purchase(self, code: str) -> Opportunity:
        key = self._key("get_agile_purchase", code)
        return self._one(key, Opportunity, lambda: self._gateway.get_agile_purchase(code))

    def find_supplier(self, rut: str) -> Supplier:
        key = self._key("find_supplier", rut)
        return self._one(key, Supplier, lambda: self._gateway.find_supplier(rut))

    def list_buyers(self, limit: int) -> list[Buyer]:
        key = self._key("list_buyers", limit)
        return self._many(key, BUYER_LIST_ADAPTER, lambda: self._gateway.list_buyers(limit))
