"""Drive a hardened browser for sites with bot detection (Stealth engine).

Target: https://web-scraping.dev/product/1

The Stealth engine runs a fingerprint-hardened browser. Use it for
targets that profile TLS/JS fingerprints or challenge headless browsers. Here we
spoof an OS, run a scripted interaction, capture a screenshot, and read the cost
and final fingerprint back from the job manifest.

    SCRAPENEST_API_KEY=sn_live_... python examples/06_stealth_screenshot.py
"""

from __future__ import annotations

from _common import artifact_of, make_client

URL = "https://web-scraping.dev/product/1"


def main() -> None:
    client = make_client()

    result = client.scrape(
        job_type="stealth",
        target_url=URL,
        os_name="windows",
        actions=[
            {"action": "wait_for_timeout", "timeout_ms": 800},
        ],
        artifact_options={"include_screenshot": True, "include_html": True},
        timeout=120,
    )
    print(f"job {result.job_id}: {result.status}")

    manifest = client.jobs.get_manifest(result.job_id)
    if manifest:
        print(f"  engine:     {manifest.engine}")
        print(f"  outcome:    {manifest.outcome} (blocked={manifest.blocked})")
        print(f"  final_url:  {manifest.final_url}")
        print(f"  user_agent: {manifest.user_agent}")
        print(f"  http:       {manifest.response.http_status if manifest.response else None}")
        if manifest.credits:
            print(f"  credits:    {manifest.credits.amount}")

    shot = artifact_of(client.jobs.get(result.job_id), "screenshot")
    if shot:
        data = client.artifacts.download_bytes(shot.artifact_id)
        with open("product_stealth.png", "wb") as fh:
            fh.write(data)
        print(f"\nsaved screenshot ({len(data)} bytes) -> product_stealth.png")


if __name__ == "__main__":
    main()
