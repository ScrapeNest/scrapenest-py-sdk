"""Crawl many pages concurrently with the async client.

Target: https://web-scraping.dev/product/{1..N}

Each product page publishes JSON-LD. We fire all the jobs concurrently with the
async client, pull each product's structured data, and assemble a catalog. This
is the pattern for high-throughput ingestion.

    SCRAPENEST_API_KEY=sn_live_... python examples/07_async_crawl.py
"""

from __future__ import annotations

import asyncio
import json

from _common import aread_extraction, make_async_client

PRODUCT_IDS = range(1, 8)
JSONLD = {"hooks": [{"hook_id": "jsonld", "type": "css", "selector": "script[type='application/ld+json']"}]}


async def fetch_product(client, product_id: int) -> dict | None:
    result = await client.scrape(
        job_type="stealth",
        target_url=f"https://web-scraping.dev/product/{product_id}",
        artifact_options={"include_extraction": True},
        extraction=JSONLD,
        timeout=60,
        raise_on_failure=False,
    )
    if result.status != "succeeded":
        return None
    hooks = await aread_extraction(client, result.job_id)
    if not hooks.get("jsonld"):
        return None
    return json.loads(hooks["jsonld"][0])


async def main() -> None:
    async with make_async_client() as client:
        products = await asyncio.gather(*(fetch_product(client, pid) for pid in PRODUCT_IDS))

    catalog = [p for p in products if p]
    print(f"scraped {len(catalog)}/{len(PRODUCT_IDS)} products concurrently\n")
    for product in catalog:
        offers = product.get("offers") or {}
        price = offers.get("price") or offers.get("lowPrice")
        print(f"  {str(price):>6}  {product.get('name')}")


if __name__ == "__main__":
    asyncio.run(main())
