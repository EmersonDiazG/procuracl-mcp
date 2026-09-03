from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from procura_cl.domain.errors import OpportunityNotFoundError, UpstreamServiceError

API_V2_URL = "https://api2.mercadopublico.cl/v2"
_SANTIAGO = ZoneInfo("America/Santiago")


class _APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AgileStatus(_APIModel):
    code: str = Field(alias="codigo")
    label: str = Field(alias="glosa")


class AgileDates(_APIModel):
    published_at: datetime = Field(alias="fecha_publicacion")
    closing_at: datetime | None = Field(default=None, alias="fecha_cierre")

    @field_validator("published_at", "closing_at")
    @classmethod
    def attach_upstream_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=_SANTIAGO)


class AgileInstitution(_APIModel):
    buyer_organization: str = Field(alias="organismo_comprador")
    tax_id: str = Field(alias="rut")
    region_name: str | None = Field(default=None, alias="nombre_region")


class AgileAmounts(_APIModel):
    available_amount_clp: Decimal | None = Field(default=None, alias="monto_disponible_clp")


class AgilePurchaseRecord(_APIModel):
    code: str = Field(alias="codigo")
    name: str = Field(alias="nombre")
    description: str | None = Field(default=None, alias="descripcion")
    status: AgileStatus = Field(alias="estado")
    dates: AgileDates = Field(alias="fechas")
    institution: AgileInstitution = Field(alias="institucion")
    amounts: AgileAmounts | None = Field(default=None, alias="montos")
    budget: AgileAmounts | None = Field(default=None, alias="presupuesto")

    @property
    def available_amount_clp(self) -> Decimal | None:
        money = self.amounts or self.budget
        return money.available_amount_clp if money is not None else None


class AgilePage(_APIModel):
    items: list[AgilePurchaseRecord]


class AgileApiClient:
    """Small anti-corruption client for the evolving official Compra Ágil v2 contract."""

    def __init__(
        self,
        ticket: str,
        *,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._ticket = ticket
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def search(
        self,
        *,
        query: str | None,
        published_from: datetime | None,
        published_until: datetime | None,
        statuses: list[str] | None,
        regions: list[int] | None,
        page_size: int,
    ) -> list[AgilePurchaseRecord]:
        payload = self._request(
            "compra-agil",
            params={
                "q": query,
                "publicado_desde": published_from.isoformat() if published_from else None,
                "publicado_hasta": published_until.isoformat() if published_until else None,
                "estado": ",".join(statuses) if statuses else None,
                "region": ",".join(str(region) for region in regions) if regions else None,
                "tamano_pagina": page_size,
                "numero_pagina": 1,
                "ordenar_por": "FechaUltimaModificacion",
            },
        )
        try:
            return AgilePage.model_validate(payload).items
        except ValidationError as error:
            raise UpstreamServiceError(
                "Compra Ágil returned an incompatible list contract"
            ) from error

    def get(self, code: str) -> AgilePurchaseRecord:
        payload = self._request(f"compra-agil/{code}", not_found_code=code)
        try:
            return AgilePurchaseRecord.model_validate(payload)
        except ValidationError as error:
            raise UpstreamServiceError(
                "Compra Ágil returned an incompatible detail contract"
            ) from error

    def _request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        not_found_code: str | None = None,
    ) -> Any:
        compact_params = {key: value for key, value in (params or {}).items() if value is not None}
        try:
            response = self._http_client.get(
                f"{API_V2_URL}/{path.lstrip('/')}",
                params=compact_params,
                headers={"ticket": self._ticket},
            )
        except httpx.TimeoutException as error:
            raise UpstreamServiceError("Compra Ágil request timed out") from error
        except httpx.RequestError as error:
            raise UpstreamServiceError("Could not communicate with Compra Ágil") from error

        if response.status_code in {401, 403}:
            raise UpstreamServiceError("Compra Ágil rejected the configured API ticket")
        if response.status_code == 404 and not_found_code is not None:
            raise OpportunityNotFoundError(f"Compra Ágil {not_found_code!r} was not found")
        if response.status_code == 429:
            raise UpstreamServiceError("Compra Ágil request limit was exceeded")
        if response.is_error:
            raise UpstreamServiceError(f"Compra Ágil returned HTTP {response.status_code}")

        try:
            envelope = response.json()
        except ValueError as error:
            raise UpstreamServiceError("Compra Ágil returned invalid JSON") from error
        if not isinstance(envelope, dict) or envelope.get("success") != "OK":
            raise UpstreamServiceError("Compra Ágil returned an unsuccessful response")
        payload = envelope.get("payload")
        if payload is None:
            raise UpstreamServiceError("Compra Ágil response did not include payload")
        return payload
