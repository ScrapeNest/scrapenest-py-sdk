from __future__ import annotations

import httpx
import pytest

from scrapenest import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ScrapeNestAPIError,
    ScrapeNestClient,
    ServerError,
    ValidationError,
)


def client_returning(status: int, body: dict) -> ScrapeNestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return ScrapeNestClient(
        api_key="sn_test",
        base_url="https://api.test",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, ValidationError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_status_maps_to_exception(status: int, expected: type[ScrapeNestAPIError]) -> None:
    client = client_returning(status, {"error": {"code": "x", "message": "m"}})
    with pytest.raises(expected) as exc:
        client.jobs.get("job-1")
    assert isinstance(exc.value, ScrapeNestAPIError)
    assert exc.value.status_code == status


def test_validation_error_exposes_field_details() -> None:
    client = client_returning(
        422,
        {
            "error": {
                "code": "validation_failed",
                "message": "Invalid request.",
                "request_id": "req-9",
                "details": [{"field": "target_url", "message": "Must be a valid HTTPS URL."}],
            }
        },
    )
    with pytest.raises(ValidationError) as exc:
        client.jobs.get("job-1")
    assert exc.value.request_id == "req-9"
    assert exc.value.details[0]["field"] == "target_url"
