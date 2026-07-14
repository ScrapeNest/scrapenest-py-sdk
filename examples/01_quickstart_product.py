"""Quickstart: scrape a product page and read its structured data.

Target: https://web-scraping.dev/product/1 (a ScrapFly practice site).

The best structured data is the one the site already publishes. This product
page embeds a JSON-LD block and a JSON reviews blob. We pull both with a single
Light (HTTP-only) job and one extraction pass, then read them as plain dicts.

    SCRAPENEST_API_KEY=sn_live_... python examples/01_quickstart_product.py
"""

from __future__ import annotations

import json

from _common import make_client, read_extraction

PRODUCT_URL = "https://web-scraping.dev/product/1"


def main() -> None:
    client = make_client()

    result = client.scrape(
        job_type="light",
        target_url=PRODUCT_URL,
        artifact_options={"include_extraction": True},
        extraction={
            "hooks": [
                # Grab the raw text of the documents the page already publishes.
                {"hook_id": "jsonld", "type": "css", "selector": "script[type='application/ld+json']"},
                {"hook_id": "reviews", "type": "css", "selector": "#reviews-data"},
                # And a couple of human-readable feature rows for good measure.
                {"hook_id": "features", "type": "css", "selector": ".feature-label", "all_matches": True},
                {"hook_id": "values", "type": "css", "selector": ".feature-value", "all_matches": True},
            ]
        },
        timeout=60,
    )
    print(f"job {result.job_id}: {result.status}")

    hooks = read_extraction(client, result.job_id)
    product = json.loads(hooks["jsonld"][0])
    offers = product.get("offers") or {}

    print("\nProduct")
    print(f"  name:  {product.get('name')}")
    print(f"  brand: {(product.get('brand') or {}).get('name')}")
    print(f"  price: {offers.get('lowPrice')} - {offers.get('highPrice')} {offers.get('priceCurrency')}")
    rating = product.get("aggregateRating") or {}
    print(f"  rating: {rating.get('ratingValue')} ({rating.get('reviewCount')} reviews)")

    print("\nFeatures")
    for label, value in zip(hooks.get("features", []), hooks.get("values", []), strict=False):
        print(f"  {label}: {value}")

    reviews = json.loads(hooks["reviews"][0]) if hooks.get("reviews") else []
    print(f"\nReviews JSON blob: {len(reviews)} entries")
    for review in reviews[:3]:
        print(f"  {review.get('rating')}* - {str(review.get('text', ''))[:70]}")

    manifest = client.jobs.get_manifest(result.job_id)
    if manifest and manifest.credits:
        print(f"\nCredits charged: {manifest.credits.amount} (engine={manifest.engine})")


if __name__ == "__main__":
    main()
