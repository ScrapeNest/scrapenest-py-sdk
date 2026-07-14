"""Register a webhook endpoint and debug its deliveries.

Instead of polling job status, register an HTTPS endpoint once and let
ScrapeNest push job events to it. This example creates an endpoint, shows how
to inspect what was delivered (and why a delivery failed), then cleans up.

Pair it with `webhook_receiver.py`, which implements the receiving side.

Run: SCRAPENEST_API_KEY=sn_live_... python examples/09_webhook_endpoints.py
"""

from _common import make_client

# Replace with your own receiver. The URL must be HTTPS and its host must
# resolve to a public IP - the API rejects unresolvable or private hosts.
RECEIVER_URL = "https://example.com/webhooks/scrapenest"


def main() -> None:
    client = make_client()

    # The signing secret is returned exactly once, at creation time. Store it
    # in your secret manager; the receiver needs it to verify signatures.
    endpoint = client.webhook_endpoints.create(
        name="example-receiver",
        url=RECEIVER_URL,
        description="Created by the SDK examples",
        metadata={"env": "example"},
        # Optional: tune delivery retries (platform defaults are sensible).
        retry_config={"max_attempts": 5, "timeout_seconds": 15},
    )
    print(f"endpoint {endpoint.endpoint_id} -> {endpoint.url}")
    print(f"signing secret (store it now, shown once): {endpoint.secret[:12]}...")

    # Recent deliveries to this endpoint, newest first. Each message is one
    # event (job.completed, ...) with its current delivery status.
    for message in client.webhook_endpoints.iter_messages(endpoint.endpoint_id, page_size=20):
        print(f"  {message.event_type} {message.status} at {message.dispatched_at}")

        # When a delivery fails, the attempts show your endpoint's responses.
        if message.status == "failed":
            attempts = client.webhook_endpoints.attempts(endpoint.endpoint_id, message.message_id)
            for attempt in attempts.items:
                print(f"    attempt: HTTP {attempt.status_code} in {attempt.latency_ms}ms")

    # Rotating the secret invalidates the old one immediately - update the
    # receiver first, then rotate.
    rotation = client.webhook_endpoints.rotate_secret(endpoint.endpoint_id)
    print(f"rotated secret, new prefix {rotation.secret_prefix}")

    # Pause while your receiver is down for maintenance; resume when back.
    client.webhook_endpoints.pause(endpoint.endpoint_id)
    client.webhook_endpoints.resume(endpoint.endpoint_id)

    client.webhook_endpoints.delete(endpoint.endpoint_id)
    print("deleted endpoint")


if __name__ == "__main__":
    main()
