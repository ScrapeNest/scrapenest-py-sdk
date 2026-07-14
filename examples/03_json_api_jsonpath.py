"""Scrape a JSON API and pull fields with JSONPath hooks.

Target: scrapethissite.com's AJAX films endpoint, which returns a JSON array:
    https://www.scrapethissite.com/pages/ajax-javascript/?ajax=true&year=2015

When the response body is JSON, `jsonpath` hooks run straight against it - no
HTML parsing involved. Great for internal/XHR endpoints you discover in the
network tab.

    SCRAPENEST_API_KEY=sn_live_... python examples/03_json_api_jsonpath.py
"""

from __future__ import annotations

from _common import make_client, read_extraction

API = "https://www.scrapethissite.com/pages/ajax-javascript/?ajax=true&year=2015"


def main() -> None:
    client = make_client()

    result = client.scrape(
        job_type="light",
        target_url=API,
        artifact_options={"include_extraction": True, "include_response_body": True},
        extraction={
            "hooks": [
                {"hook_id": "titles", "type": "jsonpath", "path": "$[*].title"},
                {"hook_id": "awards", "type": "jsonpath", "path": "$[*].awards"},
                {"hook_id": "nominations", "type": "jsonpath", "path": "$[*].nominations"},
            ]
        },
        timeout=60,
    )
    print(f"job {result.job_id}: {result.status}")

    hooks = read_extraction(client, result.job_id)
    titles = hooks.get("titles", [])
    awards = hooks.get("awards", [])

    print(f"\n{len(titles)} films from 2015, ranked by awards:")
    for title, count in sorted(zip(titles, awards, strict=False), key=lambda t: -(t[1] or 0)):
        print(f"  {count:>2} awards  {title.strip()}")


if __name__ == "__main__":
    main()
