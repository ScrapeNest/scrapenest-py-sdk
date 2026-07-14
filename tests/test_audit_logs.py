from __future__ import annotations

import httpx

from conftest import async_client, sync_client

ENTRY = {
    "id": "7c6b5a49-0000-4000-8000-000000000006",
    "event_type": "api_key.created",
    "action": "create",
    "actor_id": "3a2b1c0d-0000-4000-8000-000000000007",
    "actor_type": "user",
    "result": "success",
    "severity": "medium",
    "metadata": {"key_prefix": "sn_live_abcd"},
    "source_ip": "203.0.113.7",
    "occurred_at": "2026-07-07T10:30:00+00:00",
}


def test_list_audit_logs_with_filters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"items": [ENTRY], "total": 1, "limit": 50, "offset": 0},
        )

    client = sync_client(handler)

    page = client.audit_logs.list(severity="medium", result="success", limit=50)
    assert page.total == 1
    entry = page.items[0]
    assert entry.event_type == "api_key.created"
    assert entry.actor_type == "user"
    assert entry.metadata == {"key_prefix": "sn_live_abcd"}
    assert entry.occurred_at is not None

    assert seen[0].method == "GET"
    assert seen[0].url.path == "/v1/audit-logs"
    params = dict(seen[0].url.params)
    assert params["severity"] == "medium"
    assert params["result"] == "success"
    assert params["limit"] == "50"
    # Unset filters must not be sent.
    assert "event_type" not in params
    assert "offset" not in params


def test_iter_audit_logs_pages_transparently() -> None:
    pages = [
        {"items": [ENTRY, ENTRY], "total": 3, "limit": 2, "offset": 0},
        {"items": [ENTRY], "total": 3, "limit": 2, "offset": 2},
    ]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = pages[calls["n"]]
        calls["n"] += 1
        return httpx.Response(200, json=page)

    client = sync_client(handler)

    entries = list(client.audit_logs.iter(page_size=2))
    assert len(entries) == 3
    assert calls["n"] == 2


async def test_async_audit_logs_mirror_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"items": [ENTRY], "total": 1, "limit": 50, "offset": 0},
        )

    async with async_client(handler) as client:
        page = await client.audit_logs.list(event_type="api_key.created")
        assert page.items[0].severity == "medium"
