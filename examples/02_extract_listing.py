"""Turn a product listing into structured records with the Light engine.

Target: https://web-scraping.dev/products (paginated, 5 products per page).

One Light job per page, a handful of CSS hooks, and we zip the per-hook columns
into clean rows. No browser needed - the listing is server-rendered HTML.

    SCRAPENEST_API_KEY=sn_live_... python examples/02_extract_listing.py
"""

from __future__ import annotations

from dataclasses import dataclass

from _common import make_client, read_extraction

LISTING = "https://web-scraping.dev/products"
PAGES = 3


@dataclass
class Product:
    name: str
    price: str
    url: str
    blurb: str


def scrape_page(client, page: int) -> list[Product]:
    result = client.scrape(
        job_type="light",
        target_url=f"{LISTING}?page={page}",
        tags=[f"listing:page-{page}"],
        artifact_options={"include_extraction": True},
        extraction={
            "hooks": [
                {"hook_id": "name", "type": "css", "selector": ".product .description h3 a", "all_matches": True},
                {"hook_id": "url", "type": "css", "selector": ".product .description h3 a",
                 "attribute": "href", "all_matches": True},
                {"hook_id": "price", "type": "css", "selector": ".product .price", "all_matches": True},
                {"hook_id": "blurb", "type": "css", "selector": ".product .short-description", "all_matches": True},
            ]
        },
        timeout=60,
    )
    h = read_extraction(client, result.job_id)
    rows = zip(h.get("name", []), h.get("price", []), h.get("url", []), h.get("blurb", []), strict=False)
    return [Product(n, p, u, b) for n, p, u, b in rows]


def main() -> None:
    client = make_client()
    catalog: list[Product] = []
    for page in range(1, PAGES + 1):
        page_rows = scrape_page(client, page)
        print(f"page {page}: {len(page_rows)} products")
        catalog.extend(page_rows)

    print(f"\n{len(catalog)} products total\n")
    for product in catalog:
        print(f"  {product.price:>8}  {product.name}")
        print(f"            {product.url}")


if __name__ == "__main__":
    main()
