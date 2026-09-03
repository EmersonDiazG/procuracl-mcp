import httpx

from procura_cl.infrastructure.agile_api import AgileApiClient


def test_real_contract_shape_accepts_numeric_document_ids() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["ticket"] == "secret"
        assert request.url.params["estado"] == "publicada"
        return httpx.Response(
            200,
            json={
                "success": "OK",
                "payload": {
                    "items": [
                        {
                            "codigo": "5539-124-COT26",
                            "nombre": "Terminal biométrico",
                            "estado": {"codigo": "publicada", "glosa": "Publicada"},
                            "documentos": [{"id": 1857188, "nombre": "anexo.pdf"}],
                            "fechas": {
                                "fecha_publicacion": "2026-09-03 17:45",
                                "fecha_cierre": "2026-09-07 12:00",
                            },
                            "montos": {"monto_disponible_clp": 2_200_000},
                            "institucion": {
                                "organismo_comprador": "UNIVERSIDAD DE CHILE",
                                "rut": "60.910.000-1",
                                "nombre_region": "Región Metropolitana de Santiago",
                            },
                        }
                    ],
                    "paginacion": {"total_resultados": 1},
                },
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = AgileApiClient("secret", http_client=http_client)

    items = client.search(
        query="software",
        published_from=None,
        published_until=None,
        statuses=["publicada"],
        regions=[13],
        page_size=10,
    )

    assert items[0].code == "5539-124-COT26"
    assert items[0].available_amount_clp == 2_200_000
    assert items[0].dates.published_at.tzinfo is not None
