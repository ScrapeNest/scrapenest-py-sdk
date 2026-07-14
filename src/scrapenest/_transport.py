"""Send loops with retry, shared in shape by the sync and async clients.

The sync and async variants differ only in their I/O primitives (blocking
`client.request` + `time.sleep` vs `await client.request` + `asyncio.sleep`);
the retry decision logic lives in `_retry.py`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from scrapenest._retry import compute_delay, is_retryable_status, parse_retry_after
from scrapenest.exceptions import ScrapeNestAPIError, ScrapeNestConnectionError


def raise_on_error(response: httpx.Response) -> httpx.Response:
    if not response.is_success:
        raise ScrapeNestAPIError.from_response(response)
    return response


def _connection_error(method: str, url: str, exc: Exception) -> ScrapeNestConnectionError:
    return ScrapeNestConnectionError(
        f"Could not reach ScrapeNest ({method} {url}): {exc}"
    )


def send_sync(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any | None = None,
    max_retries: int,
    backoff_factor: float,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = client.request(method, url, params=params, json=json)
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(compute_delay(attempt=attempt, backoff_factor=backoff_factor))
                continue
            raise _connection_error(method, url, exc) from exc

        if is_retryable_status(response.status_code) and attempt < max_retries:
            retry_after = parse_retry_after(response.headers.get("retry-after"))
            time.sleep(
                compute_delay(
                    attempt=attempt,
                    backoff_factor=backoff_factor,
                    retry_after=retry_after,
                )
            )
            continue

        return raise_on_error(response)

    raise _connection_error(method, url, last_exc or RuntimeError("retries exhausted"))


async def send_async(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any | None = None,
    max_retries: int,
    backoff_factor: float,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, params=params, json=json)
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt < max_retries:
                await asyncio.sleep(compute_delay(attempt=attempt, backoff_factor=backoff_factor))
                continue
            raise _connection_error(method, url, exc) from exc

        if is_retryable_status(response.status_code) and attempt < max_retries:
            retry_after = parse_retry_after(response.headers.get("retry-after"))
            await asyncio.sleep(
                compute_delay(
                    attempt=attempt,
                    backoff_factor=backoff_factor,
                    retry_after=retry_after,
                )
            )
            continue

        return raise_on_error(response)

    raise _connection_error(method, url, last_exc or RuntimeError("retries exhausted"))
