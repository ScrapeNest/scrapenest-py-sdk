"""Build a CSV dataset from a data-dense page.

Target: https://www.scrapethissite.com/pages/simple/ (250 countries, one page).

A single Light job plus four column hooks gives us aligned columns we zip into
rows and write to CSV. Note: each extraction hook returns up to 50 values, so
this writes the first 50 countries - for larger sets, crawl paginated listings
(see 02_extract_listing.py) and append.

    SCRAPENEST_API_KEY=sn_live_... python examples/04_dataset_to_csv.py countries.csv
"""

from __future__ import annotations

import csv
import sys

from _common import make_client, read_extraction

URL = "https://www.scrapethissite.com/pages/simple/"


def main(out_path: str) -> None:
    client = make_client()

    result = client.scrape(
        job_type="light",
        target_url=URL,
        artifact_options={"include_extraction": True},
        extraction={
            "hooks": [
                {"hook_id": "name", "type": "css", "selector": ".country .country-name", "all_matches": True},
                {"hook_id": "capital", "type": "css", "selector": ".country .country-capital", "all_matches": True},
                {"hook_id": "population", "type": "css", "selector": ".country .country-population", "all_matches": True},
                {"hook_id": "area", "type": "css", "selector": ".country .country-area", "all_matches": True},
            ]
        },
        timeout=60,
    )
    print(f"job {result.job_id}: {result.status}")

    h = read_extraction(client, result.job_id)
    rows = list(zip(h.get("name", []), h.get("capital", []), h.get("population", []), h.get("area", []), strict=False))

    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "capital", "population", "area_km2"])
        for name, capital, population, area in rows:
            writer.writerow([name.strip(), capital.strip(), population.strip(), area.strip()])

    print(f"wrote {len(rows)} rows to {out_path}")
    for name, capital, *_ in rows[:5]:
        print(f"  {name.strip()} - capital {capital.strip()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "countries.csv")
