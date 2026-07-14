from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from scrapenest import _ops
from scrapenest.models import (
    ApiKey,
    ApiKeyCreated,
    ApiKeyIpAllowlist,
    ApiKeyRevocation,
    ApiKeyRotation,
)

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class ApiKeysResource:
    """Manage the organization's API keys.

    Requires a key with the `api_keys.manage` scope. Tokens are returned in
    plaintext exactly once (on create and rotate) - store them immediately.
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def list(self) -> list[ApiKey]:
        return self._client._execute(_ops.list_api_keys())

    def create(
        self,
        *,
        name: str,
        scopes: Sequence[str],
        description: str | None = None,
        expires_at: str | None = None,
        allowed_cidrs: Sequence[str] | None = None,
        rate_limit_rpm: int | None = None,
        daily_quota: int | None = None,
        max_concurrent_jobs: int | None = None,
        enforcement_mode: str | None = None,
    ) -> ApiKeyCreated:
        return self._client._execute(
            _ops.create_api_key(
                name=name,
                scopes=list(scopes),
                description=description,
                expires_at=expires_at,
                allowed_cidrs=list(allowed_cidrs) if allowed_cidrs is not None else None,
                rate_limit_rpm=rate_limit_rpm,
                daily_quota=daily_quota,
                max_concurrent_jobs=max_concurrent_jobs,
                enforcement_mode=enforcement_mode,
            )
        )

    def rotate(self, key_id: str) -> ApiKeyRotation:
        """Issue a new token for the key. The old token stops working immediately."""
        return self._client._execute(_ops.rotate_api_key(key_id))

    def revoke(self, key_id: str, *, reason: str | None = None) -> ApiKeyRevocation:
        return self._client._execute(_ops.revoke_api_key(key_id, reason))

    def set_ip_allowlist(self, key_id: str, allowed_cidrs: Sequence[str]) -> ApiKeyIpAllowlist:
        """Replace the key's IP allowlist. An empty list clears the key-level restriction."""
        return self._client._execute(_ops.set_api_key_ip_allowlist(key_id, list(allowed_cidrs)))


class AsyncApiKeysResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def list(self) -> list[ApiKey]:
        return await self._client._execute(_ops.list_api_keys())

    async def create(
        self,
        *,
        name: str,
        scopes: Sequence[str],
        description: str | None = None,
        expires_at: str | None = None,
        allowed_cidrs: Sequence[str] | None = None,
        rate_limit_rpm: int | None = None,
        daily_quota: int | None = None,
        max_concurrent_jobs: int | None = None,
        enforcement_mode: str | None = None,
    ) -> ApiKeyCreated:
        return await self._client._execute(
            _ops.create_api_key(
                name=name,
                scopes=list(scopes),
                description=description,
                expires_at=expires_at,
                allowed_cidrs=list(allowed_cidrs) if allowed_cidrs is not None else None,
                rate_limit_rpm=rate_limit_rpm,
                daily_quota=daily_quota,
                max_concurrent_jobs=max_concurrent_jobs,
                enforcement_mode=enforcement_mode,
            )
        )

    async def rotate(self, key_id: str) -> ApiKeyRotation:
        return await self._client._execute(_ops.rotate_api_key(key_id))

    async def revoke(self, key_id: str, *, reason: str | None = None) -> ApiKeyRevocation:
        return await self._client._execute(_ops.revoke_api_key(key_id, reason))

    async def set_ip_allowlist(self, key_id: str, allowed_cidrs: Sequence[str]) -> ApiKeyIpAllowlist:
        return await self._client._execute(_ops.set_api_key_ip_allowlist(key_id, list(allowed_cidrs)))
