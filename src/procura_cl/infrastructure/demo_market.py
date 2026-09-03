from __future__ import annotations

from datetime import UTC, datetime

from procura_cl.domain.errors import OpportunityNotFoundError
from procura_cl.domain.models import (
    Buyer,
    DataSource,
    Opportunity,
    OpportunityKind,
    OpportunitySearch,
    Supplier,
)

_BUYERS = [
    Buyer(code="6945", name="Dirección de Compras y Contratación Pública"),
    Buyer(code="1057418", name="Servicio Nacional de Capacitación y Empleo"),
    Buyer(code="7210", name="Municipalidad de Santiago"),
]

_OPPORTUNITIES = [
    Opportunity(
        code="DEMO-101-LE26",
        title="Desarrollo e integración de plataforma de datos",
        kind=OpportunityKind.TENDER,
        status="published",
        buyer=_BUYERS[0],
        published_at=datetime(2026, 8, 4, 12, tzinfo=UTC),
        closing_at=datetime(2026, 8, 18, 18, tzinfo=UTC),
        amount_clp=48_000_000,
        region="Región Metropolitana",
        description="Servicios Python, integración API y automatización de procesos.",
        source=DataSource.DEMO,
    ),
    Opportunity(
        code="DEMO-202-AG26",
        title="Automatización de reportes institucionales",
        kind=OpportunityKind.AGILE_PURCHASE,
        status="open",
        buyer=_BUYERS[1],
        published_at=datetime(2026, 8, 8, 13, tzinfo=UTC),
        closing_at=datetime(2026, 8, 13, 17, tzinfo=UTC),
        amount_clp=7_500_000,
        region="Región Metropolitana",
        description="Construcción de integración y reportes automatizados.",
        source=DataSource.DEMO,
    ),
    Opportunity(
        code="DEMO-303-AG26",
        title="Evaluación de seguridad de aplicación web",
        kind=OpportunityKind.AGILE_PURCHASE,
        status="open",
        buyer=_BUYERS[2],
        published_at=datetime(2026, 8, 9, 14, tzinfo=UTC),
        closing_at=datetime(2026, 8, 14, 16, tzinfo=UTC),
        amount_clp=5_200_000,
        region="Región Metropolitana",
        description="Revisión de ciberseguridad y plan de mitigación.",
        source=DataSource.DEMO,
    ),
]


class DemoMarketGateway:
    """Deterministic portfolio/demo adapter that never calls an external API."""

    source = DataSource.DEMO

    def _search(self, kind: OpportunityKind, filters: OpportunitySearch) -> list[Opportunity]:
        items = [item for item in _OPPORTUNITIES if item.kind == kind]
        if filters.query:
            query = filters.query.casefold()
            items = [
                item
                for item in items
                if query in item.title.casefold() or query in (item.description or "").casefold()
            ]
        if filters.status:
            items = [item for item in items if item.status.casefold() == filters.status.casefold()]
        if filters.region:
            items = [
                item
                for item in items
                if item.region and filters.region.casefold() in item.region.casefold()
            ]
        if filters.published_on:
            items = [
                item
                for item in items
                if item.published_at and item.published_at.date() == filters.published_on
            ]
        return items[: filters.limit]

    def search_tenders(self, filters: OpportunitySearch) -> list[Opportunity]:
        return self._search(OpportunityKind.TENDER, filters)

    def get_tender(self, code: str) -> Opportunity:
        return self._get(code, OpportunityKind.TENDER)

    def search_agile_purchases(self, filters: OpportunitySearch) -> list[Opportunity]:
        return self._search(OpportunityKind.AGILE_PURCHASE, filters)

    def get_agile_purchase(self, code: str) -> Opportunity:
        return self._get(code, OpportunityKind.AGILE_PURCHASE)

    def _get(self, code: str, kind: OpportunityKind) -> Opportunity:
        for item in _OPPORTUNITIES:
            if item.code.casefold() == code.casefold() and item.kind == kind:
                return item
        raise OpportunityNotFoundError(f"Opportunity {code!r} was not found")

    def find_supplier(self, rut: str) -> Supplier:
        return Supplier(code="DEMO-SUPPLIER-1", name="Tecnología Demo SpA", rut=rut)

    def list_buyers(self, limit: int) -> list[Buyer]:
        return _BUYERS[:limit]
