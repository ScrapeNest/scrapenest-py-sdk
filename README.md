# ScrapeNest Python SDK

The official Python client for the [ScrapeNest](https://scrapenest.com) scraping API. Submit
scraping jobs, wait for or collect their results, download artifacts, manage monitors, webhook
endpoints, and API keys - everything the API offers, fully typed.

```bash
pip install scrapenest-sdk
```

```python
import scrapenest
```

Requires Python 3.10+. The only runtime dependency is [httpx](https://www.python-httpx.org/).

## Quick start

```python
from scrapenest import ScrapeNestClient

client = ScrapeNestClient(api_key="sn_live_...")

# Submit and wait (polls until terminal, up to `timeout` seconds)
result = client.scrape(job_type="light", target_url="https://example.com")
print(result.status, result.artifact_count)

# Fetch the rendered HTML artifact
job = client.jobs.get(result.job_id)
html_artifact = next(a for a in job.artifacts if a.artifact_type == "html")
html = client.artifacts.download_text(html_artifact.artifact_id)
```

Authentication uses your API key, sent automatically in the `X-API-Key` header. Create and manage
keys in the dashboard (or with `client.api_keys`, below).

## Job tiers

`job_type` selects the worker tier; the SDK gives you autocomplete for each tier's options:

| Tier | What it does | Tier-specific options |
|------|--------------|-----------------------|
| `light` | Fast HTTP-only fetch | `method`, `body`, `follow_redirects`, `retry_policy` |
| `standard` | Headless Chromium | `actions`, `viewport`, `wait_until`, `locale`, ... |
| `stealth` | Anti-blocking browser | everything in standard plus `os_name`, `proxy`, `browser_extensions` |

```python
# Stealth job with structured extraction
job = client.submit(
    job_type="stealth",
    target_url="https://example.com/pricing",
    artifact_options={"include_screenshot": True, "include_extraction": True},
    extraction={
        "hooks": [
            {"hook_id": "price", "type": "css", "selector": ".price", "all_matches": True},
        ]
    },
)
print(job.job_id, "idempotent replay:", job.idempotent_replay)
```

### Waiting vs collecting later

The ScrapeNest API is asynchronous: you submit a job and collect the result once it runs.

- `client.scrape(...)` submits and blocks (polling) until the job reaches a terminal state.
- `client.submit(...)` returns an acknowledgement immediately; collect the result later via
  `client.jobs.get(...)` or a webhook.

Every job creation automatically attaches an `idempotency_token`, so transparent retries never
create duplicate jobs. Pass your own `idempotency_token` to make a call safe to repeat across
processes.

## Async client

```python
import asyncio
from scrapenest import AsyncScrapeNestClient

async def main():
    async with AsyncScrapeNestClient(api_key="sn_live_...") as client:
        result = await client.scrape(job_type="light", target_url="https://example.com")
        print(result.status)

        async for summary in client.jobs.iter(status="succeeded"):
            print(summary.job_id)

asyncio.run(main())
```

The async client mirrors the sync API one-to-one across every resource.

## Listing and paginating jobs

```python
page = client.jobs.list(status="succeeded", limit=50)
print(page.total)

# Or iterate every match, transparently walking pages:
for summary in client.jobs.iter(job_type="stealth"):
    print(summary.job_id)
```

## Job outcome and credits (manifest)

A job's `status` tells you whether it ran (`succeeded`/`failed`). To see whether the target
*blocked* you and what it cost, fetch the forensics manifest:

```python
manifest = client.jobs.get_manifest(job_id)
if manifest:
    print(manifest.outcome)        # "success" | "blocked" | "failed"
    print(manifest.blocked)        # True when the target challenged/denied us
    print(manifest.credits.amount) # credits charged (0 when not charged)
```

## Monitors

A monitor runs a scrape on a cron cadence; every fire mints a normal job. Add a
`detection` block to also get notified when the watched content changes.

```python
monitor = client.monitors.create(
    name="hourly-prices",
    cron="0 * * * *",
    timezone="Europe/Paris",
    job_type="light",
    target_url="https://example.com/pricing",
    # optional: watch for changes and alert by webhook + email
    detection={"enabled": True, "mode": "selector", "selector": ".price",
               "notify": {"email": ["alerts@acme.eu"]}},
)

client.monitors.pause(monitor.id)
client.monitors.resume(monitor.id)

for run in client.monitors.iter_runs(monitor.id):
    print(run.fired_at, run.status, run.job_id)

# When detection is on, review what changed (newest first):
for change in client.monitors.iter_changes(monitor.id):
    print(change.detected_at, change.change_ratio, change.notified_channels)
```

`update()` replaces the whole monitor definition - pass every field you want to keep.

## Recipes (beta)

Recipes are ready-made scrapers for well-known sites (Google results, GitHub
issues, ...) that return JSON validated against a versioned output schema.
`contract` is the schema version you code against; `impl` changes when
ScrapeNest fixes the scraper, never the schema. Only definitive answers are
billed: outcome `ok`, `ok_empty` or `not_found`.

```python
for recipe in client.recipes.list().items:
    print(recipe.slug, recipe.status, recipe.health)

contract = client.recipes.get("github-issues").contracts[0]
print(contract.input_schema)  # JSON Schema of the input

result = client.recipes.run_and_wait("github-issues", {"owner": "cli", "repo": "cli"})
if result.outcome == "ok":
    for issue in result.output["issues"]:
        print(issue["number"], issue["title"])

# Or queue now and collect later (job.completed webhooks carry the result too):
run = client.recipes.run("google-serp", {"q": "best coffee grinder"})
result = client.recipes.result(run.job_id)
```

An input that does not match the contract raises `ValidationError` with field
`details`.

## Webhook endpoints

Register an HTTPS endpoint once and ScrapeNest pushes job events to it - no polling:

```python
endpoint = client.webhook_endpoints.create(
    name="prod-receiver",
    url="https://hooks.your-app.com/scrapenest",
)
print(endpoint.secret)  # signing secret - shown once only, store it now
```

Debug deliveries without leaving Python:

```python
for message in client.webhook_endpoints.iter_messages(endpoint.endpoint_id):
    print(message.event_type, message.status)
    if message.status == "failed":
        attempts = client.webhook_endpoints.attempts(endpoint.endpoint_id, message.message_id)
        for attempt in attempts.items:
            print(f"  HTTP {attempt.status_code} in {attempt.latency_ms}ms: {attempt.response_body}")
```

`rotate_secret()`, `pause()`, `resume()`, `update()`, and `delete()` complete the lifecycle.
Rotation invalidates the old secret immediately - update your receiver first.

### Verifying deliveries

Verify the signature of incoming webhook deliveries before trusting them:

```python
from scrapenest import verify_webhook, WebhookVerificationError

# `payload` is the raw request body (bytes); `headers` carries the svix-* headers.
try:
    event = verify_webhook(payload, headers, secret="whsec_...")
except WebhookVerificationError:
    return 400  # reject
handle(event)
```

See [`examples/webhook_receiver.py`](examples/webhook_receiver.py) for a full FastAPI handler.

## API keys

Provision least-privilege keys per consumer (requires the `api_keys.manage` scope):

```python
created = client.api_keys.create(
    name="ci-pipeline",
    scopes=["jobs.create", "jobs.read", "artifacts.read"],
    allowed_cidrs=["203.0.113.0/24"],
    rate_limit_rpm=60,
)
print(created.token)  # plaintext key - shown once only

client.api_keys.rotate(created.api_key_id)   # old token stops working immediately
client.api_keys.revoke(created.api_key_id, reason="pipeline retired")
```

## Retention and legal holds

Artifacts are purged after your retention window unless a hold protects them
(requires the `retention.manage` scope):

```python
policy = client.retention.get_policy()
print(policy.retention_days, policy.max_retention_days)

hold = client.retention.create_hold(
    scope_type="job",
    scope_ref=job_id,
    justification="Dispute #4242 - preserve evidence",
)
client.retention.release_hold(hold.hold_id, release_notes="Dispute closed")
```

## Organization IP allowlist

Restrict API access to known networks (requires the `org.manage` scope):

```python
client.org.set_ip_allowlist(["203.0.113.0/24", "2001:db8::/32"])
```

The effective allowlist for a key is the org list intersected with any non-empty key-level list.

## Errors

Every non-2xx response raises a typed exception, all subclasses of `ScrapeNestAPIError`:

| Status | Exception |
|--------|-----------|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 422 | `ValidationError` (see `.details`) |
| 429 | `RateLimitError` (see `.retry_after`) |
| 5xx | `ServerError` |

```python
from scrapenest import RateLimitError, ValidationError

try:
    client.submit(job_type="light", target_url="not-a-url")
except ValidationError as exc:
    for problem in exc.details:
        print(problem["field"], problem["message"])
except RateLimitError as exc:
    print("retry after", exc.retry_after, "seconds")
```

Every `ScrapeNestAPIError` carries `request_id` - include it when contacting support.

`429` and `5xx` responses are retried automatically with jittered backoff (honoring `Retry-After`);
configure with `ScrapeNestClient(..., max_retries=2, backoff_factor=0.5)`. Transport failures after
retries raise `ScrapeNestConnectionError`.

## Examples

The [`examples/`](examples/) directory contains runnable end-to-end scripts: quickstart, structured
extraction, browser and stealth jobs, an async crawl, monitors and change detection, webhook endpoint
management, API key hygiene, and retention holds.

## License

MIT. See [LICENSE](LICENSE).
