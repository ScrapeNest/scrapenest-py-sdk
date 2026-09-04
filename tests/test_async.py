from __future__ import annotations

import httpx
import pytest

from scrapenest import AsyncScrapeNestClient, NotFoundError


def make_client(handler, download_handler=None, *, max_retries=0) -> AsyncScrapeNestClient:
    return AsyncScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        download_transport=httpx.MockTransport(download_handler or handler),
    )


@pytest.mark.asyncio
async def test_async_scrape_polls_until_success() -> None:
    responses = [
        httpx.Response(
            201,
            json={
                "job_id": "job-1",
                "status": "queued",
                "created_at": "2026-06-07T14:00:00+00:00",
                "artifact_ids": [],
            },
        ),
        httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "succeeded",
                "job_type": "light",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": "2026-06-07T14:00:01+00:00",
                "failure_reason": None,
                "artifact_ids": ["a1"],
                "artifacts": [
                    {
                        "artifact_id": "a1",
                        "artifact_type": "html",
                        "byte_size": 10,
                        "content_hash": "x",
                        "created_at": "2026-06-07T14:00:01+00:00",
                    }
                ],
            },
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    async with make_client(handler) as client:
        result = await client.scrape(job_type="light", target_url="https://example.com")
        assert result.status == "succeeded"
        assert result.artifact_count == 1


@pytest.mark.asyncio
async def test_async_list_and_iter() -> None:
    total = 3

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        limit = int(request.url.params.get("limit", "2"))
        items = [
            {
                "job_id": f"job-{i}",
                "job_type": "light",
                "status": "succeeded",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "updated_at": None,
                "completed_at": None,
            }
            for i in range(offset, min(offset + limit, total))
        ]
        return httpx.Response(200, json={"items": items, "total": total, "limit": limit, "offset": offset})

    async with make_client(handler) as client:
        seen = [s.job_id async for s in client.jobs.iter(page_size=2)]
        assert seen == ["job-0", "job-1", "job-2"]


@pytest.mark.asyncio
async def test_async_error_taxonomy() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "nope"}})

    async with make_client(handler) as client:
        with pytest.raises(NotFoundError):
            await client.jobs.get("missing")


@pytest.mark.asyncio
async def test_async_artifact_download() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "artifact_id": "a1",
                "download_url": "https://objects.test/a1",
                "expires_at": "2026-06-07T14:15:01+00:00",
            },
        )

    def download_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>ok</html>")

    async with make_client(api_handler, download_handler) as client:
        text = await client.artifacts.download_text("a1")
        assert text == "<html>ok</html>"


@pytest.mark.asyncio
async def test_async_stats() -> None:
    stats_response = {
        "from": "2026-09-03T00:00:00+00:00",
        "to": "2026-09-04T00:00:00+00:00",
        "bucket_seconds": 3600,
        "buckets": [
            {
                "start": "2026-09-03T10:00:00+00:00",
                "total": 7, "succeeded": 6, "failed": 1,
                "running": 0, "queued": 0,
            },
        ],
        "totals": {
            "total": 7, "succeeded": 6, "failed": 1,
            "running": 0, "queued": 0,
            "success_rate": 0.857, "avg_duration_seconds": 2.1,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs/stats"
        return httpx.Response(200, json=stats_response)

    async with make_client(handler) as client:
        s = await client.jobs.stats(from_="2026-09-03T00:00:00Z")
        assert s.totals.total == 7
        assert s.totals.success_rate == 0.857
        assert len(s.buckets) == 1
