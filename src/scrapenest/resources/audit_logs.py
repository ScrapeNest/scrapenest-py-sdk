from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

from scrapenest import _ops
from scrapenest.models import AuditLogEntry, AuditLogListResponse

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class AuditLogsResource:
    """Read the organization audit trail.

    Requires a key with the `audit_logs.read` scope.
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def list(
        self,
        *,
        severity: str | None = None,
        result: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> AuditLogListResponse:
        """List audit log entries, newest first.

        Filter by `severity` (e.g. low, medium, high, critical), `result`
        (e.g. success, failure, error), or `event_type`.
        """
        return self._client._execute(
            _ops.list_audit_logs(severity, result, event_type, limit, offset)
        )

    def iter(
        self,
        *,
        severity: str | None = None,
        result: str | None = None,
        event_type: str | None = None,
        page_size: int = 50,
    ) -> Iterator[AuditLogEntry]:
        """Iterate over every matching audit log entry, paging transparently."""
        offset = 0
        while True:
            page = self.list(
                severity=severity,
                result=result,
                event_type=event_type,
                limit=page_size,
                offset=offset,
            )
            yield from page.items
            offset += len(page.items)
            if not page.items or offset >= page.total:
                return


class AsyncAuditLogsResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def list(
        self,
        *,
        severity: str | None = None,
        result: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> AuditLogListResponse:
        return await self._client._execute(
            _ops.list_audit_logs(severity, result, event_type, limit, offset)
        )

    async def iter(
        self,
        *,
        severity: str | None = None,
        result: str | None = None,
        event_type: str | None = None,
        page_size: int = 50,
    ) -> AsyncIterator[AuditLogEntry]:
        offset = 0
        while True:
            page = await self.list(
                severity=severity,
                result=result,
                event_type=event_type,
                limit=page_size,
                offset=offset,
            )
            for item in page.items:
                yield item
            offset += len(page.items)
            if not page.items or offset >= page.total:
                return
