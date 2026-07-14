from __future__ import annotations

import json

import httpx

from conftest import async_client, sync_client

KEY_SUMMARY = {
    "api_key_id": "6b2f8f2e-0000-4000-8000-000000000001",
    "name": "ci-pipeline",
    "description": None,
    "prefix": "sn_live_a1b2",
    "status": "active",
    "scopes": ["jobs.create", "jobs.read", "artifacts.read"],
    "rate_limit_rpm": 300,
    "daily_quota": 10000,
    "max_concurrent_jobs": 5,
    "enforcement_mode": "block",
    "allowed_cidrs": ["10.0.0.0/8"],
    "last_used_at": "2026-06-07T13:59:00+00:00",
    "rotated_at": None,
    "expires_at": None,
    "created_at": "2026-01-15T09:00:00+00:00",
}


def test_list_parses_key_summaries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/keys"
        return httpx.Response(200, json={"items": [KEY_SUMMARY]})

    client = sync_client(handler)
    keys = client.api_keys.list()

    assert len(keys) == 1
    assert keys[0].prefix == "sn_live_a1b2"
    assert keys[0].scopes == ["jobs.create", "jobs.read", "artifacts.read"]
    assert keys[0].rotated_at is None
    assert keys[0].last_used_at is not None


def test_create_sends_only_provided_fields_and_returns_token_once() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            201,
            json={
                "api_key_id": KEY_SUMMARY["api_key_id"],
                "name": "ci-pipeline",
                "description": None,
                "prefix": "sn_live_a1b2",
                "token": "sn_live_a1b2c3d4_secret",
                "scopes": ["jobs.create"],
                "rate_limit_rpm": 300,
                "daily_quota": 10000,
                "max_concurrent_jobs": 5,
                "enforcement_mode": "block",
                "expires_at": None,
                "created_at": "2026-06-07T14:00:00+00:00",
            },
        )

    client = sync_client(handler)
    created = client.api_keys.create(name="ci-pipeline", scopes=["jobs.create"])

    body = json.loads(seen[0].content)
    assert body == {"name": "ci-pipeline", "scopes": ["jobs.create"]}
    assert created.token == "sn_live_a1b2c3d4_secret"


def test_rotate_and_revoke() -> None:
    seen: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.content))
        if request.url.path.endswith("/rotate"):
            return httpx.Response(
                200,
                json={
                    "api_key_id": KEY_SUMMARY["api_key_id"],
                    "prefix": "sn_live_z9y8",
                    "token": "sn_live_z9y8_new_secret",
                    "rotated_at": "2026-06-07T14:05:00+00:00",
                },
            )
        return httpx.Response(
            200,
            json={
                "api_key_id": KEY_SUMMARY["api_key_id"],
                "status": "revoked",
                "revoked_at": "2026-06-07T14:06:00+00:00",
            },
        )

    client = sync_client(handler)
    key_id = str(KEY_SUMMARY["api_key_id"])

    rotation = client.api_keys.rotate(key_id)
    assert rotation.token == "sn_live_z9y8_new_secret"
    assert rotation.prefix == "sn_live_z9y8"

    revocation = client.api_keys.revoke(key_id, reason="leaked in CI logs")
    assert revocation.status == "revoked"

    assert seen[0][1] == f"/v1/keys/{key_id}/rotate"
    assert seen[1][1] == f"/v1/keys/{key_id}/revoke"
    assert json.loads(seen[1][2]) == {"reason": "leaked in CI logs"}


def test_set_ip_allowlist_replaces_cidrs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert json.loads(request.content) == {"allowed_cidrs": ["192.0.2.0/24"]}
        return httpx.Response(
            200,
            json={"api_key_id": KEY_SUMMARY["api_key_id"], "allowed_cidrs": ["192.0.2.0/24"]},
        )

    client = sync_client(handler)
    result = client.api_keys.set_ip_allowlist(str(KEY_SUMMARY["api_key_id"]), ["192.0.2.0/24"])
    assert result.allowed_cidrs == ["192.0.2.0/24"]


async def test_async_api_keys_mirror_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [KEY_SUMMARY]})

    async with async_client(handler) as client:
        keys = await client.api_keys.list()
        assert keys[0].name == "ci-pipeline"
