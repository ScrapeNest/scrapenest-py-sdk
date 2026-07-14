from __future__ import annotations

from collections.abc import Callable

import httpx

from scrapenest import AsyncScrapeNestClient, ScrapeNestClient

Handler = Callable[[httpx.Request], httpx.Response]


def sync_client(handler: Handler, *, max_retries: int = 0) -> ScrapeNestClient:
    return ScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        download_transport=httpx.MockTransport(handler),
    )


def async_client(handler: Handler, *, max_retries: int = 0) -> AsyncScrapeNestClient:
    return AsyncScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        download_transport=httpx.MockTransport(handler),
    )
