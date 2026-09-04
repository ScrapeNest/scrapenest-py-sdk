from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, TypeVar

import httpx

from scrapenest._ops import Op
from scrapenest._transport import send_sync
from scrapenest._version import __version__
from scrapenest.exceptions import ScrapeJobFailed, ScrapeJobTimeout
from scrapenest.models import CreateJobResponse, ScrapeResult
from scrapenest.resources.api_keys import ApiKeysResource
from scrapenest.resources.artifacts import ArtifactsResource
from scrapenest.resources.audit_logs import AuditLogsResource
from scrapenest.resources.jobs import JobsResource
from scrapenest.resources.monitors import MonitorsResource
from scrapenest.resources.org import OrgResource
from scrapenest.resources.retention import RetentionResource
from scrapenest.resources.webhook_endpoints import WebhookEndpointsResource

_DEFAULT_BASE_URL = "https://api.scrapenest.com"
_MAX_BLOCKING_TIMEOUT = 120

T = TypeVar("T")


class ScrapeNestClient:
    """Synchronous ScrapeNest API client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        verify: bool | str = True,
        transport: httpx.BaseTransport | None = None,
        download_transport: httpx.BaseTransport | None = None,
    ) -> None:
        if (api_key is None) == (access_token is None):
            raise ValueError("provide exactly one of api_key or access_token")
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

        auth_header = (
            {"X-API-Key": api_key}
            if api_key is not None
            else {"Authorization": f"Bearer {access_token}"}
        )
        headers = {
            **auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"scrapenest-python/{__version__}",
        }
        self._http = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            verify=verify,
            transport=transport,
        )
        self._download_http = httpx.Client(
            timeout=timeout,
            verify=verify,
            transport=download_transport,
        )

        self.jobs = JobsResource(self)
        self.artifacts = ArtifactsResource(self)
        self.monitors = MonitorsResource(self)
        self.webhook_endpoints = WebhookEndpointsResource(self)
        self.api_keys = ApiKeysResource(self)
        self.retention = RetentionResource(self)
        self.org = OrgResource(self)
        self.audit_logs = AuditLogsResource(self)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        return send_sync(
            self._http,
            method,
            path,
            params=params,
            json=json,
            max_retries=self._max_retries,
            backoff_factor=self._backoff_factor,
        )

    def _execute(self, op: Op[T]) -> T:
        response = self._request(op.method, op.path, params=op.params, json=op.json)
        return op.parse(response)

    def submit(self, **kwargs: Any) -> CreateJobResponse:
        """Submit a job and return immediately; collect the result later.

        Shorthand for `client.jobs.create(...)`. Poll `client.jobs.get(job_id)`
        or use a webhook endpoint to be notified when the job completes.
        """
        return self.jobs.create(**kwargs)

    def scrape(
        self,
        *,
        timeout: int = 30,
        raise_on_failure: bool = True,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Submit a job and block (polling) until it succeeds or fails.

        The job still runs asynchronously server-side; on timeout it keeps
        running and `ScrapeJobTimeout` is raised.
        """
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0 seconds")
        if timeout > _MAX_BLOCKING_TIMEOUT:
            raise ValueError(
                f"timeout cannot exceed {_MAX_BLOCKING_TIMEOUT} seconds; "
                "use submit() and a webhook for longer jobs"
            )

        created = self.jobs.create(**kwargs)
        result = self._await_via_poll(created.job_id, timeout)

        if raise_on_failure and result.status == "failed":
            raise ScrapeJobFailed(job_id=result.job_id, failure_reason=result.failure_reason)

        return result

    def _await_via_poll(self, job_id: str, timeout: int) -> ScrapeResult:
        deadline = time.monotonic() + timeout
        interval = 1.0

        while time.monotonic() < deadline:
            job = self.jobs.get(job_id)
            if job.status in ("succeeded", "failed"):
                return ScrapeResult(
                    job_id=job.job_id,
                    status=job.status,  # type: ignore[arg-type]
                    failure_reason=job.failure_reason,
                    artifact_count=len(job.artifacts),
                    completed_at=job.completed_at or datetime.now(tz=timezone.utc),
                    artifacts=job.artifacts,
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(interval, remaining))
            interval = min(interval * 1.5, 5.0)

        raise ScrapeJobTimeout(job_id=job_id, timeout_seconds=timeout)

    def close(self) -> None:
        self._http.close()
        self._download_http.close()

    def __enter__(self) -> ScrapeNestClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
