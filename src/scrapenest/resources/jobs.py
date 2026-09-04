from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, overload

from scrapenest import _ops
from scrapenest._parsing import parse_manifest
from scrapenest.models import (
    CreateJobResponse,
    Job,
    JobListResponse,
    JobManifest,
    JobStatsResponse,
    JobSummary,
)
from scrapenest.types import (
    LightJobCreate,
    StandardJobCreate,
    StealthJobCreate,
    Unpack,
)

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class JobsResource:
    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    @overload
    def create(self, **kwargs: Unpack[LightJobCreate]) -> CreateJobResponse: ...
    @overload
    def create(self, **kwargs: Unpack[StandardJobCreate]) -> CreateJobResponse: ...
    @overload
    def create(self, **kwargs: Unpack[StealthJobCreate]) -> CreateJobResponse: ...

    def create(self, **kwargs: Any) -> CreateJobResponse:
        return self._client._execute(_ops.create_job(kwargs))

    def get(
        self,
        job_id: str,
        *,
        include_download_urls: bool | None = None,
        ttl_seconds: int | None = None,
    ) -> Job:
        return self._client._execute(_ops.get_job(job_id, include_download_urls, ttl_seconds))

    def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        job_id: str | None = None,
        target_url: str | None = None,
        tag: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> JobListResponse:
        return self._client._execute(
            _ops.list_jobs(
                status=status,
                job_type=job_type,
                job_id=job_id,
                target_url=target_url,
                tag=tag,
                from_=from_,
                to=to,
                limit=limit,
                offset=offset,
            )
        )

    def stats(
        self,
        *,
        from_: str | None = None,
        to: str | None = None,
        job_type: str | None = None,
    ) -> JobStatsResponse:
        return self._client._execute(
            _ops.get_job_stats(from_=from_, to=to, job_type=job_type)
        )

    def iter(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        target_url: str | None = None,
        tag: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        page_size: int = 50,
    ) -> Iterator[JobSummary]:
        """Yield every matching job, transparently walking limit/offset pages."""
        offset = 0
        while True:
            page = self.list(
                status=status,
                job_type=job_type,
                target_url=target_url,
                tag=tag,
                from_=from_,
                to=to,
                limit=page_size,
                offset=offset,
            )
            yield from page.items
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    def get_manifest(self, job_id: str) -> JobManifest | None:
        """Download and parse the job's forensics manifest (outcome, credits, block).

        Returns None when the job has no manifest artifact yet (still running).
        """
        job = self.get(job_id, include_download_urls=True)
        manifest = next((a for a in job.artifacts if a.artifact_type == "manifest"), None)
        if manifest is None:
            return None
        content = self._client.artifacts.download_bytes(manifest.artifact_id)
        return parse_manifest(json.loads(content))


class AsyncJobsResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    @overload
    async def create(self, **kwargs: Unpack[LightJobCreate]) -> CreateJobResponse: ...
    @overload
    async def create(self, **kwargs: Unpack[StandardJobCreate]) -> CreateJobResponse: ...
    @overload
    async def create(self, **kwargs: Unpack[StealthJobCreate]) -> CreateJobResponse: ...

    async def create(self, **kwargs: Any) -> CreateJobResponse:
        return await self._client._execute(_ops.create_job(kwargs))

    async def get(
        self,
        job_id: str,
        *,
        include_download_urls: bool | None = None,
        ttl_seconds: int | None = None,
    ) -> Job:
        return await self._client._execute(
            _ops.get_job(job_id, include_download_urls, ttl_seconds)
        )

    async def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        job_id: str | None = None,
        target_url: str | None = None,
        tag: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> JobListResponse:
        return await self._client._execute(
            _ops.list_jobs(
                status=status,
                job_type=job_type,
                job_id=job_id,
                target_url=target_url,
                tag=tag,
                from_=from_,
                to=to,
                limit=limit,
                offset=offset,
            )
        )

    async def stats(
        self,
        *,
        from_: str | None = None,
        to: str | None = None,
        job_type: str | None = None,
    ) -> JobStatsResponse:
        return await self._client._execute(
            _ops.get_job_stats(from_=from_, to=to, job_type=job_type)
        )

    async def iter(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        target_url: str | None = None,
        tag: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        page_size: int = 50,
    ) -> AsyncIterator[JobSummary]:
        offset = 0
        while True:
            page = await self.list(
                status=status,
                job_type=job_type,
                target_url=target_url,
                tag=tag,
                from_=from_,
                to=to,
                limit=page_size,
                offset=offset,
            )
            for item in page.items:
                yield item
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    async def get_manifest(self, job_id: str) -> JobManifest | None:
        job = await self.get(job_id, include_download_urls=True)
        manifest = next((a for a in job.artifacts if a.artifact_type == "manifest"), None)
        if manifest is None:
            return None
        content = await self._client.artifacts.download_bytes(manifest.artifact_id)
        return parse_manifest(json.loads(content))
