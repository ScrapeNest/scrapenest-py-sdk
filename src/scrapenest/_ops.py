"""Single-source API operation builders shared by the sync and async clients.

Every endpoint the SDK talks to is described exactly once here as an ``Op``:
the HTTP method, path, query params, JSON body, and response parser. The sync
and async resource classes only differ in how they *execute* an Op, so the two
client flavors cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import uuid4

import httpx

from scrapenest import _parsing
from scrapenest.models import (
    ApiKey,
    ApiKeyCreated,
    ApiKeyIpAllowlist,
    ApiKeyRevocation,
    ApiKeyRotation,
    ArtifactDownload,
    AuditLogListResponse,
    CreateJobResponse,
    Job,
    JobListResponse,
    Monitor,
    MonitorChangeListResponse,
    MonitorListResponse,
    MonitorRunListResponse,
    OrgIpAllowlist,
    RetentionHold,
    RetentionHoldList,
    RetentionHoldRelease,
    RetentionPolicy,
    WebhookEndpoint,
    WebhookEndpointCreated,
    WebhookEndpointStatusChange,
    WebhookEndpointUpdated,
    WebhookMessageAttemptPage,
    WebhookMessagePage,
    WebhookSecretRotation,
)

T = TypeVar("T")


@dataclass(frozen=True)
class Op(Generic[T]):
    """One prepared API call: what to send and how to read the response."""

    method: str
    path: str
    parse: Callable[[httpx.Response], T]
    params: dict[str, Any] | None = None
    json: Any | None = None


def _body(fn: Callable[[dict[str, Any]], T]) -> Callable[[httpx.Response], T]:
    """Adapt a JSON-dict parser into a response parser."""

    def parse(response: httpx.Response) -> T:
        data: dict[str, Any] = response.json()
        return fn(data)

    return parse


def _nothing(_: httpx.Response) -> None:
    return None


def _drop_none(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


# --- Jobs -----------------------------------------------------------------


def create_job(kwargs: dict[str, Any]) -> Op[CreateJobResponse]:
    body = _drop_none(kwargs)
    if "job_type" not in body or "target_url" not in body:
        raise ValueError("create() requires job_type and target_url")
    # Auto-attach an idempotency token so transparent retries never double-submit.
    body.setdefault("idempotency_token", uuid4().hex)

    def parse(response: httpx.Response) -> CreateJobResponse:
        return _parsing.parse_create_job(
            response.json(),
            headers=dict(response.headers),
            status_code=response.status_code,
        )

    return Op("POST", "/v1/jobs", parse, json=body)


def get_job(
    job_id: str,
    include_download_urls: bool | None,
    ttl_seconds: int | None,
) -> Op[Job]:
    params = _drop_none(
        {"include_download_urls": include_download_urls, "ttl_seconds": ttl_seconds}
    )
    return Op("GET", f"/v1/jobs/{job_id}", _body(_parsing.parse_job), params=params)


def list_jobs(
    *,
    status: str | None,
    job_type: str | None,
    job_id: str | None,
    target_url: str | None,
    tag: str | None,
    from_: str | None,
    to: str | None,
    limit: int | None,
    offset: int | None,
) -> Op[JobListResponse]:
    params = _drop_none(
        {
            "status": status,
            "job_type": job_type,
            "job_id": job_id,
            "target_url": target_url,
            "tag": tag,
            "from": from_,
            "to": to,
            "limit": limit,
            "offset": offset,
        }
    )
    return Op("GET", "/v1/jobs", _body(_parsing.parse_job_list), params=params)


# --- Artifacts ------------------------------------------------------------


def get_artifact_download(artifact_id: str, ttl_seconds: int | None) -> Op[ArtifactDownload]:
    params = _drop_none({"ttl_seconds": ttl_seconds})
    return Op(
        "GET",
        f"/v1/artifacts/{artifact_id}/download",
        _body(_parsing.parse_artifact_download),
        params=params,
    )


# --- Monitors ------------------------------------------------------------


def _monitor_body(
    name: str,
    cron: str,
    job_type: str,
    target_url: str,
    timezone: str | None,
    overlap_policy: str | None,
    payload: dict[str, Any] | None,
    detection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = _drop_none(
        {
            "name": name,
            "cron": cron,
            "job_type": job_type,
            "target_url": target_url,
            "timezone": timezone,
            "overlap_policy": overlap_policy,
        }
    )
    if payload:
        body["payload"] = payload
    if detection is not None:
        body["detection"] = detection
    return body


def create_monitor(
    name: str,
    cron: str,
    job_type: str,
    target_url: str,
    timezone: str | None,
    overlap_policy: str | None,
    payload: dict[str, Any] | None,
    detection: dict[str, Any] | None = None,
) -> Op[Monitor]:
    body = _monitor_body(name, cron, job_type, target_url, timezone, overlap_policy, payload, detection)
    return Op("POST", "/v1/monitors", _body(_parsing.parse_monitor), json=body)


def get_monitor(monitor_id: str) -> Op[Monitor]:
    return Op("GET", f"/v1/monitors/{monitor_id}", _body(_parsing.parse_monitor))


def list_monitors(
    status: str | None, limit: int | None, offset: int | None
) -> Op[MonitorListResponse]:
    params = _drop_none({"status": status, "limit": limit, "offset": offset})
    return Op("GET", "/v1/monitors", _body(_parsing.parse_monitor_list), params=params)


def update_monitor(
    monitor_id: str,
    name: str,
    cron: str,
    job_type: str,
    target_url: str,
    timezone: str | None,
    overlap_policy: str | None,
    payload: dict[str, Any] | None,
    detection: dict[str, Any] | None = None,
) -> Op[Monitor]:
    body = _monitor_body(name, cron, job_type, target_url, timezone, overlap_policy, payload, detection)
    return Op("PATCH", f"/v1/monitors/{monitor_id}", _body(_parsing.parse_monitor), json=body)


def pause_monitor(monitor_id: str) -> Op[Monitor]:
    return Op("POST", f"/v1/monitors/{monitor_id}/pause", _body(_parsing.parse_monitor))


def resume_monitor(monitor_id: str) -> Op[Monitor]:
    return Op("POST", f"/v1/monitors/{monitor_id}/resume", _body(_parsing.parse_monitor))


def delete_monitor(monitor_id: str) -> Op[None]:
    return Op("DELETE", f"/v1/monitors/{monitor_id}", _nothing)


def list_monitor_runs(
    monitor_id: str, limit: int | None, offset: int | None
) -> Op[MonitorRunListResponse]:
    params = _drop_none({"limit": limit, "offset": offset})
    return Op(
        "GET",
        f"/v1/monitors/{monitor_id}/runs",
        _body(_parsing.parse_monitor_run_list),
        params=params,
    )


def list_monitor_changes(
    monitor_id: str, limit: int | None, offset: int | None
) -> Op[MonitorChangeListResponse]:
    params = _drop_none({"limit": limit, "offset": offset})
    return Op(
        "GET",
        f"/v1/monitors/{monitor_id}/changes",
        _body(_parsing.parse_monitor_change_list),
        params=params,
    )


# --- Audit logs -----------------------------------------------------------


def list_audit_logs(
    severity: str | None,
    result: str | None,
    event_type: str | None,
    limit: int | None,
    offset: int | None,
) -> Op[AuditLogListResponse]:
    params = _drop_none(
        {
            "severity": severity,
            "result": result,
            "event_type": event_type,
            "limit": limit,
            "offset": offset,
        }
    )
    return Op(
        "GET",
        "/v1/audit-logs",
        _body(_parsing.parse_audit_log_list),
        params=params,
    )


# --- API keys -------------------------------------------------------------


def list_api_keys() -> Op[list[ApiKey]]:
    return Op("GET", "/v1/keys", _body(_parsing.parse_api_key_list))


def create_api_key(
    *,
    name: str,
    scopes: list[str],
    description: str | None,
    expires_at: str | None,
    allowed_cidrs: list[str] | None,
    rate_limit_rpm: int | None,
    daily_quota: int | None,
    max_concurrent_jobs: int | None,
    enforcement_mode: str | None,
) -> Op[ApiKeyCreated]:
    body = _drop_none(
        {
            "name": name,
            "scopes": scopes,
            "description": description,
            "expires_at": expires_at,
            "allowed_cidrs": allowed_cidrs,
            "rate_limit_rpm": rate_limit_rpm,
            "daily_quota": daily_quota,
            "max_concurrent_jobs": max_concurrent_jobs,
            "enforcement_mode": enforcement_mode,
        }
    )
    return Op("POST", "/v1/keys", _body(_parsing.parse_api_key_created), json=body)


def rotate_api_key(key_id: str) -> Op[ApiKeyRotation]:
    return Op("POST", f"/v1/keys/{key_id}/rotate", _body(_parsing.parse_api_key_rotation))


def revoke_api_key(key_id: str, reason: str | None) -> Op[ApiKeyRevocation]:
    body = _drop_none({"reason": reason})
    return Op(
        "POST",
        f"/v1/keys/{key_id}/revoke",
        _body(_parsing.parse_api_key_revocation),
        json=body,
    )


def set_api_key_ip_allowlist(key_id: str, allowed_cidrs: list[str]) -> Op[ApiKeyIpAllowlist]:
    return Op(
        "PUT",
        f"/v1/keys/{key_id}/ip-allowlist",
        _body(_parsing.parse_api_key_ip_allowlist),
        json={"allowed_cidrs": allowed_cidrs},
    )


# --- Webhook endpoints ----------------------------------------------------


def _webhook_endpoint_body(
    name: str,
    url: str,
    description: str | None,
    metadata: dict[str, str] | None,
    retry_config: dict[str, Any] | None,
) -> dict[str, Any]:
    return _drop_none(
        {
            "name": name,
            "url": url,
            "description": description,
            "metadata": metadata,
            "retry_config": retry_config,
        }
    )


def list_webhook_endpoints() -> Op[list[WebhookEndpoint]]:
    return Op("GET", "/v1/webhook-endpoints", _body(_parsing.parse_webhook_endpoint_list))


def create_webhook_endpoint(
    name: str,
    url: str,
    description: str | None,
    metadata: dict[str, str] | None,
    retry_config: dict[str, Any] | None,
) -> Op[WebhookEndpointCreated]:
    body = _webhook_endpoint_body(name, url, description, metadata, retry_config)
    return Op(
        "POST",
        "/v1/webhook-endpoints",
        _body(_parsing.parse_webhook_endpoint_created),
        json=body,
    )


def update_webhook_endpoint(
    endpoint_id: str,
    name: str,
    url: str,
    description: str | None,
    metadata: dict[str, str] | None,
    retry_config: dict[str, Any] | None,
) -> Op[WebhookEndpointUpdated]:
    body = _webhook_endpoint_body(name, url, description, metadata, retry_config)
    return Op(
        "PUT",
        f"/v1/webhook-endpoints/{endpoint_id}",
        _body(_parsing.parse_webhook_endpoint_updated),
        json=body,
    )


def delete_webhook_endpoint(endpoint_id: str) -> Op[None]:
    return Op("DELETE", f"/v1/webhook-endpoints/{endpoint_id}", _nothing)


def rotate_webhook_secret(endpoint_id: str) -> Op[WebhookSecretRotation]:
    return Op(
        "POST",
        f"/v1/webhook-endpoints/{endpoint_id}/rotate-secret",
        _body(_parsing.parse_webhook_secret_rotation),
    )


def pause_webhook_endpoint(endpoint_id: str) -> Op[WebhookEndpointStatusChange]:
    return Op(
        "POST",
        f"/v1/webhook-endpoints/{endpoint_id}/pause",
        _body(_parsing.parse_webhook_endpoint_status_change),
    )


def resume_webhook_endpoint(endpoint_id: str) -> Op[WebhookEndpointStatusChange]:
    return Op(
        "POST",
        f"/v1/webhook-endpoints/{endpoint_id}/resume",
        _body(_parsing.parse_webhook_endpoint_status_change),
    )


def list_webhook_messages(
    endpoint_id: str, limit: int | None, iterator: str | None
) -> Op[WebhookMessagePage]:
    params = _drop_none({"limit": limit, "iterator": iterator})
    return Op(
        "GET",
        f"/v1/webhook-endpoints/{endpoint_id}/messages",
        _body(_parsing.parse_webhook_message_page),
        params=params,
    )


def list_webhook_attempts(
    endpoint_id: str, message_id: str, limit: int | None, iterator: str | None
) -> Op[WebhookMessageAttemptPage]:
    params = _drop_none({"limit": limit, "iterator": iterator})
    return Op(
        "GET",
        f"/v1/webhook-endpoints/{endpoint_id}/messages/{message_id}/attempts",
        _body(_parsing.parse_webhook_attempt_page),
        params=params,
    )


# --- Retention ------------------------------------------------------------


def get_retention_policy() -> Op[RetentionPolicy]:
    return Op("GET", "/v1/org/retention-policy", _body(_parsing.parse_retention_policy))


def update_retention_policy(retention_days: int, legal_hold_enabled: bool) -> Op[RetentionPolicy]:
    body = {"retention_days": retention_days, "legal_hold_enabled": legal_hold_enabled}
    return Op(
        "PUT", "/v1/org/retention-policy", _body(_parsing.parse_retention_policy), json=body
    )


def list_retention_holds() -> Op[RetentionHoldList]:
    return Op("GET", "/v1/org/retention-holds", _body(_parsing.parse_retention_hold_list))


def create_retention_hold(
    scope_type: str,
    justification: str,
    scope_ref: str | None,
    expires_at: str | None,
) -> Op[RetentionHold]:
    body = _drop_none(
        {
            "scope_type": scope_type,
            "justification": justification,
            "scope_ref": scope_ref,
            "expires_at": expires_at,
        }
    )
    return Op(
        "POST", "/v1/org/retention-holds", _body(_parsing.parse_retention_hold), json=body
    )


def release_retention_hold(hold_id: str, release_notes: str) -> Op[RetentionHoldRelease]:
    return Op(
        "POST",
        f"/v1/org/retention-holds/{hold_id}/release",
        _body(_parsing.parse_retention_hold_release),
        json={"release_notes": release_notes},
    )


# --- Org security ---------------------------------------------------------


def get_org_ip_allowlist() -> Op[OrgIpAllowlist]:
    return Op("GET", "/v1/org/security/ip-allowlist", _body(_parsing.parse_org_ip_allowlist))


def set_org_ip_allowlist(allowed_cidrs: list[str]) -> Op[OrgIpAllowlist]:
    return Op(
        "PUT",
        "/v1/org/security/ip-allowlist",
        _body(_parsing.parse_org_ip_allowlist),
        json={"allowed_cidrs": allowed_cidrs},
    )
