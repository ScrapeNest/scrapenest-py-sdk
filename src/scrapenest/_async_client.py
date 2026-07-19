from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, TypeVar

import httpx

from scrapenest._ops import Op
from scrapenest._transport import send_async
from scrapenest._version import __version__
from scrapenest.exceptions import ScrapeJobFailed, ScrapeJobTimeout
from scrapenest.models import CreateJobResponse, ScrapeResult
from scrapenest.resources.api_keys import AsyncApiKeysResource
from scrapenest.resources.artifacts import AsyncArtifactsResource
from scrapenest.resources.audit_logs import AsyncAuditLogsResource
from scrapenest.resources.jobs import AsyncJobsResource
from scrapenest.resources.monitors import AsyncMonitorsResource
from scrapenest.resources.org import AsyncOrgResource
from scrapenest.resources.retention import AsyncRetentionResource
from scrapenest.resources.webhook_endpoints import AsyncWebhookEndpointsResource

_DEFAULT_BASE_URL = "https://api.scrapenest.com"
_MAX_BLOCKING_TIMEOUT = 120

T = TypeVar("T")


class AsyncScrapeNestClient:
    """Asynchronous ScrapeNest API client (httpx.AsyncClient)."""

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
        transport: httpx.AsyncBaseTransport | None = None,
        download_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Customers authenticate with `api_key` (X-API-Key) - the documented,
        # default path. `access_token` (OIDC bearer) is an alternative for
        # first-party clients that already hold a Keycloak token (e.g. the MCP
        # server forwarding the caller's token); exactly one must be given.
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
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            verify=verify,
            transport=transport,
        )
        self._download_http = httpx.AsyncClient(
            timeout=timeout,
            verify=verify,
            transport=download_transport,
        )

        self.jobs = AsyncJobsResource(self)
        self.artifacts = AsyncArtifactsResource(self)
        self.monitors = AsyncMonitorsResource(self)
        self.webhook_endpoints = AsyncWebhookEndpointsResource(self)
        self.api_keys = AsyncApiKeysResource(self)
        self.retention = AsyncRetentionResource(self)
        self.org = AsyncOrgResource(self)
        self.audit_logs = AsyncAuditLogsResource(self)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        return await send_async(
            self._http,
            method,
            path,
            params=params,
            json=json,
            max_retries=self._max_retries,
            backoff_factor=self._backoff_factor,
        )

    async def _execute(self, op: Op[T]) -> T:
        response = await self._request(op.method, op.path, params=op.params, json=op.json)
        return op.parse(response)

    async def submit(self, **kwargs: Any) -> CreateJobResponse:
        """Submit a job and return immediately; collect the result later.

        Shorthand for `client.jobs.create(...)`. Poll `client.jobs.get(job_id)`
        or use a webhook endpoint to be notified when the job completes.
        """
        return await self.jobs.create(**kwargs)

    async def scrape(
        self,
        *,
        timeout: int = 30,
        raise_on_failure: bool = True,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Submit a job and wait (polling) until it succeeds or fails.

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

        created = await self.jobs.create(**kwargs)
        result = await self._await_via_poll(created.job_id, timeout)

        if raise_on_failure and result.status == "failed":
            raise ScrapeJobFailed(job_id=result.job_id, failure_reason=result.failure_reason)

        return result

    async def _await_via_poll(self, job_id: str, timeout: int) -> ScrapeResult:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        interval = 1.0

        while loop.time() < deadline:
            job = await self.jobs.get(job_id)
            if job.status in ("succeeded", "failed"):
                return ScrapeResult(
                    job_id=job.job_id,
                    status=job.status,  # type: ignore[arg-type]
                    failure_reason=job.failure_reason,
                    artifact_count=len(job.artifacts),
                    completed_at=job.completed_at or datetime.now(tz=timezone.utc),
                    artifacts=job.artifacts,
                )

            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            await asyncio.sleep(min(interval, remaining))
            interval = min(interval * 1.5, 5.0)

        raise ScrapeJobTimeout(job_id=job_id, timeout_seconds=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._download_http.aclose()

    async def __aenter__(self) -> AsyncScrapeNestClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
