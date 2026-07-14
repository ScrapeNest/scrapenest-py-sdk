from __future__ import annotations

from typing import TYPE_CHECKING

from scrapenest import _ops
from scrapenest.models import ArtifactDownload

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class ArtifactsResource:
    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def get_download_url(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> ArtifactDownload:
        return self._client._execute(_ops.get_artifact_download(artifact_id, ttl_seconds))

    def download_bytes(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> bytes:
        download = self.get_download_url(artifact_id, ttl_seconds=ttl_seconds)
        response = self._client._download_http.get(download.download_url)
        response.raise_for_status()
        return response.content

    def download_text(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
        encoding: str | None = None,
    ) -> str:
        content = self.download_bytes(artifact_id, ttl_seconds=ttl_seconds)
        return content.decode(encoding or "utf-8")


class AsyncArtifactsResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def get_download_url(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> ArtifactDownload:
        return await self._client._execute(_ops.get_artifact_download(artifact_id, ttl_seconds))

    async def download_bytes(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> bytes:
        download = await self.get_download_url(artifact_id, ttl_seconds=ttl_seconds)
        response = await self._client._download_http.get(download.download_url)
        response.raise_for_status()
        return response.content

    async def download_text(
        self,
        artifact_id: str,
        *,
        ttl_seconds: int | None = None,
        encoding: str | None = None,
    ) -> str:
        content = await self.download_bytes(artifact_id, ttl_seconds=ttl_seconds)
        return content.decode(encoding or "utf-8")
