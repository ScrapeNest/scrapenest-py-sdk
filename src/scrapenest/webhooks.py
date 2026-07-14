"""Webhook signature verification.

ScrapeNest signs every webhook delivery with the Svix scheme. Each POST carries
``svix-id``, ``svix-timestamp`` and ``svix-signature`` headers. The signature is
``v1,<base64>`` where ``<base64>`` is the HMAC-SHA256 of
``"<svix-id>.<svix-timestamp>.<raw_body>"`` keyed by the endpoint secret. Verify
the signature *before* trusting a payload, and reject deliveries whose timestamp
is outside the tolerance window (default 5 minutes) to defeat replays.

    from scrapenest import verify_webhook

    @app.post("/webhooks/scrapenest")
    async def receive(request):
        event = verify_webhook(await request.body(), request.headers, secret)
        ...
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any

from scrapenest.exceptions import WebhookVerificationError

DEFAULT_TOLERANCE_SECONDS = 300


def _header(headers: Mapping[str, str], name: str) -> str | None:
    # httpx.Headers is already case-insensitive; fall back to a manual scan for plain dicts.
    value = headers.get(name)
    if value is not None:
        return value
    lowered = name.lower()
    for key, val in headers.items():
        if key.lower() == lowered:
            return val
    return None


def _extract_signatures(signature_header: str) -> list[str]:
    """Pull candidate base64 signatures out of a (possibly multi-value) header."""
    signatures: list[str] = []
    for token in signature_header.split():
        candidate = token
        for sep in (",", "=", ":"):
            if candidate.startswith("v1" + sep):
                candidate = candidate[len("v1" + sep):]
                break
        if candidate:
            signatures.append(candidate)
    return signatures


def verify_signature(
    payload: str | bytes,
    headers: Mapping[str, str],
    secret: str,
    *,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> None:
    """Verify a webhook signature, raising ``WebhookVerificationError`` on failure."""
    body = payload.encode("utf-8") if isinstance(payload, str) else payload

    svix_id = _header(headers, "svix-id")
    timestamp = _header(headers, "svix-timestamp")
    signature_header = _header(headers, "svix-signature")
    if not svix_id or not timestamp or not signature_header:
        raise WebhookVerificationError("Missing svix-id, svix-timestamp, or svix-signature header.")

    if not timestamp.isdigit():
        raise WebhookVerificationError("Invalid svix-timestamp header.")
    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        raise WebhookVerificationError("Webhook timestamp is outside the tolerance window.")

    signed_content = f"{svix_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha256).digest()
    ).decode("ascii")

    for candidate in _extract_signatures(signature_header):
        if hmac.compare_digest(expected, candidate):
            return
    raise WebhookVerificationError("Webhook signature mismatch.")


def verify_webhook(
    payload: str | bytes,
    headers: Mapping[str, str],
    secret: str,
    *,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> dict[str, Any]:
    """Verify the signature and return the parsed JSON event body.

    Raises ``WebhookVerificationError`` if the signature/timestamp is invalid.
    """
    verify_signature(payload, headers, secret, tolerance_seconds=tolerance_seconds)
    body = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
    event: dict[str, Any] = json.loads(body)
    return event
