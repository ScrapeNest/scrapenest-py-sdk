from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest

from scrapenest import WebhookVerificationError, verify_signature, verify_webhook

SECRET = "whsec_dGVzdHNlY3JldA=="


def sign(payload: bytes, svix_id: str, timestamp: str, secret: str = SECRET) -> str:
    signed = f"{svix_id}.{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def headers_for(payload: bytes, *, svix_id="msg_1", ts=None, secret=SECRET) -> dict[str, str]:
    ts = ts or str(int(time.time()))
    return {
        "svix-id": svix_id,
        "svix-timestamp": ts,
        "svix-signature": sign(payload, svix_id, ts, secret),
    }


def test_verify_webhook_returns_parsed_event() -> None:
    payload = json.dumps({"type": "job.succeeded", "job_id": "job-1"}).encode()
    event = verify_webhook(payload, headers_for(payload), SECRET)
    assert event["type"] == "job.succeeded"


def test_verify_accepts_string_payload() -> None:
    payload = '{"type":"job.failed"}'
    event = verify_webhook(payload, headers_for(payload.encode()), SECRET)
    assert event["type"] == "job.failed"


def test_verify_accepts_multiple_space_separated_signatures() -> None:
    payload = b'{"ok":true}'
    real = headers_for(payload)["svix-signature"]
    h = headers_for(payload)
    h["svix-signature"] = f"v1,deadbeef {real}"
    verify_signature(payload, h, SECRET)  # should not raise


def test_bad_signature_raises() -> None:
    payload = b'{"ok":true}'
    h = headers_for(payload, secret="whsec_wrong")
    with pytest.raises(WebhookVerificationError):
        verify_signature(payload, h, SECRET)


def test_missing_headers_raises() -> None:
    with pytest.raises(WebhookVerificationError):
        verify_signature(b"{}", {}, SECRET)


def test_stale_timestamp_raises() -> None:
    payload = b'{"ok":true}'
    old = str(int(time.time()) - 4000)
    with pytest.raises(WebhookVerificationError):
        verify_signature(payload, headers_for(payload, ts=old), SECRET)


def test_tampered_body_raises() -> None:
    payload = b'{"amount":1}'
    h = headers_for(payload)
    with pytest.raises(WebhookVerificationError):
        verify_signature(b'{"amount":999}', h, SECRET)
