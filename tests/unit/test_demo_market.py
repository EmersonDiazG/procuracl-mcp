from datetime import date

import pytest

from procura_cl.domain.errors import OpportunityNotFoundError
from procura_cl.domain.models import OpportunitySearch
from procura_cl.infrastructure.demo_market import DemoMarketGateway


def test_search_agile_purchases_filters_query_and_region() -> None:
    gateway = DemoMarketGateway()

    results = gateway.search_agile_purchases(
        OpportunitySearch(query="automatización", region="Metropolitana")
    )

    assert [item.code for item in results] == ["DEMO-202-AG26"]
    assert results[0].source == "demo"


def test_search_tenders_filters_date() -> None:
    gateway = DemoMarketGateway()

    results = gateway.search_tenders(OpportunitySearch(published_on=date(2026, 8, 4)))

    assert len(results) == 1
    assert results[0].code == "DEMO-101-LE26"


def test_missing_opportunity_has_domain_error() -> None:
    gateway = DemoMarketGateway()

    with pytest.raises(OpportunityNotFoundError, match="was not found"):
        gateway.get_tender("missing")
