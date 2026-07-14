# Contributing

Thanks for your interest in improving the ScrapeNest Python SDK.

## Scope

This repository contains the client SDK only. Server-side behavior (API validation,
job execution, billing) is not changed here; if you hit an API bug, open an issue
with the `request_id` from the error and we will route it internally.

## Development setup

```bash
git clone https://github.com/scrapenest/scrapenest-py-sdk
cd scrapenest-py-sdk
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

All three gates must pass; CI enforces them on Python 3.10 through 3.13:

```bash
ruff check src tests examples
mypy
pytest
```

Guidelines:

- Keep the sync and async clients symmetrical. Endpoint definitions live once in
  `src/scrapenest/_ops.py`; the resource classes in `src/scrapenest/resources/` are
  thin typed wrappers over them. If you add an endpoint, add it there, wire it into
  both resource classes, and cover it in `tests/`.
- No new runtime dependencies without prior discussion in an issue - httpx is the
  only one, deliberately.
- Every public method needs a test that asserts both the request it sends (method,
  path, body) and the parsing of a realistic response.
- Public behavior changes need a `CHANGELOG.md` entry under Unreleased.

## Reporting security issues

Do not open public issues for vulnerabilities - see [SECURITY.md](SECURITY.md).
