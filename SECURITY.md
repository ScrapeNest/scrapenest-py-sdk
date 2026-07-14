# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities in this SDK or the ScrapeNest platform to
**security@scrapenest.com**. Do not open a public GitHub issue for security reports.

Include what you can: affected version, reproduction steps, and impact assessment.
We acknowledge reports within 2 business days and keep you informed while we
investigate and remediate.

## Supported versions

Only the latest released version of `scrapenest-sdk` receives security fixes.

## Scope notes for this SDK

- API keys are only ever sent in the `X-API-Key` header over HTTPS; the SDK never
  logs or persists them.
- `verify_webhook()` implements constant-time signature comparison and enforces a
  replay-protection timestamp window (default 5 minutes).
- TLS verification is on by default; `verify=False` is intended for local
  development stacks only.
