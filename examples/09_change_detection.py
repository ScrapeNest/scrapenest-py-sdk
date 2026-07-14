"""Watch a web page for changes (change detection).

Attach a ``detection`` block to a monitor and ScrapeNest fingerprints every run,
compares it to the previous version, and notifies you (webhook + email) when the
watched content changes - with a before/after diff. Availability, modes, and the
number of monitors are set by your plan.

Run: SCRAPENEST_API_KEY=sn_live_... python examples/09_change_detection.py
"""

from _common import make_client


def main() -> None:
    client = make_client()

    # Watch only the price element; ignore rotating ads/timestamps. Alert by
    # webhook and email, but only for changes above 5% of the watched content.
    monitor = client.monitors.create(
        name="competitor-pricing",
        cron="0 * * * *",
        job_type="standard",
        target_url="https://competitor.example/pricing",
        detection={
            "enabled": True,
            "mode": "selector",            # or "text" for the whole page
            "selector": ".price, #stock",
            "ignore_selectors": [".ads", "time"],
            "min_change_ratio": 0.05,
            "consecutive": 1,              # alert after N consecutive changed runs
            "cooldown_seconds": 0,         # suppress repeat alerts within N seconds
            "notify": {"webhook": True, "email": ["alerts@acme.eu"]},
        },
    )
    print("created:", monitor.id)
    print("detection:", monitor.detection)       # config + health (status / last_checked_at)

    # Review detected changes (newest first).
    for change in client.monitors.iter_changes(monitor.id):
        pct = f"{change.change_ratio * 100:.1f}%" if change.change_ratio is not None else "n/a"
        print(f"  {change.detected_at}  changed {pct}  notified={change.notified_channels}")

    # Turn detection off (leave the monitor itself running as a plain re-scrape):
    client.monitors.update(
        monitor.id,
        name="competitor-pricing",
        cron="0 * * * *",
        job_type="standard",
        target_url="https://competitor.example/pricing",
        detection={"enabled": False},
    )


if __name__ == "__main__":
    main()
