from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ScrapeNestError(Exception):
    """Base class for all ScrapeNest SDK errors."""


class ScrapeJobFailed(ScrapeNestError):
    """A job reached a terminal failed state."""

    def __init__(self, *, job_id: str, failure_reason: str | None) -> None:
        self.job_id = job_id
        self.failure_reason = failure_reason
        super().__init__(f"Job {job_id} failed: {failure_reason or 'unknown reason'}")


class ScrapeJobTimeout(ScrapeNestError):
    """A sync wait timed out while the server-side job continued running."""

    def __init__(self, *, job_id: str, timeout_seconds: int) -> None:
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Job {job_id} did not complete within {timeout_seconds}s. "
            "The job is still running; poll GET /v1/jobs/{job_id} or use webhooks."
        )


class ScrapeNestConnectionError(ScrapeNestError):
    """A transport-level failure (DNS, TLS, connect/read timeout) after retries were exhausted."""


class ScrapeNestAPIError(ScrapeNestError):
    """A non-2xx response from the ScrapeNest API."""

    def __init__(
        self,
        *,
        status_code: int,
        body: str,
        headers: Mapping[str, str] | None = None,
        error: str | None = None,
        message: str | None = None,
        request_id: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})
        self.error = error
        self.message = message
        self.details = details or []
        # Prefer the request id from the error envelope, fall back to the header.
        self.request_id = request_id or self.headers.get("x-request-id")
        self.retry_after = self.headers.get("retry-after")

        detail = message or error or body
        super().__init__(f"API error {status_code}: {detail}")

    @classmethod
    def from_response(cls, response: Any) -> ScrapeNestAPIError:
        error = None
        message = None
        request_id = None
        details: list[dict[str, Any]] | None = None
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            raw_error = payload.get("error")
            if isinstance(raw_error, Mapping):
                # Standard envelope: {"error": {"code", "message", "request_id", "details"}}
                code = raw_error.get("code")
                msg = raw_error.get("message")
                rid = raw_error.get("request_id")
                raw_details = raw_error.get("details")
                error = code if isinstance(code, str) else None
                message = msg if isinstance(msg, str) else None
                request_id = rid if isinstance(rid, str) else None
                details = (
                    [dict(d) for d in raw_details if isinstance(d, Mapping)]
                    if isinstance(raw_details, list)
                    else None
                )
            else:
                # Legacy flat shape: {"error": "...", "message": "..."}
                raw_message = payload.get("message")
                error = raw_error if isinstance(raw_error, str) else None
                message = raw_message if isinstance(raw_message, str) else None

        exc_cls = _STATUS_TO_EXCEPTION.get(response.status_code)
        if exc_cls is None and 500 <= response.status_code < 600:
            exc_cls = ServerError
        if exc_cls is None:
            exc_cls = cls

        return exc_cls(
            status_code=response.status_code,
            body=response.text,
            headers=response.headers,
            error=error,
            message=message,
            request_id=request_id,
            details=details,
        )


class BadRequestError(ScrapeNestAPIError):
    """HTTP 400 - the request was malformed."""


class AuthenticationError(ScrapeNestAPIError):
    """HTTP 401 - missing or invalid API key."""


class PermissionDeniedError(ScrapeNestAPIError):
    """HTTP 403 - authenticated but the key lacks the required scope or tenant."""


class NotFoundError(ScrapeNestAPIError):
    """HTTP 404 - the resource does not exist."""


class ConflictError(ScrapeNestAPIError):
    """HTTP 409 - the request conflicts with the current resource state."""


class ValidationError(ScrapeNestAPIError):
    """HTTP 422 - request validation failed. See `details` for field-level problems."""


class RateLimitError(ScrapeNestAPIError):
    """HTTP 429 - rate limit exceeded. See `retry_after`."""


class ServerError(ScrapeNestAPIError):
    """HTTP 5xx - an unexpected server-side error."""


_STATUS_TO_EXCEPTION: dict[int, type[ScrapeNestAPIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
}


class WebhookVerificationError(ScrapeNestError):
    """A webhook payload failed signature verification."""
