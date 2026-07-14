from __future__ import annotations

from typing import TYPE_CHECKING

from scrapenest import _ops
from scrapenest.models import OrgIpAllowlist

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class OrgResource:
    """Organization-wide security settings.

    Requires a key with the `org.manage` scope.
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def get_ip_allowlist(self) -> OrgIpAllowlist:
        return self._client._execute(_ops.get_org_ip_allowlist())

    def set_ip_allowlist(self, allowed_cidrs: list[str]) -> OrgIpAllowlist:
        """Replace the org IP allowlist. An empty list removes the restriction.

        The effective allowlist for a key is this list intersected with any
        non-empty key-level allowlist. Take care not to lock yourself out.
        """
        return self._client._execute(_ops.set_org_ip_allowlist(allowed_cidrs))


class AsyncOrgResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def get_ip_allowlist(self) -> OrgIpAllowlist:
        return await self._client._execute(_ops.get_org_ip_allowlist())

    async def set_ip_allowlist(self, allowed_cidrs: list[str]) -> OrgIpAllowlist:
        return await self._client._execute(_ops.set_org_ip_allowlist(allowed_cidrs))
