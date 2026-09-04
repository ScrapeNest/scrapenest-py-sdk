"""Transport-agnostic parsing of API responses into models.

These are pure functions shared by the sync and async resources so the two
client flavors never drift apart.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scrapenest.models import (
    ApiKey,
    ApiKeyCreated,
    ApiKeyIpAllowlist,
    ApiKeyRevocation,
    ApiKeyRotation,
    Artifact,
    ArtifactDownload,
    AuditLogEntry,
    AuditLogListResponse,
    CreateJobResponse,
    Job,
    JobBlock,
    JobCredits,
    JobListResponse,
    JobManifest,
    JobResponseInfo,
    JobStatsBucket,
    JobStatsResponse,
    JobStatsTotals,
    JobSummary,
    JobTiming,
    Monitor,
    MonitorChange,
    MonitorChangeDiff,
    MonitorChangeListResponse,
    MonitorListResponse,
    MonitorRun,
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
    WebhookMessage,
    WebhookMessageAttempt,
    WebhookMessageAttemptPage,
    WebhookMessagePage,
    WebhookSecretRotation,
)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or value == "":
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_datetime(value: Any, what: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"{what} response did not include a valid timestamp.")
    return parsed


def _str_map(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _str_list(data: Any) -> list[str]:
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def parse_artifact(data: dict[str, Any]) -> Artifact:
    return Artifact(
        artifact_id=data["artifact_id"],
        artifact_type=data.get("artifact_type", ""),
        byte_size=int(data.get("byte_size") or data.get("size_bytes") or 0),
        content_hash=data.get("content_hash"),
        created_at=parse_datetime(data.get("created_at")),
        download_url=data.get("download_url"),
        expires_at=parse_datetime(data.get("expires_at")),
    )


def parse_job(data: dict[str, Any]) -> Job:
    return Job(
        job_id=data["job_id"],
        status=data["status"],
        outcome=data.get("outcome"),
        block=_parse_block(data.get("block")),
        job_type=data.get("job_type"),
        target_url=data.get("target_url", ""),
        tags=list(data.get("tags") or []),
        created_at=_require_datetime(data.get("created_at"), "Job"),
        completed_at=parse_datetime(data.get("completed_at")),
        failure_reason=data.get("failure_reason"),
        artifact_ids=list(data.get("artifact_ids") or []),
        artifacts=[parse_artifact(item) for item in data.get("artifacts", [])],
    )


def parse_job_summary(data: dict[str, Any]) -> JobSummary:
    return JobSummary(
        job_id=data["job_id"],
        job_type=data.get("job_type", ""),
        status=data["status"],
        outcome=data.get("outcome"),
        block=_parse_block(data.get("block")),
        target_url=data.get("target_url", ""),
        tags=list(data.get("tags") or []),
        created_at=_require_datetime(data.get("created_at"), "Job summary"),
        updated_at=parse_datetime(data.get("updated_at")),
        completed_at=parse_datetime(data.get("completed_at")),
    )


def parse_job_list(data: dict[str, Any]) -> JobListResponse:
    return JobListResponse(
        items=[parse_job_summary(item) for item in data.get("items", [])],
        total=int(data.get("total", 0)),
        limit=int(data.get("limit", 0)),
        offset=int(data.get("offset", 0)),
    )


def parse_job_stats_bucket(data: dict[str, Any]) -> JobStatsBucket:
    return JobStatsBucket(
        start=_require_datetime(data.get("start"), "JobStatsBucket"),
        total=int(data.get("total", 0)),
        succeeded=int(data.get("succeeded", 0)),
        failed=int(data.get("failed", 0)),
        running=int(data.get("running", 0)),
        queued=int(data.get("queued", 0)),
    )


def parse_job_stats(data: dict[str, Any]) -> JobStatsResponse:
    totals_raw = data.get("totals", {})
    sr = totals_raw.get("success_rate")
    ad = totals_raw.get("avg_duration_seconds")
    return JobStatsResponse(
        from_=_require_datetime(data.get("from"), "JobStats"),
        to=_require_datetime(data.get("to"), "JobStats"),
        bucket_seconds=int(data.get("bucket_seconds", 3600)),
        buckets=[parse_job_stats_bucket(b) for b in data.get("buckets", [])],
        totals=JobStatsTotals(
            total=int(totals_raw.get("total", 0)),
            succeeded=int(totals_raw.get("succeeded", 0)),
            failed=int(totals_raw.get("failed", 0)),
            running=int(totals_raw.get("running", 0)),
            queued=int(totals_raw.get("queued", 0)),
            success_rate=float(sr) if sr is not None else None,
            avg_duration_seconds=float(ad) if ad is not None else None,
        ),
    )


def parse_create_job(
    data: dict[str, Any],
    *,
    headers: dict[str, str],
    status_code: int,
) -> CreateJobResponse:
    return CreateJobResponse(
        job_id=data["job_id"],
        status=data.get("status", "queued"),
        created_at=_require_datetime(data.get("created_at"), "Job create"),
        artifact_ids=list(data.get("artifact_ids") or []),
        headers=headers,
        idempotent_replay=status_code == 200,
    )


def parse_artifact_download(data: dict[str, Any]) -> ArtifactDownload:
    expires_at = parse_datetime(data.get("expires_at"))
    if expires_at is None:
        raise ValueError("Artifact download response did not include expires_at.")
    return ArtifactDownload(
        artifact_id=data["artifact_id"],
        download_url=data["download_url"],
        expires_at=expires_at,
    )


def _parse_block(data: Any) -> JobBlock | None:
    if not isinstance(data, dict):
        return None
    return JobBlock(
        blocked=bool(data.get("blocked")),
        signal=data.get("signal"),
        http_status=data.get("http_status"),
    )


def _parse_response_info(data: Any) -> JobResponseInfo | None:
    if not isinstance(data, dict):
        return None
    headers = data.get("headers") or {}
    return JobResponseInfo(
        http_status=data.get("http_status"),
        headers={str(k): str(v) for k, v in headers.items()},
    )


def _parse_timing(data: Any) -> JobTiming | None:
    if not isinstance(data, dict):
        return None
    return JobTiming(
        started_at=parse_datetime(data.get("started_at")),
        finished_at=parse_datetime(data.get("finished_at")),
        duration_ms=int(data.get("duration_ms") or 0),
    )


def _parse_credits(data: Any) -> JobCredits | None:
    if not isinstance(data, dict):
        return None
    return JobCredits(
        weight=int(data.get("weight") or 0),
        charged=bool(data.get("charged")),
        amount=int(data.get("amount") or 0),
    )


def parse_manifest(data: dict[str, Any]) -> JobManifest:
    return JobManifest(
        manifest_version=data.get("manifest_version", ""),
        job_id=data["job_id"],
        engine=data.get("engine", ""),
        target_url=data.get("target_url", ""),
        status=data.get("status", ""),
        outcome=data.get("outcome", ""),
        final_url=data.get("final_url"),
        block=_parse_block(data.get("block")),
        response=_parse_response_info(data.get("response")),
        timing=_parse_timing(data.get("timing")),
        user_agent=data.get("user_agent"),
        retry_count=data.get("retry_count"),
        request=dict(data.get("request") or {}),
        credits=_parse_credits(data.get("credits")),
        artifacts=[parse_artifact(item) for item in data.get("artifacts", [])],
    )


def parse_monitor(data: dict[str, Any]) -> Monitor:
    return Monitor(
        id=data["id"],
        name=data.get("name", ""),
        cron=data.get("cron", ""),
        timezone=data.get("timezone", "UTC"),
        job_type=data.get("job_type", ""),
        target_url=data.get("target_url", ""),
        overlap_policy=data.get("overlap_policy", "skip"),
        status=data.get("status", "active"),
        payload=dict(data.get("payload") or {}),
        detection=(dict(data["detection"]) if isinstance(data.get("detection"), dict) else None),
        last_run_at=parse_datetime(data.get("last_run_at")),
        next_run_at=parse_datetime(data.get("next_run_at")),
        created_at=parse_datetime(data.get("created_at")),
        updated_at=parse_datetime(data.get("updated_at")),
    )


def parse_monitor_list(data: dict[str, Any]) -> MonitorListResponse:
    return MonitorListResponse(
        items=[parse_monitor(item) for item in data.get("items", [])],
        total=int(data.get("total", 0)),
        limit=int(data.get("limit", 0)),
        offset=int(data.get("offset", 0)),
    )


def parse_monitor_run(data: dict[str, Any]) -> MonitorRun:
    return MonitorRun(
        id=data["id"],
        monitor_id=data.get("monitor_id", ""),
        status=data.get("status", ""),
        fired_at=parse_datetime(data.get("fired_at")),
        job_id=data.get("job_id"),
        detail=data.get("detail"),
    )


def parse_monitor_run_list(data: dict[str, Any]) -> MonitorRunListResponse:
    return MonitorRunListResponse(
        items=[parse_monitor_run(item) for item in data.get("items", [])],
        total=int(data.get("total", 0)),
        limit=int(data.get("limit", 0)),
        offset=int(data.get("offset", 0)),
    )


def parse_monitor_change(data: dict[str, Any]) -> MonitorChange:
    ratio = data.get("change_ratio")
    return MonitorChange(
        id=data["id"],
        new_fingerprint=data.get("new_fingerprint", ""),
        detected_at=parse_datetime(data.get("detected_at")),
        job_id=data.get("job_id"),
        run_id=data.get("run_id"),
        old_fingerprint=data.get("old_fingerprint"),
        change_ratio=float(ratio) if ratio is not None else None,
        summary=data.get("summary"),
        has_diff=bool(data.get("has_diff", False)),
        notified_channels=list(data.get("notified_channels") or []),
    )


def parse_monitor_change_list(data: dict[str, Any]) -> MonitorChangeListResponse:
    return MonitorChangeListResponse(
        items=[parse_monitor_change(item) for item in data.get("items", [])],
        total=int(data.get("total", 0)),
        limit=int(data.get("limit", 0)),
        offset=int(data.get("offset", 0)),
    )


def parse_monitor_change_diff(data: dict[str, Any]) -> MonitorChangeDiff:
    return MonitorChangeDiff(
        change_id=data["change_id"],
        format=data.get("format", "unified"),
        diff=data.get("diff", ""),
    )


def parse_audit_log_entry(data: dict[str, Any]) -> AuditLogEntry:
    return AuditLogEntry(
        id=data["id"],
        event_type=data.get("event_type", ""),
        action=data.get("action", ""),
        actor_type=data.get("actor_type", ""),
        result=data.get("result", ""),
        severity=data.get("severity", ""),
        actor_id=data.get("actor_id"),
        metadata=data.get("metadata"),
        source_ip=data.get("source_ip"),
        occurred_at=parse_datetime(data.get("occurred_at")),
    )


def parse_audit_log_list(data: dict[str, Any]) -> AuditLogListResponse:
    return AuditLogListResponse(
        items=[parse_audit_log_entry(item) for item in data.get("items", [])],
        total=int(data.get("total", 0)),
        limit=int(data.get("limit", 0)),
        offset=int(data.get("offset", 0)),
    )


def parse_api_key(data: dict[str, Any]) -> ApiKey:
    return ApiKey(
        api_key_id=data["api_key_id"],
        name=data.get("name", ""),
        prefix=data.get("prefix", ""),
        status=data.get("status", ""),
        scopes=_str_list(data.get("scopes")),
        rate_limit_rpm=int(data.get("rate_limit_rpm") or 0),
        daily_quota=int(data.get("daily_quota") or 0),
        max_concurrent_jobs=int(data.get("max_concurrent_jobs") or 0),
        enforcement_mode=data.get("enforcement_mode", ""),
        created_at=_require_datetime(data.get("created_at"), "API key"),
        description=data.get("description"),
        allowed_cidrs=_str_list(data.get("allowed_cidrs")),
        last_used_at=parse_datetime(data.get("last_used_at")),
        rotated_at=parse_datetime(data.get("rotated_at")),
        expires_at=parse_datetime(data.get("expires_at")),
    )


def parse_api_key_list(data: dict[str, Any]) -> list[ApiKey]:
    return [parse_api_key(item) for item in data.get("items", [])]


def parse_api_key_created(data: dict[str, Any]) -> ApiKeyCreated:
    return ApiKeyCreated(
        api_key_id=data["api_key_id"],
        name=data.get("name", ""),
        prefix=data.get("prefix", ""),
        token=data["token"],
        scopes=_str_list(data.get("scopes")),
        rate_limit_rpm=int(data.get("rate_limit_rpm") or 0),
        daily_quota=int(data.get("daily_quota") or 0),
        max_concurrent_jobs=int(data.get("max_concurrent_jobs") or 0),
        enforcement_mode=data.get("enforcement_mode", ""),
        created_at=_require_datetime(data.get("created_at"), "API key create"),
        description=data.get("description"),
        expires_at=parse_datetime(data.get("expires_at")),
    )


def parse_api_key_rotation(data: dict[str, Any]) -> ApiKeyRotation:
    return ApiKeyRotation(
        api_key_id=data["api_key_id"],
        prefix=data.get("prefix", ""),
        token=data["token"],
        rotated_at=_require_datetime(data.get("rotated_at"), "API key rotate"),
    )


def parse_api_key_revocation(data: dict[str, Any]) -> ApiKeyRevocation:
    return ApiKeyRevocation(
        api_key_id=data["api_key_id"],
        status=data.get("status", "revoked"),
        revoked_at=_require_datetime(data.get("revoked_at"), "API key revoke"),
    )


def parse_api_key_ip_allowlist(data: dict[str, Any]) -> ApiKeyIpAllowlist:
    return ApiKeyIpAllowlist(
        api_key_id=data["api_key_id"],
        allowed_cidrs=_str_list(data.get("allowed_cidrs")),
    )


def _retry_config(data: Any) -> dict[str, Any] | None:
    return dict(data) if isinstance(data, dict) else None


def parse_webhook_endpoint(data: dict[str, Any]) -> WebhookEndpoint:
    return WebhookEndpoint(
        endpoint_id=data["endpoint_id"],
        name=data.get("name", ""),
        url=data.get("url", ""),
        status=data.get("status", ""),
        secret_prefix=data.get("secret_prefix", ""),
        created_at=_require_datetime(data.get("created_at"), "Webhook endpoint"),
        updated_at=parse_datetime(data.get("updated_at")),
        description=data.get("description"),
        metadata=_str_map(data.get("metadata")),
        retry_config=_retry_config(data.get("retry_config")),
        consecutive_failures=int(data.get("consecutive_failures") or 0),
        last_health_status=data.get("last_health_status"),
        last_health_checked_at=parse_datetime(data.get("last_health_checked_at")),
    )


def parse_webhook_endpoint_list(data: dict[str, Any]) -> list[WebhookEndpoint]:
    return [parse_webhook_endpoint(item) for item in data.get("items", [])]


def parse_webhook_endpoint_created(data: dict[str, Any]) -> WebhookEndpointCreated:
    return WebhookEndpointCreated(
        endpoint_id=data["endpoint_id"],
        name=data.get("name", ""),
        url=data.get("url", ""),
        status=data.get("status", ""),
        secret=data["secret"],
        secret_prefix=data.get("secret_prefix", ""),
        created_at=_require_datetime(data.get("created_at"), "Webhook endpoint create"),
        updated_at=parse_datetime(data.get("updated_at")),
        description=data.get("description"),
        metadata=_str_map(data.get("metadata")),
        retry_config=_retry_config(data.get("retry_config")),
    )


def parse_webhook_endpoint_updated(data: dict[str, Any]) -> WebhookEndpointUpdated:
    return WebhookEndpointUpdated(
        endpoint_id=data["endpoint_id"],
        name=data.get("name", ""),
        url=data.get("url", ""),
        status=data.get("status", ""),
        updated_at=parse_datetime(data.get("updated_at")),
        description=data.get("description"),
        metadata=_str_map(data.get("metadata")),
        retry_config=_retry_config(data.get("retry_config")),
    )


def parse_webhook_secret_rotation(data: dict[str, Any]) -> WebhookSecretRotation:
    return WebhookSecretRotation(
        endpoint_id=data["endpoint_id"],
        secret=data["secret"],
        secret_prefix=data.get("secret_prefix", ""),
        rotated_at=_require_datetime(data.get("rotated_at"), "Webhook secret rotate"),
    )


def parse_webhook_endpoint_status_change(data: dict[str, Any]) -> WebhookEndpointStatusChange:
    return WebhookEndpointStatusChange(
        endpoint_id=data["endpoint_id"],
        status=data.get("status", ""),
        changed_at=parse_datetime(data.get("paused_at") or data.get("resumed_at")),
    )


def parse_webhook_message(data: dict[str, Any]) -> WebhookMessage:
    return WebhookMessage(
        message_id=data["message_id"],
        status=data.get("status", ""),
        payload=dict(data.get("payload") or {}),
        dispatched_at=_require_datetime(data.get("dispatched_at"), "Webhook message"),
        event_type=data.get("event_type"),
        event_id=data.get("event_id"),
    )


def parse_webhook_message_page(data: dict[str, Any]) -> WebhookMessagePage:
    return WebhookMessagePage(
        endpoint_id=data.get("endpoint_id", ""),
        items=[parse_webhook_message(item) for item in data.get("items", [])],
        iterator=data.get("iterator"),
        prev_iterator=data.get("prev_iterator"),
        done=bool(data.get("done", True)),
        limit=int(data.get("limit") or 0),
    )


def parse_webhook_attempt(data: dict[str, Any]) -> WebhookMessageAttempt:
    return WebhookMessageAttempt(
        id=data["id"],
        status=data.get("status", ""),
        dispatched_at=_require_datetime(data.get("dispatched_at"), "Webhook attempt"),
        status_code=data.get("status_code"),
        latency_ms=data.get("latency_ms"),
        response_body=data.get("response_body"),
    )


def parse_webhook_attempt_page(data: dict[str, Any]) -> WebhookMessageAttemptPage:
    return WebhookMessageAttemptPage(
        endpoint_id=data.get("endpoint_id", ""),
        message_id=data.get("message_id", ""),
        items=[parse_webhook_attempt(item) for item in data.get("items", [])],
        iterator=data.get("iterator"),
        prev_iterator=data.get("prev_iterator"),
        done=bool(data.get("done", True)),
        limit=int(data.get("limit") or 0),
    )


def parse_retention_hold(data: dict[str, Any]) -> RetentionHold:
    return RetentionHold(
        hold_id=data["hold_id"],
        org_id=data.get("org_id", ""),
        scope_type=data.get("scope_type", ""),
        status=data.get("status", ""),
        justification=data.get("justification", ""),
        created_at=_require_datetime(data.get("created_at"), "Retention hold"),
        scope_ref=data.get("scope_ref"),
        expires_at=parse_datetime(data.get("expires_at")),
        released_at=parse_datetime(data.get("released_at")),
    )


def parse_retention_hold_list(data: dict[str, Any]) -> RetentionHoldList:
    return RetentionHoldList(
        org_id=data.get("org_id", ""),
        items=[parse_retention_hold(item) for item in data.get("items", [])],
    )


def parse_retention_hold_release(data: dict[str, Any]) -> RetentionHoldRelease:
    return RetentionHoldRelease(
        hold_id=data["hold_id"],
        status=data.get("status", "released"),
        released_at=_require_datetime(data.get("released_at"), "Retention hold release"),
    )


def parse_retention_policy(data: dict[str, Any]) -> RetentionPolicy:
    return RetentionPolicy(
        org_id=data.get("org_id", ""),
        retention_days=int(data.get("retention_days") or 0),
        max_retention_days=int(data.get("max_retention_days") or 0),
        legal_hold_enabled=bool(data.get("legal_hold_enabled")),
        policy_version=int(data.get("policy_version") or 0),
        updated_at=parse_datetime(data.get("updated_at")),
    )


def parse_org_ip_allowlist(data: dict[str, Any]) -> OrgIpAllowlist:
    return OrgIpAllowlist(
        org_id=data.get("org_id", ""),
        allowed_cidrs=_str_list(data.get("allowed_cidrs")),
    )
