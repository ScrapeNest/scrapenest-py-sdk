from __future__ import annotations

import json
from datetime import datetime

import httpx

from conftest import async_client, sync_client

MONITOR = {
    "id": "mon-1",
    "name": "hourly prices",
    "cron": "0 * * * *",
    "timezone": "Europe/Paris",
    "job_type": "light",
    "target_url": "https://example.com/pricing",
    "overlap_policy": "skip",
    "status": "active",
    "payload": {"artifact_options": {"include_extraction": True}},
    "last_run_at": "2026-06-07T13:00:00+00:00",
    "next_run_at": "2026-06-07T14:00:00+00:00",
    "created_at": "2026-06-01T09:00:00+00:00",
    "updated_at": None,
}


def test_create_sends_full_body_and_parses_timestamps() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json=MONITOR)

    client = sync_client(handler)
    monitor = client.monitors.create(
        name="hourly prices",
        cron="0 * * * *",
        job_type="light",
        target_url="https://example.com/pricing",
        timezone="Europe/Paris",
        payload={"artifact_options": {"include_extraction": True}},
    )

    assert seen[0].method == "POST"
    assert seen[0].url.path == "/v1/monitors"
    body = json.loads(seen[0].content)
    assert body["cron"] == "0 * * * *"
    assert "overlap_policy" not in body  # omitted, server default applies

    assert monitor.id == "mon-1"
    assert monitor.next_run_at == datetime.fromisoformat("2026-06-07T14:00:00+00:00")
    assert monitor.updated_at is None


def test_update_pause_resume_delete_hit_expected_routes() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        return httpx.Response(200, json=MONITOR)

    client = sync_client(handler)
    client.monitors.update(
        "mon-1",
        name="hourly prices",
        cron="30 * * * *",
        job_type="light",
        target_url="https://example.com/pricing",
    )
    client.monitors.pause("mon-1")
    client.monitors.resume("mon-1")
    client.monitors.delete("mon-1")

    assert seen == [
        ("PATCH", "/v1/monitors/mon-1"),
        ("POST", "/v1/monitors/mon-1/pause"),
        ("POST", "/v1/monitors/mon-1/resume"),
        ("DELETE", "/v1/monitors/mon-1"),
    ]


def test_iter_walks_offset_pages() -> None:
    pages = [
        {"items": [dict(MONITOR, id=f"mon-{i}") for i in (1, 2)], "total": 3, "limit": 2, "offset": 0},
        {"items": [dict(MONITOR, id="mon-3")], "total": 3, "limit": 2, "offset": 2},
    ]
    offsets: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offsets.append(request.url.params.get("offset"))
        return httpx.Response(200, json=pages.pop(0))

    client = sync_client(handler)
    ids = [m.id for m in client.monitors.iter(page_size=2)]

    assert ids == ["mon-1", "mon-2", "mon-3"]
    assert offsets == ["0", "2"]


def test_runs_parses_fired_at() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/monitors/mon-1/runs"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "run-1",
                        "monitor_id": "mon-1",
                        "status": "minted",
                        "fired_at": "2026-06-07T13:00:00+00:00",
                        "job_id": "job-9",
                    },
                    {
                        "id": "run-2",
                        "monitor_id": "mon-1",
                        "status": "skipped_quota",
                        "fired_at": None,
                        "detail": "daily quota exhausted",
                    },
                ],
                "total": 2,
                "limit": 50,
                "offset": 0,
            },
        )

    client = sync_client(handler)
    runs = client.monitors.runs("mon-1")

    assert runs.items[0].job_id == "job-9"
    assert runs.items[0].monitor_id == "mon-1"
    assert runs.items[0].fired_at is not None
    assert runs.items[1].fired_at is None
    assert runs.items[1].detail == "daily quota exhausted"


async def test_async_monitors_mirror_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MONITOR)

    async with async_client(handler) as client:
        monitor = await client.monitors.get("mon-1")
        assert monitor.name == "hourly prices"

        paused = await client.monitors.pause("mon-1")
        assert paused.id == "mon-1"



WATCHED_MONITOR = {
    **MONITOR,
    "detection": {
        "enabled": True,
        "mode": "selector",
        "selector": ".price",
        "ignore_selectors": [],
        "min_change_ratio": 0.05,
        "consecutive": 1,
        "cooldown_seconds": 0,
        "notify": {"webhook": True, "email": ["alerts@acme.eu"]},
        "health": {"status": "ok", "last_checked_at": None, "last_change_at": None},
    },
}


def test_create_with_detection_sends_block_and_parses_it() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json=WATCHED_MONITOR)

    client = sync_client(handler)
    monitor = client.monitors.create(
        name="hourly prices",
        cron="0 * * * *",
        job_type="standard",
        target_url="https://example.com/pricing",
        detection={"enabled": True, "mode": "selector", "selector": ".price",
                   "notify": {"email": ["alerts@acme.eu"]}},
    )

    body = json.loads(seen[0].content)
    assert body["detection"]["mode"] == "selector"
    assert body["detection"]["selector"] == ".price"
    assert monitor.detection is not None
    assert monitor.detection["enabled"] is True
    assert monitor.detection["health"]["status"] == "ok"


def test_update_omitting_detection_leaves_it_out_of_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=MONITOR)

    client = sync_client(handler)
    client.monitors.update(
        "mon-1", name="hourly prices", cron="0 * * * *",
        job_type="light", target_url="https://example.com/pricing",
    )
    body = json.loads(seen[0].content)
    assert "detection" not in body  # omitted -> detection left unchanged


CHANGES = {
    "items": [
        {
            "id": "chg-1",
            "job_id": "job-1",
            "run_id": "run-1",
            "detected_at": "2026-07-07T01:00:00+00:00",
            "old_fingerprint": "sha256:aaa",
            "new_fingerprint": "sha256:bbb",
            "change_ratio": 0.25,
            "summary": None,
            "has_diff": True,
            "notified_channels": ["webhook", "email"],
        }
    ],
    "total": 1,
    "limit": 25,
    "offset": 0,
}


def test_changes_route_and_parsing() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=CHANGES)

    client = sync_client(handler)
    page = client.monitors.changes("mon-1")
    assert seen[0] == "/v1/monitors/mon-1/changes"
    assert page.total == 1
    chg = page.items[0]
    assert chg.new_fingerprint == "sha256:bbb"
    assert chg.change_ratio == 0.25
    assert chg.has_diff is True
    assert chg.notified_channels == ["webhook", "email"]
    assert chg.detected_at == datetime.fromisoformat("2026-07-07T01:00:00+00:00")



DIFF_RESPONSE = {
    "change_id": "chg-1",
    "format": "unified",
    "diff": "--- before\n+++ after\n@@ -1 +1 @@\n-old\n+new",
}


def test_change_diff_hits_correct_route() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=DIFF_RESPONSE)

    client = sync_client(handler)
    client.monitors.change_diff("mon-1", "chg-1")

    assert seen[0].method == "GET"
    assert seen[0].url.path == "/v1/monitors/mon-1/changes/chg-1/diff"


def test_change_diff_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=DIFF_RESPONSE)

    client = sync_client(handler)
    d = client.monitors.change_diff("mon-1", "chg-1")

    assert d.change_id == "chg-1"
    assert d.format == "unified"
    assert "+new" in d.diff
    assert "-old" in d.diff


def test_change_diff_defaults_format_to_unified() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"change_id": "chg-2", "diff": "some diff"})

    client = sync_client(handler)
    d = client.monitors.change_diff("mon-1", "chg-2")

    assert d.format == "unified"
    assert d.diff == "some diff"


async def test_async_change_diff() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=DIFF_RESPONSE)

    async with async_client(handler) as client:
        d = await client.monitors.change_diff("mon-1", "chg-1")
        assert d.change_id == "chg-1"
        assert d.format == "unified"
