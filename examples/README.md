# ScrapeNest SDK examples

Runnable, end-to-end examples. The scraping ones target two public practice
sandboxes so you can run them without picking a victim:

- [web-scraping.dev](https://web-scraping.dev) - products, reviews, infinite
  scroll, hidden JSON (by ScrapFly).
- [scrapethissite.com](https://www.scrapethissite.com/pages/) - countries, films
  AJAX API, paginated tables.

## Setup

```bash
pip install scrapenest-sdk
export SCRAPENEST_API_KEY=sn_live_...
# Optional, to run against a local/self-signed stack:
# export SCRAPENEST_BASE_URL=https://api.scrapenest.localhost
# export SCRAPENEST_VERIFY_TLS=0
python examples/01_quickstart_product.py
```

All examples read configuration from the environment via `_common.py`, so the
same code runs against production or a local stack unchanged.

## Index

### Scraping

| File | Engine | Demonstrates |
|------|--------|--------------|
| `01_quickstart_product.py` | light | Read a page's own JSON-LD + JSON blobs; features; credits |
| `02_extract_listing.py` | light | CSS hooks -> structured rows; walk paginated listings |
| `03_json_api_jsonpath.py` | light | JSONPath hooks against a JSON API response |
| `04_dataset_to_csv.py` | light | Aligned column hooks -> a CSV dataset |
| `05_browser_infinite_scroll.py` | standard | JS rendering + auto-scroll; full-page screenshot |
| `06_stealth_screenshot.py` | stealth | Hardened browser, OS spoof, scripted actions, manifest |
| `07_async_crawl.py` | async | Concurrent crawl of many pages into a catalog |

### Automation and account management

| File | Demonstrates |
|------|--------------|
| `08_monitor.py` | Monitors: recurring cron scrapes; run history; pause/resume |
| `09_change_detection.py` | Watch a page for changes; detection block, modes, review detected changes |
| `09_webhook_endpoints.py` | Register webhook endpoints; inspect deliveries and failed attempts; rotate secrets |
| `10_api_key_hygiene.py` | Least-privilege API keys: scopes, IP allowlists, rotation, revocation |
| `11_retention_and_holds.py` | Read the retention policy; place and release a legal hold |
| `webhook_receiver.py` | Verify webhook signatures in a FastAPI endpoint |

## Picking an engine

- **light** - HTTP only (curl-impersonate). Fastest and cheapest. Use it for
  server-rendered HTML and JSON APIs. Most of these examples use it.
- **standard** - headless Chromium. Use it when content is rendered by
  JavaScript or appears on scroll/click.
- **stealth** - fingerprint-hardened browser. Use it for targets with
  active bot detection.
