from __future__ import annotations

import httpx
import pytest

from scrapenest import AsyncScrapeNestClient, ScrapeNestClient


def _capture() -> tuple[dict[str, str], httpx.MockTransport]:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, json={})

    return seen, httpx.MockTransport(handler)


def test_api_key_sets_x_api_key_header() -> None:
    seen, transport = _capture()
    client = ScrapeNestClient(api_key="sn_test", base_url="https://api.test", transport=transport)
    client._request("GET", "/v1/org")
    assert seen["x-api-key"] == "sn_test"
    assert "authorization" not in seen


def test_access_token_sets_bearer_header() -> None:
    seen, transport = _capture()
    client = ScrapeNestClient(access_token="jwt-abc", base_url="https://api.test", transport=transport)
    client._request("GET", "/v1/org")
    assert seen["authorization"] == "Bearer jwt-abc"
    assert "x-api-key" not in seen


def test_rejects_both_credentials() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ScrapeNestClient(api_key="sn_test", access_token="jwt-abc")


def test_rejects_no_credentials() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ScrapeNestClient()


@pytest.mark.asyncio
async def test_async_access_token_sets_bearer_header() -> None:
    seen, transport = _capture()
    async with AsyncScrapeNestClient(
        access_token="jwt-async", base_url="https://api.test", transport=transport
    ) as client:
        await client._request("GET", "/v1/org")
    assert seen["authorization"] == "Bearer jwt-async"
    assert "x-api-key" not in seen


@pytest.mark.asyncio
async def test_async_rejects_both_credentials() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        AsyncScrapeNestClient(api_key="sn_test", access_token="jwt-abc")
