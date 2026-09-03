from procura_cl.config import Settings
from procura_cl.domain.errors import ConfigurationError
from procura_cl.domain.ports import MarketGateway
from procura_cl.infrastructure.budgeted_market import BudgetedMarketGateway
from procura_cl.infrastructure.cached_market import CachedMarketGateway
from procura_cl.infrastructure.demo_market import DemoMarketGateway
from procura_cl.infrastructure.live_market import LiveMarketGateway
from procura_cl.infrastructure.sqlite_repository import SQLiteRepository


def build_gateway(settings: Settings, repository: SQLiteRepository) -> MarketGateway:
    if settings.data_mode == "demo":
        return DemoMarketGateway()
    if settings.data_mode == "live":
        ticket = settings.market_ticket
        if not ticket:
            raise ConfigurationError(
                "CHILE_PUBLIC_MARKET_TICKET is required when PROCURA_DATA_MODE=live"
            )
        return CachedMarketGateway(
            BudgetedMarketGateway(
                LiveMarketGateway(ticket, timeout=settings.api_timeout_seconds),
                repository,
                daily_limit=settings.daily_request_limit,
            ),
            repository,
            ttl_seconds=settings.cache_ttl_seconds,
        )
    raise ConfigurationError(f"Unsupported data mode: {settings.data_mode}")
