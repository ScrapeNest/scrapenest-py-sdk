from __future__ import annotations

import json

import httpx
import pytest

from conftest import async_client, sync_client
from scrapenest import ConflictError

ORG_ID = "0e1f2a3b-0000-4000-8000-000000000003"

HOLD = {
    "hold_id": "9d8c7b6a-0000-4000-8000-000000000004",
    "org_id": ORG_ID,
    "scope_type": "job",
    "scope_ref": "5a4b3c2d-0000-4000-8000-000000000005",
    "status": "active",
    "justification": "litigation hold, case FR-2026-042",
    "created_at": "2026-06-07T14:00:00+00:00",
    "expires_at": None,
    "released_at": None,
}


def test_retention_policy_roundtrip() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "org_id": ORG_ID,
                "retention_days": 90,
                "max_retention_days": 365,
                "legal_hold_enabled": True,
                "policy_version": 4,
                "updated_at": "2026-06-07T14:00:00+00:00",
            },
        )

    client = sync_client(handler)

    policy = client.retention.get_policy()
    assert policy.retention_days == 90
    assert policy.max_retention_days == 365

    client.retention.update_policy(retention_days=90, legal_hold_enabled=True)
    assert seen[1].method == "PUT"
    assert json.loads(seen[1].content) == {"retention_days": 90, "legal_hold_enabled": True}


def test_update_policy_conflict_maps_to_conflict_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "error": {
                    "code": "active_hold_conflict",
                    "message": "Retention cannot drop below an active legal hold.",
                }
            },
        )

    client = sync_client(handler)
    with pytest.raises(ConflictError) as excinfo:
        client.retention.update_policy(retention_days=1, legal_hold_enabled=False)
    assert excinfo.value.error == "active_hold_conflict"


def test_hold_lifecycle() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/release"):
            return httpx.Response(
                200,
                json={
                    "hold_id": HOLD["hold_id"],
                    "status": "released",
                    "released_at": "2026-06-08T09:00:00+00:00",
                },
            )
        if request.method == "POST":
            return httpx.Response(201, json=HOLD)
        return httpx.Response(200, json={"org_id": ORG_ID, "items": [HOLD]})

    client = sync_client(handler)

    hold = client.retention.create_hold(
        scope_type="job",
        scope_ref=str(HOLD["scope_ref"]),
        justification="litigation hold, case FR-2026-042",
    )
    assert hold.status == "active"
    body = json.loads(seen[0].content)
    assert body["scope_type"] == "job"
    assert "expires_at" not in body

    holds = client.retention.list_holds()
    assert holds.org_id == ORG_ID
    assert holds.items[0].hold_id == HOLD["hold_id"]

    release = client.retention.release_hold(
        str(HOLD["hold_id"]), release_notes="case closed, counsel sign-off attached"
    )
    assert release.status == "released"
    assert json.loads(seen[2].content) == {
        "release_notes": "case closed, counsel sign-off attached"
    }


def test_org_ip_allowlist_roundtrip() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"org_id": ORG_ID, "allowed_cidrs": ["203.0.113.0/24"]})

    client = sync_client(handler)

    allowlist = client.org.get_ip_allowlist()
    assert allowlist.allowed_cidrs == ["203.0.113.0/24"]

    client.org.set_ip_allowlist(["203.0.113.0/24"])
    assert seen[1].method == "PUT"
    assert seen[1].url.path == "/v1/org/security/ip-allowlist"
    assert json.loads(seen[1].content) == {"allowed_cidrs": ["203.0.113.0/24"]}


async def test_async_retention_and_org_mirror_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "retention-holds" in request.url.path:
            return httpx.Response(200, json={"org_id": ORG_ID, "items": [HOLD]})
        return httpx.Response(200, json={"org_id": ORG_ID, "allowed_cidrs": []})

    async with async_client(handler) as client:
        holds = await client.retention.list_holds()
        assert holds.items[0].scope_type == "job"

        allowlist = await client.org.get_ip_allowlist()
        assert allowlist.allowed_cidrs == []
