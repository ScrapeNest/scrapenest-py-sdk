from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

JobStatus = Literal["queued", "running", "succeeded", "failed"]
JobType = Literal["light", "standard", "stealth"]
ArtifactType = Literal[
    "html",
    "response_body",
    "screenshot",
    "har",
    "console",
    "extraction",
    "manifest",
]
ManifestStatus = Literal["completed", "failed"]
JobOutcome = Literal["success", "blocked", "failed"]


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    artifact_type: str
    byte_size: int = 0
    content_hash: str | None = None
    created_at: datetime | None = None
    download_url: str | None = None
    expires_at: datetime | None = None

    @property
    def size_bytes(self) -> int:
        """Backward-compatible alias for older examples."""
        return self.byte_size


@dataclass(frozen=True)
class Job:
    job_id: str
    status: str
    target_url: str
    created_at: datetime
    job_type: str | None = None
    #: Delivery outcome ("success" | "blocked" | "failed"); None until terminal.
    #: Distinct from ``status`` (lifecycle): a blocked scrape is status=succeeded.
    outcome: JobOutcome | None = None
    #: Present only when ``outcome == "blocked"``.
    block: JobBlock | None = None
    tags: list[str] = field(default_factory=list)
    completed_at: datetime | None = None
    failure_reason: str | None = None
    artifact_ids: list[str] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in ("succeeded", "failed")

    @property
    def blocked(self) -> bool:
        """Whether the target denied/challenged the crawl (no content delivered)."""
        return self.outcome == "blocked"


@dataclass(frozen=True)
class JobSummary:
    job_id: str
    job_type: str
    status: str
    target_url: str
    tags: list[str]
    created_at: datetime
    #: Delivery outcome ("success" | "blocked" | "failed"); None until terminal.
    outcome: JobOutcome | None = None
    block: JobBlock | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def blocked(self) -> bool:
        return self.outcome == "blocked"


@dataclass(frozen=True)
class JobListResponse:
    items: list[JobSummary]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class CreateJobResponse:
    job_id: str
    status: str
    created_at: datetime
    artifact_ids: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    idempotent_replay: bool = False
    """True when the server returned an existing job for a repeated idempotency_token (HTTP 200)."""


@dataclass(frozen=True)
class ArtifactDownload:
    artifact_id: str
    download_url: str
    expires_at: datetime


@dataclass(frozen=True)
class ScrapeResult:
    job_id: str
    status: Literal["succeeded", "failed"]
    failure_reason: str | None
    artifact_count: int
    completed_at: datetime
    artifacts: list[Artifact] = field(default_factory=list)


@dataclass(frozen=True)
class JobCredits:
    """Credit accounting for a job. Credits are charged only when content was delivered."""

    weight: int
    charged: bool
    amount: int


@dataclass(frozen=True)
class JobBlock:
    """Present when outcome=blocked: the crawl ran but the target denied or challenged it."""

    blocked: bool
    signal: str | None = None
    http_status: int | None = None


@dataclass(frozen=True)
class JobResponseInfo:
    """The target's HTTP response. Headers are sanitized server-side."""

    http_status: int | None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class JobTiming:
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class JobEgress:
    """Where the job's traffic exited: the ScrapeNest-managed pool, or a custom
    proxy chained through ScrapeNest. Never includes credentials."""

    mode: str  # "managed" | "custom"
    chained: bool = True
    proxy_server: str | None = None


@dataclass(frozen=True)
class JobManifest:
    """Forensics manifest of a terminal job. Source of truth for outcome and produced artifacts."""

    manifest_version: str
    job_id: str
    engine: str
    target_url: str
    status: str
    outcome: str
    final_url: str | None = None
    block: JobBlock | None = None
    response: JobResponseInfo | None = None
    timing: JobTiming | None = None
    user_agent: str | None = None
    retry_count: int | None = None
    request: dict[str, object] = field(default_factory=dict)
    credits: JobCredits | None = None
    egress: JobEgress | None = None
    artifacts: list[Artifact] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.outcome == "blocked"


MonitorStatus = Literal["active", "paused", "auto_paused"]
MonitorRunStatus = Literal[
    "minted",
    "delivered",
    "blocked",
    "failed",
    "skipped_quota",
    "skipped_not_allowed",
    "skipped_not_active",
    "error",
]
OverlapPolicy = Literal["skip", "buffer_one", "allow"]


@dataclass(frozen=True)
class Monitor:
    id: str
    name: str
    cron: str
    timezone: str
    job_type: str
    target_url: str
    overlap_policy: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    # Change-detection config + health, or None when detection is not configured.
    detection: dict[str, Any] | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class MonitorRun:
    id: str
    monitor_id: str
    status: str
    fired_at: datetime | None = None
    job_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class MonitorListResponse:
    items: list[Monitor]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class MonitorRunListResponse:
    items: list[MonitorRun]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class MonitorChange:
    """A detected change on a monitor (change detection)."""

    id: str
    new_fingerprint: str
    detected_at: datetime | None = None
    job_id: str | None = None
    run_id: str | None = None
    old_fingerprint: str | None = None
    change_ratio: float | None = None
    summary: str | None = None
    has_diff: bool = False
    notified_channels: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MonitorChangeListResponse:
    items: list[MonitorChange]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class MonitorChangeDiff:
    """The before/after unified diff for a detected change."""

    change_id: str
    format: str
    diff: str


@dataclass(frozen=True)
class JobStatsBucket:
    """Job counts for one UTC hour."""

    start: datetime
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    running: int = 0
    queued: int = 0


@dataclass(frozen=True)
class JobStatsTotals:
    """Aggregates over the whole stats window."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    running: int = 0
    queued: int = 0
    success_rate: float | None = None
    avg_duration_seconds: float | None = None


@dataclass(frozen=True)
class JobStatsResponse:
    """Hourly job throughput aggregation."""

    from_: datetime
    to: datetime
    bucket_seconds: int
    buckets: list[JobStatsBucket]
    totals: JobStatsTotals


@dataclass(frozen=True)
class AuditLogEntry:
    """A single audit record for a sensitive action in the organization."""

    id: str
    event_type: str
    action: str
    actor_type: str
    result: str
    severity: str
    actor_id: str | None = None
    metadata: dict[str, Any] | None = None
    source_ip: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class AuditLogListResponse:
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


ApiKeyStatus = Literal["active", "revoked"]
ApiKeyScope = Literal[
    "api_keys.manage",
    "webhooks.manage",
    "jobs.create",
    "jobs.read",
    "artifacts.read",
    "org.manage",
    "audit_logs.read",
    "billing.manage",
    "retention.manage",
    "privacy.manage",
]
EnforcementMode = Literal["block", "observe"]


@dataclass(frozen=True)
class ApiKey:
    """An API key as returned by listings. The token itself is never included."""

    api_key_id: str
    name: str
    prefix: str
    status: str
    scopes: list[str]
    rate_limit_rpm: int
    daily_quota: int
    max_concurrent_jobs: int
    enforcement_mode: str
    created_at: datetime
    description: str | None = None
    allowed_cidrs: list[str] = field(default_factory=list)
    last_used_at: datetime | None = None
    rotated_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class ApiKeyCreated:
    """Response to key creation. `token` is the plaintext key, shown once only."""

    api_key_id: str
    name: str
    prefix: str
    token: str
    scopes: list[str]
    rate_limit_rpm: int
    daily_quota: int
    max_concurrent_jobs: int
    enforcement_mode: str
    created_at: datetime
    description: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class ApiKeyRotation:
    """Rotation invalidates the previous token immediately - there is no overlap window."""

    api_key_id: str
    prefix: str
    token: str
    rotated_at: datetime


@dataclass(frozen=True)
class ApiKeyRevocation:
    api_key_id: str
    status: str
    revoked_at: datetime


@dataclass(frozen=True)
class ApiKeyIpAllowlist:
    api_key_id: str
    allowed_cidrs: list[str]


WebhookEndpointStatus = Literal["active", "paused", "disabled", "deleted"]


@dataclass(frozen=True)
class WebhookEndpoint:
    """A webhook endpoint as returned by listings (no signing secret)."""

    endpoint_id: str
    name: str
    url: str
    status: str
    secret_prefix: str
    created_at: datetime
    updated_at: datetime | None = None
    description: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    retry_config: dict[str, Any] | None = None
    consecutive_failures: int = 0
    last_health_status: str | None = None
    last_health_checked_at: datetime | None = None


@dataclass(frozen=True)
class WebhookEndpointCreated:
    """Response to endpoint creation. `secret` is the signing secret, shown once only."""

    endpoint_id: str
    name: str
    url: str
    status: str
    secret: str
    secret_prefix: str
    created_at: datetime
    updated_at: datetime | None = None
    description: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    retry_config: dict[str, Any] | None = None


@dataclass(frozen=True)
class WebhookEndpointUpdated:
    endpoint_id: str
    name: str
    url: str
    status: str
    updated_at: datetime | None = None
    description: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    retry_config: dict[str, Any] | None = None


@dataclass(frozen=True)
class WebhookSecretRotation:
    """Rotation invalidates the previous signing secret. Update consumers first."""

    endpoint_id: str
    secret: str
    secret_prefix: str
    rotated_at: datetime


@dataclass(frozen=True)
class WebhookEndpointStatusChange:
    endpoint_id: str
    status: str
    changed_at: datetime | None = None


@dataclass(frozen=True)
class WebhookMessage:
    """One event delivered (or being delivered) to a webhook endpoint."""

    message_id: str
    status: str
    payload: dict[str, Any]
    dispatched_at: datetime
    event_type: str | None = None
    event_id: str | None = None


@dataclass(frozen=True)
class WebhookMessagePage:
    """Cursor-paginated page of messages. Pass `iterator` back to fetch the next page."""

    endpoint_id: str
    items: list[WebhookMessage]
    iterator: str | None
    prev_iterator: str | None
    done: bool
    limit: int


@dataclass(frozen=True)
class WebhookMessageAttempt:
    id: str
    status: str
    dispatched_at: datetime
    status_code: int | None = None
    latency_ms: int | None = None
    response_body: str | None = None


@dataclass(frozen=True)
class WebhookMessageAttemptPage:
    endpoint_id: str
    message_id: str
    items: list[WebhookMessageAttempt]
    iterator: str | None
    prev_iterator: str | None
    done: bool
    limit: int


RetentionHoldScope = Literal["org", "job", "artifact"]
RetentionHoldStatus = Literal["active", "released"]


@dataclass(frozen=True)
class RetentionHold:
    """A legal/retention hold. Held artifacts are exempt from retention purges."""

    hold_id: str
    org_id: str
    scope_type: str
    status: str
    justification: str
    created_at: datetime
    scope_ref: str | None = None
    expires_at: datetime | None = None
    released_at: datetime | None = None


@dataclass(frozen=True)
class RetentionHoldList:
    org_id: str
    items: list[RetentionHold]


@dataclass(frozen=True)
class RetentionHoldRelease:
    hold_id: str
    status: str
    released_at: datetime


@dataclass(frozen=True)
class RetentionPolicy:
    org_id: str
    retention_days: int
    max_retention_days: int
    legal_hold_enabled: bool
    policy_version: int
    updated_at: datetime | None = None


@dataclass(frozen=True)
class OrgIpAllowlist:
    """Org-wide IP allowlist. Empty means no org-level restriction."""

    org_id: str
    allowed_cidrs: list[str]
