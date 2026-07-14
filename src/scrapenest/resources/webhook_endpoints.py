from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any

from scrapenest import _ops
from scrapenest.models import (
    WebhookEndpoint,
    WebhookEndpointCreated,
    WebhookEndpointStatusChange,
    WebhookEndpointUpdated,
    WebhookMessage,
    WebhookMessageAttemptPage,
    WebhookMessagePage,
    WebhookSecretRotation,
)

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


class WebhookEndpointsResource:
    """Manage webhook endpoints and inspect deliveries.

    Requires a key with the `webhooks.manage` scope. Endpoint URLs must be
    HTTPS; every endpoint receives all event types. Verify incoming deliveries
    with `scrapenest.verify_webhook` before trusting them.
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def list(self) -> list[WebhookEndpoint]:
        return self._client._execute(_ops.list_webhook_endpoints())

    def create(
        self,
        *,
        name: str,
        url: str,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> WebhookEndpointCreated:
        """Create an endpoint. The response carries the signing secret, shown once only."""
        return self._client._execute(
            _ops.create_webhook_endpoint(name, url, description, metadata, retry_config)
        )

    def update(
        self,
        endpoint_id: str,
        *,
        name: str,
        url: str,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> WebhookEndpointUpdated:
        """Replace the endpoint configuration. Omitted nullable fields are cleared."""
        return self._client._execute(
            _ops.update_webhook_endpoint(endpoint_id, name, url, description, metadata, retry_config)
        )

    def delete(self, endpoint_id: str) -> None:
        self._client._execute(_ops.delete_webhook_endpoint(endpoint_id))

    def rotate_secret(self, endpoint_id: str) -> WebhookSecretRotation:
        """Issue a new signing secret. The old secret stops validating immediately."""
        return self._client._execute(_ops.rotate_webhook_secret(endpoint_id))

    def pause(self, endpoint_id: str) -> WebhookEndpointStatusChange:
        return self._client._execute(_ops.pause_webhook_endpoint(endpoint_id))

    def resume(self, endpoint_id: str) -> WebhookEndpointStatusChange:
        return self._client._execute(_ops.resume_webhook_endpoint(endpoint_id))

    def messages(
        self,
        endpoint_id: str,
        *,
        limit: int | None = None,
        iterator: str | None = None,
    ) -> WebhookMessagePage:
        """One page of recent deliveries. Pass `page.iterator` back for the next page."""
        return self._client._execute(_ops.list_webhook_messages(endpoint_id, limit, iterator))

    def iter_messages(self, endpoint_id: str, *, page_size: int = 50) -> Iterator[WebhookMessage]:
        """Yield every delivery, transparently walking the cursor pages."""
        iterator: str | None = None
        while True:
            page = self.messages(endpoint_id, limit=page_size, iterator=iterator)
            yield from page.items
            if page.done or page.iterator is None:
                break
            iterator = page.iterator

    def attempts(
        self,
        endpoint_id: str,
        message_id: str,
        *,
        limit: int | None = None,
        iterator: str | None = None,
    ) -> WebhookMessageAttemptPage:
        """Delivery attempts for one message (status codes, latency, response bodies)."""
        return self._client._execute(
            _ops.list_webhook_attempts(endpoint_id, message_id, limit, iterator)
        )


class AsyncWebhookEndpointsResource:
    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def list(self) -> list[WebhookEndpoint]:
        return await self._client._execute(_ops.list_webhook_endpoints())

    async def create(
        self,
        *,
        name: str,
        url: str,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> WebhookEndpointCreated:
        return await self._client._execute(
            _ops.create_webhook_endpoint(name, url, description, metadata, retry_config)
        )

    async def update(
        self,
        endpoint_id: str,
        *,
        name: str,
        url: str,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> WebhookEndpointUpdated:
        return await self._client._execute(
            _ops.update_webhook_endpoint(endpoint_id, name, url, description, metadata, retry_config)
        )

    async def delete(self, endpoint_id: str) -> None:
        await self._client._execute(_ops.delete_webhook_endpoint(endpoint_id))

    async def rotate_secret(self, endpoint_id: str) -> WebhookSecretRotation:
        return await self._client._execute(_ops.rotate_webhook_secret(endpoint_id))

    async def pause(self, endpoint_id: str) -> WebhookEndpointStatusChange:
        return await self._client._execute(_ops.pause_webhook_endpoint(endpoint_id))

    async def resume(self, endpoint_id: str) -> WebhookEndpointStatusChange:
        return await self._client._execute(_ops.resume_webhook_endpoint(endpoint_id))

    async def messages(
        self,
        endpoint_id: str,
        *,
        limit: int | None = None,
        iterator: str | None = None,
    ) -> WebhookMessagePage:
        return await self._client._execute(_ops.list_webhook_messages(endpoint_id, limit, iterator))

    async def iter_messages(
        self, endpoint_id: str, *, page_size: int = 50
    ) -> AsyncIterator[WebhookMessage]:
        iterator: str | None = None
        while True:
            page = await self.messages(endpoint_id, limit=page_size, iterator=iterator)
            for item in page.items:
                yield item
            if page.done or page.iterator is None:
                break
            iterator = page.iterator

    async def attempts(
        self,
        endpoint_id: str,
        message_id: str,
        *,
        limit: int | None = None,
        iterator: str | None = None,
    ) -> WebhookMessageAttemptPage:
        return await self._client._execute(
            _ops.list_webhook_attempts(endpoint_id, message_id, limit, iterator)
        )
