from __future__ import annotations

from typing import TYPE_CHECKING

from scrapenest import _ops
from scrapenest.models import (
    RetentionHold,
    RetentionHoldList,
    RetentionHoldRelease,
    RetentionPolicy,
)

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class RetentionResource:
    """Artifact retention policy and legal holds.

    Requires a key with the `retention.manage` scope. Artifacts under an
    active hold are exempt from retention purges until the hold is released.
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def get_policy(self) -> RetentionPolicy:
        return self._client._execute(_ops.get_retention_policy())

    def update_policy(self, *, retention_days: int, legal_hold_enabled: bool) -> RetentionPolicy:
        """Replace the retention policy.

        `retention_days` may not exceed the policy's `max_retention_days`;
        shortening retention below an active legal hold is rejected with a 409.
        """
        return self._client._execute(
            _ops.update_retention_policy(retention_days, legal_hold_enabled)
        )

    def list_holds(self) -> RetentionHoldList:
        return self._client._execute(_ops.list_retention_holds())

    def create_hold(
        self,
        *,
        scope_type: str,
        justification: str,
        scope_ref: str | None = None,
        expires_at: str | None = None,
    ) -> RetentionHold:
        """Place a hold on the org, a job, or an artifact.

        `scope_ref` is the job/artifact id and is required unless scope_type
        is "org". `expires_at` auto-releases the hold; omit it to hold until
        explicitly released.
        """
        return self._client._execute(
            _ops.create_retention_hold(scope_type, justification, scope_ref, expires_at)
        )

    def release_hold(self, hold_id: str, *, release_notes: str) -> RetentionHoldRelease:
        return self._client._execute(_ops.release_retention_hold(hold_id, release_notes))


class AsyncRetentionResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def get_policy(self) -> RetentionPolicy:
        return await self._client._execute(_ops.get_retention_policy())

    async def update_policy(
        self, *, retention_days: int, legal_hold_enabled: bool
    ) -> RetentionPolicy:
        return await self._client._execute(
            _ops.update_retention_policy(retention_days, legal_hold_enabled)
        )

    async def list_holds(self) -> RetentionHoldList:
        return await self._client._execute(_ops.list_retention_holds())

    async def create_hold(
        self,
        *,
        scope_type: str,
        justification: str,
        scope_ref: str | None = None,
        expires_at: str | None = None,
    ) -> RetentionHold:
        return await self._client._execute(
            _ops.create_retention_hold(scope_type, justification, scope_ref, expires_at)
        )

    async def release_hold(self, hold_id: str, *, release_notes: str) -> RetentionHoldRelease:
        return await self._client._execute(_ops.release_retention_hold(hold_id, release_notes))
