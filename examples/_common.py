"""Shared helpers for the examples.

Every example reads configuration from the environment so the same code runs
against production or a local stack without edits:

    SCRAPENEST_API_KEY     required; your API key (sn_live_...)
    SCRAPENEST_BASE_URL    optional; defaults to https://api.scrapenest.com
    SCRAPENEST_VERIFY_TLS  optional; set to "0" to disable TLS verification
                           (useful against a local self-signed stack)
"""

from __future__ import annotations

import os

from scrapenest import Artifact, AsyncScrapeNestClient, Job, ScrapeNestClient


def _config() -> tuple[str, str, bool]:
    api_key = os.environ.get("SCRAPENEST_API_KEY")
    if not api_key:
        raise SystemExit("Set SCRAPENEST_API_KEY to run this example.")
    base_url = os.environ.get("SCRAPENEST_BASE_URL", "https://api.scrapenest.com")
    verify = os.environ.get("SCRAPENEST_VERIFY_TLS", "1") != "0"
    return api_key, base_url, verify


def make_client() -> ScrapeNestClient:
    api_key, base_url, verify = _config()
    return ScrapeNestClient(api_key=api_key, base_url=base_url, verify=verify)


def make_async_client() -> AsyncScrapeNestClient:
    api_key, base_url, verify = _config()
    return AsyncScrapeNestClient(api_key=api_key, base_url=base_url, verify=verify)


def artifact_of(job: Job, artifact_type: str) -> Artifact | None:
    return next((a for a in job.artifacts if a.artifact_type == artifact_type), None)


def _extraction_map(payload: dict) -> dict[str, list]:
    """Flatten an `extraction` artifact into {hook_id: [values...]}."""
    out: dict[str, list] = {}
    for hook in payload.get("hooks", []):
        out[hook["hook_id"]] = hook.get("result") or []
    return out


def read_extraction(client: ScrapeNestClient, job_id: str) -> dict[str, list]:
    job = client.jobs.get(job_id)
    art = artifact_of(job, "extraction")
    if not art:
        return {}
    import json

    return _extraction_map(json.loads(client.artifacts.download_text(art.artifact_id)))


async def aread_extraction(client: AsyncScrapeNestClient, job_id: str) -> dict[str, list]:
    job = await client.jobs.get(job_id)
    art = artifact_of(job, "extraction")
    if not art:
        return {}
    import json

    return _extraction_map(json.loads(await client.artifacts.download_text(art.artifact_id)))
