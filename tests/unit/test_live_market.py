from decimal import Decimal

import pytest
from chile_public_market_sdk.models.tenders import Organization, Tender

from procura_cl.infrastructure.live_market import LiveMarketGateway


def test_region_name_is_normalized_to_upstream_code() -> None:
    assert LiveMarketGateway._region_codes("Región Metropolitana") == [13]
    assert LiveMarketGateway._region_codes("Ñuble") == [16]


def test_unknown_region_fails_before_external_request() -> None:
    with pytest.raises(ValueError, match="Unknown Chilean region"):
        LiveMarketGateway._region_codes("Región inventada")


@pytest.mark.parametrize(
    ("input_status", "expected"),
    [
        ("open", "activas"),
        ("Abierta", "activas"),
        ("publicada", "publicada"),
        ("awarded", "adjudicada"),
    ],
)
def test_tender_status_is_normalized(input_status: str, expected: str) -> None:
    assert LiveMarketGateway._tender_status(input_status) == expected


@pytest.mark.parametrize(
    ("input_status", "expected"),
    [
        ("open", ["publicada"]),
        ("Abierta", ["publicada"]),
        ("supplier selected", ["proveedor_seleccionado"]),
        ("oc_emitida", ["oc_emitida"]),
    ],
)
def test_agile_status_is_normalized(input_status: str, expected: list[str]) -> None:
    assert LiveMarketGateway._agile_statuses(input_status) == expected


def test_unknown_status_fails_before_external_request() -> None:
    with pytest.raises(ValueError, match="Unknown tender status"):
        LiveMarketGateway._tender_status("inventado")
    with pytest.raises(ValueError, match="Unknown Compra Ágil status"):
        LiveMarketGateway._agile_statuses("inventado")


def test_tender_mapping_preserves_provenance() -> None:
    upstream = Tender(
        external_code="1234-56-LE26",
        name="Integración de sistemas",
        status="Publicada",
        description="Construcción de una integración API",
        estimated_amount=Decimal("25000000"),
        buyer=Organization(organization_code="6945", organization_name="ChileCompra"),
    )

    result = LiveMarketGateway._tender(upstream)

    assert result.code == "1234-56-LE26"
    assert result.amount_clp == 25_000_000
    assert result.buyer.name == "ChileCompra"
    assert result.source == "mercado_publico"
