# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Recipes (beta): `client.recipes.list()`, `get(slug)`, `run(slug, input, contract=..., idempotency_token=...)`, `result(job_id)` and the blocking `run_and_wait(...)`, on both clients, with `RecipeSummary`, `Recipe`, `RecipeContract`, `RecipeRun`, `RecipeResult` (`billed` property) and `RecipeIdentity` models.

## [1.2.0] - 2026-09-04

### Added
- Job stats endpoint: `client.jobs.stats(from_=..., to=..., job_type=...)` returns hourly throughput buckets with `JobStatsResponse`, `JobStatsBucket`, and `JobStatsTotals` models.
- Monitor change diff endpoint: `client.monitors.change_diff(monitor_id, change_id)` returns the unified diff for a detected change via `MonitorChangeDiff`.

## [1.1.0] - 2026-07-20

### Added
- MCP OAuth support: `AsyncScrapeNestClient(access_token=...)` for clients authenticating with an OIDC bearer token.
- Custom proxy (BYO egress) for stealth-tier jobs: `job(proxy={server: "..."})`.
- `JobEgress` model in job manifest forensics: track egress mode (`managed` | `custom`) and chained proxy details.

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

[1.2.0]: https://github.com/ScrapeNest/scrapenest-py-sdk/releases/tag/v1.2.0
[1.1.0]: https://github.com/ScrapeNest/scrapenest-py-sdk/releases/tag/v1.1.0
[1.0.0]: https://github.com/ScrapeNest/scrapenest-py-sdk/releases/tag/v1.0.0
