from __future__ import annotations

import json

import httpx

from conftest import async_client, sync_client

ENDPOINT_ID = "f6d9a1f0-0000-4000-8000-000000000002"

ENDPOINT_SUMMARY = {
    "endpoint_id": ENDPOINT_ID,
    "name": "prod-receiver",
    "description": None,
    "url": "https://hooks.example.com/scrapenest",
    "status": "active",
    "secret_prefix": "whsec_a1b2",
    "metadata": {"env": "prod"},
    "retry_config": {"max_attempts": 5},
    "dispatcher_endpoint_id": "ep_123",
    "consecutive_failures": 0,
    "last_health_status": "healthy",
    "last_health_checked_at": "2026-06-07T13:50:00+00:00",
    "created_at": "2026-05-01T09:00:00+00:00",
    "updated_at": "2026-06-01T09:00:00+00:00",
}


def test_create_returns_secret_once() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            201,
            json={
                "endpoint_id": ENDPOINT_ID,
                "name": "prod-receiver",
                "description": None,
                "url": "https://hooks.example.com/scrapenest",
                "status": "active",
                "secret": "whsec_a1b2c3d4e5",
                "secret_prefix": "whsec_a1b2",
                "metadata": None,
                "retry_config": None,
                "dispatcher_endpoint_id": "ep_123",
                "created_at": "2026-06-07T14:00:00+00:00",
                "updated_at": "2026-06-07T14:00:00+00:00",
            },
        )

    client = sync_client(handler)
    created = client.webhook_endpoints.create(
        name="prod-receiver",
        url="https://hooks.example.com/scrapenest",
    )

    assert json.loads(seen[0].content) == {
        "name": "prod-receiver",
        "url": "https://hooks.example.com/scrapenest",
    }
    assert created.secret == "whsec_a1b2c3d4e5"
    assert created.status == "active"


def test_list_update_and_lifecycle_routes() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json={"items": [ENDPOINT_SUMMARY]})
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.url.path.endswith("/rotate-secret"):
            return httpx.Response(
                200,
                json={
                    "endpoint_id": ENDPOINT_ID,
                    "secret": "whsec_new",
                    "secret_prefix": "whsec_new1",
                    "rotated_at": "2026-06-07T14:10:00+00:00",
                },
            )
        if request.url.path.endswith("/pause"):
            return httpx.Response(
                200,
                json={
                    "endpoint_id": ENDPOINT_ID,
                    "status": "paused",
                    "paused_at": "2026-06-07T14:11:00+00:00",
                },
            )
        if request.url.path.endswith("/resume"):
            return httpx.Response(
                200,
                json={
                    "endpoint_id": ENDPOINT_ID,
                    "status": "active",
                    "resumed_at": "2026-06-07T14:12:00+00:00",
                },
            )
        return httpx.Response(
            200,
            json={
                "endpoint_id": ENDPOINT_ID,
                "name": "prod-receiver-v2",
                "description": "renamed",
                "url": "https://hooks.example.com/v2",
                "status": "active",
                "metadata": None,
                "retry_config": None,
                "updated_at": "2026-06-07T14:09:00+00:00",
            },
        )

    client = sync_client(handler)

    endpoints = client.webhook_endpoints.list()
    assert endpoints[0].metadata == {"env": "prod"}
    assert endpoints[0].last_health_status == "healthy"

    updated = client.webhook_endpoints.update(
        ENDPOINT_ID, name="prod-receiver-v2", url="https://hooks.example.com/v2"
    )
    assert updated.name == "prod-receiver-v2"

    rotation = client.webhook_endpoints.rotate_secret(ENDPOINT_ID)
    assert rotation.secret == "whsec_new"

    paused = client.webhook_endpoints.pause(ENDPOINT_ID)
    assert paused.status == "paused"
    assert paused.changed_at is not None

    resumed = client.webhook_endpoints.resume(ENDPOINT_ID)
    assert resumed.status == "active"

    client.webhook_endpoints.delete(ENDPOINT_ID)

    assert [m for m, _ in seen] == ["GET", "PUT", "POST", "POST", "POST", "DELETE"]


def _message(i: int) -> dict[str, object]:
    return {
        "message_id": f"msg-{i}",
        "event_type": "job.completed",
        "event_id": f"evt-{i}",
        "status": "delivered",
        "payload": {"job_id": f"job-{i}"},
        "dispatched_at": "2026-06-07T14:00:00+00:00",
    }


def test_iter_messages_walks_cursor_pages() -> None:
    iterators: list[str | None] = []
    pages = [
        {
            "endpoint_id": ENDPOINT_ID,
            "items": [_message(1), _message(2)],
            "iterator": "cursor-2",
            "prev_iterator": None,
            "done": False,
            "limit": 2,
        },
        {
            "endpoint_id": ENDPOINT_ID,
            "items": [_message(3)],
            "iterator": None,
            "prev_iterator": "cursor-2",
            "done": True,
            "limit": 2,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        iterators.append(request.url.params.get("iterator"))
        return httpx.Response(200, json=pages.pop(0))

    client = sync_client(handler)
    messages = list(client.webhook_endpoints.iter_messages(ENDPOINT_ID, page_size=2))

    assert [m.message_id for m in messages] == ["msg-1", "msg-2", "msg-3"]
    assert iterators == [None, "cursor-2"]


def test_attempts_expose_delivery_forensics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == (
            f"/v1/webhook-endpoints/{ENDPOINT_ID}/messages/msg-1/attempts"
        )
        return httpx.Response(
            200,
            json={
                "endpoint_id": ENDPOINT_ID,
                "message_id": "msg-1",
                "items": [
                    {
                        "id": "atmpt-1",
                        "status": "failed",
                        "status_code": 500,
                        "latency_ms": 1200,
                        "response_body": "internal error",
                        "dispatched_at": "2026-06-07T14:00:00+00:00",
                    },
                    {
                        "id": "atmpt-2",
                        "status": "delivered",
                        "status_code": 200,
                        "latency_ms": 45,
                        "response_body": "",
                        "dispatched_at": "2026-06-07T14:01:00+00:00",
                    },
                ],
                "iterator": None,
                "prev_iterator": None,
                "done": True,
                "limit": 50,
            },
        )

    client = sync_client(handler)
    page = client.webhook_endpoints.attempts(ENDPOINT_ID, "msg-1")

    assert page.items[0].status_code == 500
    assert page.items[1].latency_ms == 45
    assert page.done is True


async def test_async_iter_messages_walks_cursor_pages() -> None:
    pages = [
        {
            "endpoint_id": ENDPOINT_ID,
            "items": [_message(1)],
            "iterator": "cursor-1",
            "prev_iterator": None,
            "done": False,
            "limit": 1,
        },
        {
            "endpoint_id": ENDPOINT_ID,
            "items": [_message(2)],
            "iterator": None,
            "prev_iterator": "cursor-1",
            "done": True,
            "limit": 1,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages.pop(0))

    async with async_client(handler) as client:
        seen = [m.message_id async for m in client.webhook_endpoints.iter_messages(ENDPOINT_ID)]
        assert seen == ["msg-1", "msg-2"]
