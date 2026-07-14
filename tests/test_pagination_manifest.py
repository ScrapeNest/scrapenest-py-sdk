from __future__ import annotations

import json

import httpx

from scrapenest import ScrapeNestClient


def make_client(handler, download_handler=None) -> ScrapeNestClient:
    return ScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=0,
        transport=httpx.MockTransport(handler),
        download_transport=httpx.MockTransport(download_handler or handler),
    )


def _summary(i: int) -> dict:
    return {
        "job_id": f"job-{i}",
        "job_type": "light",
        "status": "succeeded",
        "target_url": "https://example.com",
        "tags": [],
        "created_at": "2026-06-07T14:00:00+00:00",
        "updated_at": None,
        "completed_at": "2026-06-07T14:00:01+00:00",
    }


def test_jobs_iter_walks_all_pages() -> None:
    total = 5

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        limit = int(request.url.params.get("limit", "2"))
        items = [_summary(i) for i in range(offset, min(offset + limit, total))]
        return httpx.Response(200, json={"items": items, "total": total, "limit": limit, "offset": offset})

    client = make_client(handler)
    ids = [s.job_id for s in client.jobs.iter(page_size=2)]
    assert ids == [f"job-{i}" for i in range(total)]


def test_get_manifest_downloads_and_parses() -> None:
    manifest = {
        "manifest_version": "1.0.0",
        "job_id": "job-1",
        "engine": "stealth",
        "target_url": "https://example.com",
        "final_url": "https://example.com/home",
        "status": "completed",
        "outcome": "blocked",
        "block": {"blocked": True, "signal": "anti_bot_challenge", "http_status": 403},
        "response": {"http_status": 403, "headers": {"server": "cloudflare"}},
        "timing": {"started_at": None, "finished_at": None, "duration_ms": 1200},
        "user_agent": "Mozilla/5.0",
        "retry_count": 1,
        "request": {"job_type": "stealth"},
        "credits": {"weight": 10, "charged": False, "amount": 0},
        "artifacts": [],
    }

    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/download"):
            return httpx.Response(
                200,
                json={
                    "artifact_id": "art-manifest",
                    "download_url": "https://objects.test/manifest.json",
                    "expires_at": "2026-06-07T14:15:01+00:00",
                },
            )
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "failed",
                "job_type": "stealth",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": "2026-06-07T14:00:02+00:00",
                "failure_reason": None,
                "artifact_ids": ["art-manifest"],
                "artifacts": [
                    {
                        "artifact_id": "art-manifest",
                        "artifact_type": "manifest",
                        "byte_size": 500,
                        "content_hash": "a" * 64,
                        "created_at": "2026-06-07T14:00:02+00:00",
                        "download_url": "https://objects.test/manifest.json",
                        "expires_at": "2026-06-07T14:15:01+00:00",
                    }
                ],
            },
        )

    def download_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(manifest).encode())

    client = make_client(api_handler, download_handler)
    parsed = client.jobs.get_manifest("job-1")
    assert parsed is not None
    assert parsed.outcome == "blocked"
    assert parsed.blocked is True
    assert parsed.block is not None and parsed.block.http_status == 403
    assert parsed.credits is not None and parsed.credits.charged is False


def test_get_manifest_returns_none_when_absent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "running",
                "job_type": "light",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": None,
                "failure_reason": None,
                "artifact_ids": [],
                "artifacts": [],
            },
        )

    client = make_client(handler)
    assert client.jobs.get_manifest("job-1") is None
