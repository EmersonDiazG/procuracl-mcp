from __future__ import annotations

import unicodedata
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from chile_public_market_sdk import (
    ChilePublicMarketError,
    NotFoundError,
    SyncChilePublicMarketClient,
)
from chile_public_market_sdk.models.tenders import Tender

from procura_cl.domain.errors import OpportunityNotFoundError, UpstreamServiceError
from procura_cl.domain.models import (
    Buyer,
    DataSource,
    Opportunity,
    OpportunityKind,
    OpportunitySearch,
    Supplier,
)
from procura_cl.infrastructure.agile_api import AgileApiClient, AgilePurchaseRecord

_REGIONS = {
    "tarapaca": 1,
    "antofagasta": 2,
    "atacama": 3,
    "coquimbo": 4,
    "valparaiso": 5,
    "ohiggins": 6,
    "maule": 7,
    "biobio": 8,
    "araucania": 9,
    "los lagos": 10,
    "aysen": 11,
    "magallanes": 12,
    "metropolitana": 13,
    "los rios": 14,
    "arica y parinacota": 15,
    "nuble": 16,
}

_TENDER_STATUSES = {
    "open": "activas",
    "active": "activas",
    "abierta": "activas",
    "abiertas": "activas",
    "activa": "activas",
    "activas": "activas",
    "published": "publicada",
    "publicada": "publicada",
    "closed": "cerrada",
    "cerrada": "cerrada",
    "deserted": "desierta",
    "desierta": "desierta",
    "awarded": "adjudicada",
    "adjudicada": "adjudicada",
    "revoked": "revocada",
    "revocada": "revocada",
    "suspended": "suspendida",
    "suspendida": "suspendida",
    "all": "todos",
    "todos": "todos",
}

_AGILE_STATUSES = {
    "open": "publicada",
    "active": "publicada",
    "abierta": "publicada",
    "publicada": "publicada",
    "published": "publicada",
    "closed": "cerrada",
    "cerrada": "cerrada",
    "deserted": "desierta",
    "desierta": "desierta",
    "cancelled": "cancelada",
    "canceled": "cancelada",
    "cancelada": "cancelada",
    "supplier_selected": "proveedor_seleccionado",
    "proveedor_seleccionado": "proveedor_seleccionado",
    "purchase_order_issued": "oc_emitida",
    "oc_emitida": "oc_emitida",
}


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _amount(value: Decimal | None) -> int | None:
    return int(value) if value is not None else None


class LiveMarketGateway:
    """Adapter for the unofficial typed SDK backed by official ChileCompra APIs."""

    source = DataSource.MERCADO_PUBLICO

    def __init__(
        self,
        ticket: str,
        *,
        client: SyncChilePublicMarketClient | None = None,
        agile_client: AgileApiClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = client or SyncChilePublicMarketClient(ticket=ticket, timeout=timeout)
        self._agile_client = agile_client or AgileApiClient(ticket, timeout=timeout)

    def search_tenders(self, filters: OpportunitySearch) -> list[Opportunity]:
        try:
            response = self._client.get_tenders(
                date=filters.published_on,
                status=self._tender_status(filters.status),
            )
        except ChilePublicMarketError as error:
            raise UpstreamServiceError("Mercado Público tender search failed") from error
        items = [self._tender(item) for item in response.items]
        if filters.query:
            needle = filters.query.casefold()
            items = [
                item
                for item in items
                if needle in item.title.casefold() or needle in (item.description or "").casefold()
            ]
        return items[: filters.limit]

    def get_tender(self, code: str) -> Opportunity:
        try:
            response = self._client.get_tenders(code=code)
        except NotFoundError as error:
            raise OpportunityNotFoundError(f"Tender {code!r} was not found") from error
        except ChilePublicMarketError as error:
            raise UpstreamServiceError("Mercado Público tender lookup failed") from error
        if not response.items:
            raise OpportunityNotFoundError(f"Tender {code!r} was not found")
        return self._tender(response.items[0])

    def search_agile_purchases(self, filters: OpportunitySearch) -> list[Opportunity]:
        published_from: datetime | None = None
        published_until: datetime | None = None
        if filters.published_on:
            published_from = datetime.combine(filters.published_on, time.min, tzinfo=UTC)
            published_until = published_from + timedelta(days=1)
        regions = self._region_codes(filters.region)
        try:
            items = self._agile_client.search(
                query=filters.query,
                published_from=published_from,
                published_until=published_until,
                statuses=self._agile_statuses(filters.status),
                regions=regions,
                page_size=max(10, filters.limit),
            )
        except (OpportunityNotFoundError, UpstreamServiceError):
            raise
        return [self._agile(item) for item in items[: filters.limit]]

    def get_agile_purchase(self, code: str) -> Opportunity:
        return self._agile(self._agile_client.get(code))

    def find_supplier(self, rut: str) -> Supplier:
        try:
            response = self._client.find_supplier(rut)
        except ChilePublicMarketError as error:
            raise UpstreamServiceError("Supplier lookup failed") from error
        if not response.companies:
            raise OpportunityNotFoundError(f"Supplier {rut!r} was not found")
        company = response.companies[0]
        return Supplier(
            code=str(company.company_code or "unknown"),
            name=company.company_name or "Unknown supplier",
            rut=company.tax_id or rut,
        )

    def list_buyers(self, limit: int) -> list[Buyer]:
        try:
            response = self._client.get_buyers()
        except ChilePublicMarketError as error:
            raise UpstreamServiceError("Buyer listing failed") from error
        return [
            Buyer(
                code=str(company.company_code or "unknown"),
                name=company.company_name or "Unknown buyer",
            )
            for company in response.companies[:limit]
        ]

    @staticmethod
    def _tender(item: Tender) -> Opportunity:
        buyer = item.buyer
        dates = item.dates
        return Opportunity(
            code=item.external_code,
            title=item.name or "Untitled tender",
            kind=OpportunityKind.TENDER,
            status=item.status or str(item.status_code or "unknown"),
            buyer=Buyer(
                code=str(buyer.organization_code or "unknown") if buyer else "unknown",
                name=buyer.organization_name or "Unknown buyer" if buyer else "Unknown buyer",
            ),
            published_at=dates.published_at if dates else None,
            closing_at=item.closing_at if isinstance(item.closing_at, datetime) else None,
            amount_clp=_amount(item.estimated_amount),
            region=str(buyer.region) if buyer and buyer.region is not None else None,
            description=item.description,
            source=DataSource.MERCADO_PUBLICO,
        )

    @staticmethod
    def _agile(item: AgilePurchaseRecord) -> Opportunity:
        return Opportunity(
            code=item.code,
            title=item.name,
            kind=OpportunityKind.AGILE_PURCHASE,
            status=item.status.label,
            buyer=Buyer(
                code=item.institution.tax_id,
                name=item.institution.buyer_organization,
            ),
            published_at=item.dates.published_at,
            closing_at=item.dates.closing_at,
            amount_clp=_amount(item.available_amount_clp),
            region=item.institution.region_name,
            description=item.description,
            source=DataSource.MERCADO_PUBLICO,
        )

    @staticmethod
    def _region_codes(region: str | None) -> list[int] | None:
        if region is None:
            return None
        name = _plain(region).removeprefix("region de ").removeprefix("region del ")
        code = next((value for key, value in _REGIONS.items() if key in name), None)
        if code is None:
            supported = ", ".join(sorted(_REGIONS))
            raise ValueError(f"Unknown Chilean region {region!r}. Supported names: {supported}")
        return [code]

    @staticmethod
    def _tender_status(status: str | None) -> str | None:
        if status is None:
            return None
        normalized = _plain(status).strip().replace(" ", "_")
        value = _TENDER_STATUSES.get(normalized)
        if value is None:
            supported = ", ".join(sorted(_TENDER_STATUSES))
            raise ValueError(f"Unknown tender status {status!r}. Supported values: {supported}")
        return value

    @staticmethod
    def _agile_statuses(status: str | None) -> list[str] | None:
        if status is None:
            return None
        normalized = _plain(status).strip().replace(" ", "_")
        value = _AGILE_STATUSES.get(normalized)
        if value is None:
            supported = ", ".join(sorted(_AGILE_STATUSES))
            raise ValueError(
                f"Unknown Compra Ágil status {status!r}. Supported values: {supported}"
            )
        return [value]
