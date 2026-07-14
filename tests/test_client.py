from __future__ import annotations

import httpx
import pytest

from scrapenest import (
    ScrapeJobFailed,
    ScrapeJobTimeout,
    ScrapeNestAPIError,
    ScrapeNestClient,
)


def make_client(handler, download_handler=None, *, max_retries=0) -> ScrapeNestClient:
    return ScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
        download_transport=httpx.MockTransport(download_handler or handler),
    )


def test_scrape_polls_until_success_and_parses_artifacts() -> None:
    calls: list[tuple[str, str, bytes]] = []
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
                "tags": ["batch:test"],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": "2026-06-07T14:00:01+00:00",
                "failure_reason": None,
                "artifact_ids": ["artifact-1"],
                "artifacts": [
                    {
                        "artifact_id": "artifact-1",
                        "artifact_type": "html",
                        "byte_size": 123,
                        "content_hash": "sha256",
                        "created_at": "2026-06-07T14:00:01Z",
                    }
                ],
            },
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url), request.content))
        return responses.pop(0)

    client = make_client(handler)
    result = client.scrape(job_type="light", target_url="https://example.com")

    assert result.status == "succeeded"
    assert result.artifact_count == 1
    assert result.artifacts[0].byte_size == 123
    assert result.artifacts[0].size_bytes == 123
    assert calls[0][0] == "POST"
    assert calls[0][1] == "https://api.test/v1/jobs"
    assert calls[1][1] == "https://api.test/v1/jobs/job-1"


def test_jobs_get_can_request_download_urls() -> None:
    seen_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_url
        seen_url = str(request.url)
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "succeeded",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": "2026-06-07T14:00:01+00:00",
                "failure_reason": None,
                "artifact_ids": ["artifact-1"],
                "artifacts": [
                    {
                        "artifact_id": "artifact-1",
                        "artifact_type": "html",
                        "byte_size": 123,
                        "content_hash": "sha256",
                        "created_at": "2026-06-07T14:00:01+00:00",
                        "download_url": "https://objects.test/artifact-1",
                        "expires_at": "2026-06-07T14:15:01+00:00",
                    }
                ],
            },
        )

    client = make_client(handler)
    job = client.jobs.get("job-1", include_download_urls=True, ttl_seconds=600)

    assert "include_download_urls=true" in seen_url
    assert "ttl_seconds=600" in seen_url
    assert job.artifacts[0].download_url == "https://objects.test/artifact-1"


def test_jobs_get_exposes_blocked_outcome() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "succeeded",
                "outcome": "blocked",
                "block": {"blocked": True, "signal": "anti_bot_challenge", "http_status": 403},
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-07-12T19:45:00+00:00",
                "completed_at": "2026-07-12T19:45:09+00:00",
                "failure_reason": None,
                "artifact_ids": [],
                "artifacts": [],
            },
        )

    job = make_client(handler).jobs.get("job-1")

    # status says the crawl ran; outcome says it did not deliver.
    assert job.status == "succeeded"
    assert job.outcome == "blocked"
    assert job.blocked is True
    assert job.block is not None
    assert job.block.signal == "anti_bot_challenge"
    assert job.block.http_status == 403


def test_artifact_download_helpers() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.test/v1/artifacts/artifact-1/download?ttl_seconds=600"
        return httpx.Response(
            200,
            json={
                "artifact_id": "artifact-1",
                "download_url": "https://objects.test/artifact-1",
                "expires_at": "2026-06-07T14:15:01+00:00",
            },
        )

    def download_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://objects.test/artifact-1"
        return httpx.Response(200, content=b"<html>ok</html>")

    client = make_client(api_handler, download_handler)

    assert client.artifacts.download_text("artifact-1", ttl_seconds=600) == "<html>ok</html>"


def test_scrape_raises_on_failed_job() -> None:
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
                "status": "failed",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": "2026-06-07T14:00:01+00:00",
                "failure_reason": "stealth_blocked",
                "artifact_ids": [],
                "artifacts": [],
            },
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    client = make_client(handler)

    with pytest.raises(ScrapeJobFailed) as exc:
        client.scrape(job_type="stealth", target_url="https://example.com")

    assert exc.value.job_id == "job-1"
    assert exc.value.failure_reason == "stealth_blocked"


def test_api_error_parses_error_payload_and_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests.",
                    "request_id": "req-1",
                }
            },
            headers={"Retry-After": "3", "X-Request-Id": "req-header"},
        )

    client = make_client(handler)

    with pytest.raises(ScrapeNestAPIError) as exc:
        client.submit(job_type="light", target_url="https://example.com")

    assert exc.value.status_code == 429
    assert exc.value.error == "rate_limited"
    assert exc.value.message == "Too many requests."
    assert exc.value.retry_after == "3"
    # request_id from the error envelope is preferred over the header.
    assert exc.value.request_id == "req-1"


def test_scrape_timeout_keeps_job_id() -> None:
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
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if responses:
            return responses.pop(0)
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "running",
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

    with pytest.raises(ScrapeJobTimeout) as exc:
        client.scrape(job_type="light", target_url="https://example.com", timeout=1)

    assert exc.value.job_id == "job-1"
