# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-15

First public release.

### Added
- Sync (`ScrapeNestClient`) and async (`AsyncScrapeNestClient`) clients with identical surfaces.
- `client.scrape(...)` (submit and wait) and `client.submit(...)` (fire and collect later).
- Typed job-create overloads per tier (`light`/`standard`/`stealth`) with autocomplete for
  extraction hooks, browser actions, proxy, retry policy, viewport, and artifact options.
- `client.jobs`: create, get, list, `iter()` pagination, `get_manifest()` (outcome, credits, block, timing).
- `client.artifacts`: presigned download URLs plus `download_bytes` / `download_text` helpers.
- `client.monitors`: recurring cron scrapes - create, update, pause/resume, delete, run history
  (`runs` / `iter_runs`).
- Change detection: `detection=` on `monitors.create/update`, `monitors.changes(...)` /
  `iter_changes(...)`, and `Monitor.detection` with `MonitorChange` /
  `MonitorChangeListResponse` models.
- `client.webhook_endpoints`: endpoint CRUD, secret rotation, pause/resume, delivery messages
  and per-attempt forensics with cursor pagination.
- `client.api_keys`: list, create (scopes, expiry, per-key limits, IP allowlist), rotate, revoke.
- `client.retention`: retention policy read/update, legal holds (create, list, release).
- `client.org`: organization IP allowlist read/replace.
- `client.audit_logs`: read the organization audit trail with `severity` / `result` /
  `event_type` filters and transparent pagination.
- Automatic retries with jittered exponential backoff on `429`/`5xx` and transport errors,
  honoring `Retry-After`; configurable via `max_retries` / `backoff_factor`.
- Automatic `idempotency_token` on job creation so retries never double-submit; `CreateJobResponse.idempotent_replay`.
- Typed exception taxonomy: `BadRequestError`, `AuthenticationError`, `PermissionDeniedError`,
  `NotFoundError`, `ConflictError`, `ValidationError`, `RateLimitError`, `ServerError`,
  `ScrapeNestConnectionError`.
- `verify_webhook()` / `verify_signature()` for Svix-scheme webhook signature verification.

[1.0.0]: https://github.com/scrapenest/scrapenest-py-sdk/releases/tag/v1.0.0
