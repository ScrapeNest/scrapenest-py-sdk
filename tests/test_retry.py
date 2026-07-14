from __future__ import annotations

import httpx
import pytest

from scrapenest import RateLimitError, ScrapeNestClient, ScrapeNestConnectionError
from scrapenest._retry import compute_delay, is_retryable_status, parse_retry_after


def make_client(handler, *, max_retries=2, backoff_factor=0.0) -> ScrapeNestClient:
    return ScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        transport=httpx.MockTransport(handler),
    )


def test_is_retryable_status() -> None:
    assert is_retryable_status(429)
    assert is_retryable_status(503)
    assert not is_retryable_status(400)
    assert not is_retryable_status(200)


def test_parse_retry_after() -> None:
    assert parse_retry_after("3") == 3.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("nonsense") is None
    assert parse_retry_after("-5") is None


def test_compute_delay_honors_retry_after() -> None:
    assert compute_delay(attempt=0, backoff_factor=1.0, retry_after=2.0) == 2.0
    # caps at 30s
    assert compute_delay(attempt=0, backoff_factor=1.0, retry_after=120.0) == 30.0


def test_compute_delay_backoff_is_bounded() -> None:
    for attempt in range(6):
        delay = compute_delay(attempt=attempt, backoff_factor=0.5)
        assert 0.0 <= delay <= 30.0


def test_retries_5xx_then_succeeds() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(503, json={"error": {"code": "unavailable", "message": "down"}})
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "succeeded",
                "target_url": "https://example.com",
                "tags": [],
                "created_at": "2026-06-07T14:00:00+00:00",
                "completed_at": None,
                "failure_reason": None,
                "artifact_ids": [],
                "artifacts": [],
            },
        )

    client = make_client(handler, max_retries=3)
    job = client.jobs.get("job-1")
    assert job.status == "succeeded"
    assert len(attempts) == 3


def test_retries_exhausted_raises_rate_limit_error() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, json={"error": {"code": "rate_limited", "message": "slow down"}})

    client = make_client(handler, max_retries=2)
    with pytest.raises(RateLimitError) as exc:
        client.jobs.get("job-1")
    assert exc.value.status_code == 429
    assert len(calls) == 3  # initial + 2 retries


def test_transport_error_becomes_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = make_client(handler, max_retries=1)
    with pytest.raises(ScrapeNestConnectionError):
        client.jobs.get("job-1")


def test_idempotency_token_auto_attached_and_stable_across_retries() -> None:
    seen_tokens: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        seen_tokens.append(body["idempotency_token"])
        if len(seen_tokens) < 2:
            return httpx.Response(503, json={"error": {"code": "x", "message": "y"}})
        return httpx.Response(
            201,
            json={
                "job_id": "job-1",
                "status": "queued",
                "created_at": "2026-06-07T14:00:00+00:00",
                "artifact_ids": [],
            },
        )

    client = make_client(handler, max_retries=2)
    result = client.submit(job_type="light", target_url="https://example.com")
    assert result.job_id == "job-1"
    assert len(seen_tokens) == 2
    assert seen_tokens[0] == seen_tokens[1]  # same token reused on retry


def test_idempotent_replay_flag_on_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job_id": "job-1",
                "status": "queued",
                "created_at": "2026-06-07T14:00:00+00:00",
                "artifact_ids": [],
            },
        )

    client = make_client(handler, max_retries=0)
    result = client.submit(
        job_type="light", target_url="https://example.com", idempotency_token="fixed"
    )
    assert result.idempotent_replay is True
