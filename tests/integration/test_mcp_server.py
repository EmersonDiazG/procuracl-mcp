from uuid import uuid4

import pytest
from mcp import Client

from procura_cl.mcp.server import mcp


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.integration
async def test_search_tool_returns_structured_content() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool(
            "search_agile_purchases",
            {"query": "automatización", "region": "Metropolitana", "limit": 5},
        )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["count"] == 1
    assert result.structured_content["items"][0]["code"] == "DEMO-202-AG26"


@pytest.mark.anyio
@pytest.mark.integration
async def test_data_source_status_does_not_expose_a_ticket() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("get_data_source_status", {})

    assert result.structured_content is not None
    assert result.structured_content["mode"] == "demo"
    assert result.structured_content["source"] == "demo"
    assert result.structured_content["ticket_configured"] is False
    assert "ticket" not in result.structured_content


@pytest.mark.anyio
@pytest.mark.integration
async def test_watchlist_workflow_through_mcp() -> None:
    name = f"integration-{uuid4().hex}"
    async with Client(mcp, raise_exceptions=True) as client:
        created = await client.call_tool(
            "create_watchlist",
            {
                "name": name,
                "terms": ["automatización"],
                "kind": "agile_purchases",
                "region": "Metropolitana",
            },
        )
        assert created.structured_content is not None
        watchlist_id = created.structured_content["id"]

        synced = await client.call_tool("sync_watchlist", {"watchlist_id": watchlist_id})
        changes = await client.call_tool("list_watchlist_changes", {"watchlist_id": watchlist_id})
        deleted = await client.call_tool("delete_watchlist", {"watchlist_id": watchlist_id})

    assert synced.structured_content is not None
    assert synced.structured_content["records_new"] == 1
    assert changes.structured_content is not None
    assert changes.structured_content["result"][0]["opportunity"]["source"] == "demo"
    assert deleted.structured_content == {"result": True}
