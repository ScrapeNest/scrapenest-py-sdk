"""Render a JavaScript page that lazy-loads on scroll (Standard engine).

Target: https://web-scraping.dev/testimonials (testimonials appear as you scroll).

A plain HTTP fetch only sees the testimonials in the initial HTML. The Standard
(headless Chromium) engine auto-scrolls the page, so the lazy-loaded items render
before we extract - the count jumps. We also grab a full-page screenshot.

    SCRAPENEST_API_KEY=sn_live_... python examples/05_browser_infinite_scroll.py
"""

from __future__ import annotations

from _common import artifact_of, make_client, read_extraction

URL = "https://web-scraping.dev/testimonials"
HOOKS = {"hooks": [{"hook_id": "items", "type": "css", "selector": ".testimonial", "all_matches": True}]}


def count_testimonials(client, engine: str, **opts) -> tuple[str, int]:
    result = client.scrape(
        job_type=engine,
        target_url=URL,
        artifact_options={"include_extraction": True, **opts.pop("artifact_options", {})},
        extraction=HOOKS,
        timeout=115,
        **opts,
    )
    return result.job_id, len(read_extraction(client, result.job_id).get("items", []))


def main() -> None:
    client = make_client()

    # 1. HTTP-only: sees just the server-rendered testimonials.
    _, light_count = count_testimonials(client, "light")
    print(f"light  (no JS):       {light_count} testimonials")

    # 2. Headless browser: auto-scrolls, lazy content renders, screenshot captured.
    job_id, std_count = count_testimonials(
        client, "standard", artifact_options={"include_screenshot": True}
    )
    print(f"standard (rendered):  {std_count} testimonials")
    print(f"\nThe browser engine surfaced {std_count - light_count} extra items that")
    print("were not in the initial HTML.")

    shot = artifact_of(client.jobs.get(job_id), "screenshot")
    if shot:
        data = client.artifacts.download_bytes(shot.artifact_id)
        with open("testimonials.png", "wb") as fh:
            fh.write(data)
        print(f"\nsaved full-page screenshot ({len(data)} bytes) -> testimonials.png")


if __name__ == "__main__":
    main()
