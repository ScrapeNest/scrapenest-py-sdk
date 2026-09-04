from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any

from scrapenest import _ops
from scrapenest.models import (
    Monitor,
    MonitorChange,
    MonitorChangeDiff,
    MonitorChangeListResponse,
    MonitorListResponse,
    MonitorRun,
    MonitorRunListResponse,
)

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class MonitorsResource:
    """Manage recurring job monitors (cron-based scrapes)."""

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def create(
        self,
        *,
        name: str,
        cron: str,
        job_type: str,
        target_url: str,
        timezone: str | None = None,
        overlap_policy: str | None = None,
        payload: dict[str, Any] | None = None,
        detection: dict[str, Any] | None = None,
    ) -> Monitor:
        """Create a recurring monitor.

        Pass ``detection`` to enable change detection, e.g.
        ``detection={"enabled": True, "mode": "selector", "selector": ".price",
        "notify": {"email": ["alerts@acme.eu"]}}``.
        """
        return self._client._execute(
            _ops.create_monitor(
                name, cron, job_type, target_url, timezone, overlap_policy, payload, detection
            )
        )

    def get(self, monitor_id: str) -> Monitor:
        return self._client._execute(_ops.get_monitor(monitor_id))

    def list(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorListResponse:
        return self._client._execute(_ops.list_monitors(status, limit, offset))

    def iter(self, *, status: str | None = None, page_size: int = 50) -> Iterator[Monitor]:
        offset = 0
        while True:
            page = self.list(status=status, limit=page_size, offset=offset)
            yield from page.items
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    def update(
        self,
        monitor_id: str,
        *,
        name: str,
        cron: str,
        job_type: str,
        target_url: str,
        timezone: str | None = None,
        overlap_policy: str | None = None,
        payload: dict[str, Any] | None = None,
        detection: dict[str, Any] | None = None,
    ) -> Monitor:
        """Replace the monitor. The API requires the full definition on update,
        so pass every field you want to keep, not just the changed ones.

        Omit ``detection`` to leave change detection unchanged; pass
        ``detection={"enabled": False}`` to turn it off.
        """
        return self._client._execute(
            _ops.update_monitor(
                monitor_id, name, cron, job_type, target_url, timezone, overlap_policy, payload, detection
            )
        )

    def pause(self, monitor_id: str) -> Monitor:
        return self._client._execute(_ops.pause_monitor(monitor_id))

    def resume(self, monitor_id: str) -> Monitor:
        return self._client._execute(_ops.resume_monitor(monitor_id))

    def delete(self, monitor_id: str) -> None:
        self._client._execute(_ops.delete_monitor(monitor_id))

    def runs(
        self,
        monitor_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorRunListResponse:
        return self._client._execute(_ops.list_monitor_runs(monitor_id, limit, offset))

    def iter_runs(self, monitor_id: str, *, page_size: int = 50) -> Iterator[MonitorRun]:
        offset = 0
        while True:
            page = self.runs(monitor_id, limit=page_size, offset=offset)
            yield from page.items
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    def changes(
        self,
        monitor_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorChangeListResponse:
        """List detected changes for a monitor, newest first."""
        return self._client._execute(_ops.list_monitor_changes(monitor_id, limit, offset))

    def iter_changes(self, monitor_id: str, *, page_size: int = 50) -> Iterator[MonitorChange]:
        offset = 0
        while True:
            page = self.changes(monitor_id, limit=page_size, offset=offset)
            yield from page.items
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    def change_diff(self, monitor_id: str, change_id: str) -> MonitorChangeDiff:
        return self._client._execute(
            _ops.get_monitor_change_diff(monitor_id, change_id)
        )


class AsyncMonitorsResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def create(
        self,
        *,
        name: str,
        cron: str,
        job_type: str,
        target_url: str,
        timezone: str | None = None,
        overlap_policy: str | None = None,
        payload: dict[str, Any] | None = None,
        detection: dict[str, Any] | None = None,
    ) -> Monitor:
        return await self._client._execute(
            _ops.create_monitor(
                name, cron, job_type, target_url, timezone, overlap_policy, payload, detection
            )
        )

    async def get(self, monitor_id: str) -> Monitor:
        return await self._client._execute(_ops.get_monitor(monitor_id))

    async def list(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorListResponse:
        return await self._client._execute(_ops.list_monitors(status, limit, offset))

    async def iter(
        self, *, status: str | None = None, page_size: int = 50
    ) -> AsyncIterator[Monitor]:
        offset = 0
        while True:
            page = await self.list(status=status, limit=page_size, offset=offset)
            for item in page.items:
                yield item
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    async def update(
        self,
        monitor_id: str,
        *,
        name: str,
        cron: str,
        job_type: str,
        target_url: str,
        timezone: str | None = None,
        overlap_policy: str | None = None,
        payload: dict[str, Any] | None = None,
        detection: dict[str, Any] | None = None,
    ) -> Monitor:
        return await self._client._execute(
            _ops.update_monitor(
                monitor_id, name, cron, job_type, target_url, timezone, overlap_policy, payload, detection
            )
        )

    async def pause(self, monitor_id: str) -> Monitor:
        return await self._client._execute(_ops.pause_monitor(monitor_id))

    async def resume(self, monitor_id: str) -> Monitor:
        return await self._client._execute(_ops.resume_monitor(monitor_id))

    async def delete(self, monitor_id: str) -> None:
        await self._client._execute(_ops.delete_monitor(monitor_id))

    async def runs(
        self,
        monitor_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorRunListResponse:
        return await self._client._execute(_ops.list_monitor_runs(monitor_id, limit, offset))

    async def iter_runs(self, monitor_id: str, *, page_size: int = 50) -> AsyncIterator[MonitorRun]:
        offset = 0
        while True:
            page = await self.runs(monitor_id, limit=page_size, offset=offset)
            for item in page.items:
                yield item
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    async def changes(
        self,
        monitor_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> MonitorChangeListResponse:
        return await self._client._execute(_ops.list_monitor_changes(monitor_id, limit, offset))

    async def iter_changes(
        self, monitor_id: str, *, page_size: int = 50
    ) -> AsyncIterator[MonitorChange]:
        offset = 0
        while True:
            page = await self.changes(monitor_id, limit=page_size, offset=offset)
            for item in page.items:
                yield item
            offset += len(page.items)
            if not page.items or offset >= page.total:
                break

    async def change_diff(self, monitor_id: str, change_id: str) -> MonitorChangeDiff:
        return await self._client._execute(
            _ops.get_monitor_change_diff(monitor_id, change_id)
        )
