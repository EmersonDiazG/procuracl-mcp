from __future__ import annotations

import json
from datetime import date, datetime

from mcp.server import MCPServer

from procura_cl.application.opportunities import OpportunityService
from procura_cl.application.watchlists import WatchlistService
from procura_cl.config import Settings
from procura_cl.domain.models import (
    Buyer,
    DataSourceStatus,
    Opportunity,
    OpportunitySearch,
    RequestBudgetStatus,
    SearchResult,
    Supplier,
    SyncResult,
    Watchlist,
    WatchlistChange,
    WatchlistKind,
)
from procura_cl.infrastructure.factory import build_gateway
from procura_cl.infrastructure.sqlite_repository import SQLiteRepository

mcp = MCPServer("ProcuraCL")
settings = Settings.from_env()
repository = SQLiteRepository(settings.database_path)
gateway = build_gateway(settings, repository)
service = OpportunityService(gateway)
watchlists = WatchlistService(
    gateway,
    repository,
    daily_request_limit=settings.daily_request_limit,
)


@mcp.tool()
def search_tenders(
    query: str | None = None,
    published_on: date | None = None,
    status: str | None = None,
    limit: int = 10,
) -> SearchResult:
    """Search typed Mercado Público tender opportunities."""
    filters = OpportunitySearch(query=query, published_on=published_on, status=status, limit=limit)
    return service.search_tenders(filters)


@mcp.tool()
def get_tender(code: str) -> Opportunity:
    """Get one tender by its Mercado Público code."""
    return service.get_tender(code)


@mcp.tool()
def search_agile_purchases(
    query: str | None = None,
    published_on: date | None = None,
    status: str | None = None,
    region: str | None = None,
    limit: int = 10,
) -> SearchResult:
    """Search typed Compra Ágil opportunities."""
    filters = OpportunitySearch(
        query=query,
        published_on=published_on,
        status=status,
        region=region,
        limit=limit,
    )
    return service.search_agile_purchases(filters)


@mcp.tool()
def get_agile_purchase(code: str) -> Opportunity:
    """Get one Compra Ágil opportunity by code."""
    return service.get_agile_purchase(code)


@mcp.tool()
def find_supplier(rut: str) -> Supplier:
    """Find a supplier using a Chilean RUT."""
    return service.find_supplier(rut)


@mcp.tool()
def list_buyers(limit: int = 20) -> list[Buyer]:
    """List buyer organizations, capped at 100 records."""
    return service.list_buyers(limit)


@mcp.tool()
def create_watchlist(
    name: str,
    terms: list[str],
    kind: WatchlistKind = WatchlistKind.ALL,
    region: str | None = None,
    status: str | None = None,
) -> Watchlist:
    """Create a persistent opportunity watchlist."""
    return watchlists.create_watchlist(
        name=name,
        terms=terms,
        kind=kind,
        region=region,
        status=status,
    )


@mcp.tool()
def list_watchlists() -> list[Watchlist]:
    """List every persistent watchlist."""
    return watchlists.list_watchlists()


@mcp.tool()
def sync_watchlist(watchlist_id: str) -> SyncResult:
    """Synchronize one watchlist and record new or updated opportunities."""
    return watchlists.sync_watchlist(watchlist_id)


@mcp.tool()
def list_watchlist_changes(
    watchlist_id: str,
    since: datetime | None = None,
    limit: int = 50,
) -> list[WatchlistChange]:
    """List the latest new or updated opportunities for a watchlist."""
    return watchlists.list_changes(watchlist_id, since=since, limit=limit)


@mcp.tool()
def delete_watchlist(watchlist_id: str) -> bool:
    """Delete a watchlist and its local snapshots."""
    return watchlists.delete_watchlist(watchlist_id)


@mcp.tool()
def get_request_budget() -> RequestBudgetStatus:
    """Show today's configured Mercado Público request budget."""
    return watchlists.request_budget()


@mcp.tool()
def get_data_source_status() -> DataSourceStatus:
    """Show the active data source and production-readiness settings without exposing secrets."""
    return DataSourceStatus(
        mode=settings.data_mode,
        source=gateway.source,
        ticket_configured=settings.market_ticket is not None,
        api_v1_url="https://api.mercadopublico.cl/servicios/v1/publico",
        api_v2_url="https://api2.mercadopublico.cl/v2",
        api_timeout_seconds=settings.api_timeout_seconds,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        attribution="Dirección ChileCompra",
        request_budget=watchlists.request_budget(),
    )


@mcp.resource("procura://about")
def about() -> str:
    """Product scope, provenance and safety boundaries."""
    return (
        "ProcuraCL exposes structured Chilean public-procurement data to MCP clients. "
        "Demo records are synthetic and explicitly marked source=demo. Live records will "
        "identify Dirección ChileCompra as their source. API tickets are read only from the "
        "server environment and are never returned to clients."
    )


@mcp.resource("procura://watchlists")
def watchlist_resource() -> str:
    """Current watchlists as structured JSON."""
    return json.dumps(
        [item.model_dump(mode="json") for item in watchlists.list_watchlists()],
        ensure_ascii=False,
    )


@mcp.prompt()
def opportunity_brief(code: str) -> str:
    """Create an evidence-oriented brief for one opportunity."""
    return (
        f"Retrieve opportunity {code} with the appropriate ProcuraCL tool. Summarize its "
        "scope, buyer, status, dates, amount, risks, missing information, and source code. "
        "Do not infer requirements that are absent from the structured result."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
