"""Create and manage a monitor (a recurring scrape on a schedule).

Each time the monitor fires, ScrapeNest creates a normal job that bills as
usual. A run skipped because you are out of credits costs nothing and shows up
in the run history as "skipped_quota". Add a ``detection`` block (see example
09) to also get notified when the page changes.

Run: SCRAPENEST_API_KEY=sn_live_... python examples/08_monitor.py
"""

from _common import make_client


def main() -> None:
    client = make_client()

    # Hourly, on the hour, in Paris time. Frequency and engine are constrained
    # by your plan (see the pricing page).
    monitor = client.monitors.create(
        name="hourly-homepage",
        cron="0 * * * *",
        timezone="Europe/Paris",
        job_type="light",
        target_url="https://example.com",
    )
    print(f"created monitor {monitor.id} ({monitor.status}), next run {monitor.next_run_at}")

    # List your monitors.
    for m in client.monitors.iter():
        print(f"  - {m.name}: {m.cron} [{m.timezone}] -> {m.job_type} ({m.status})")

    # Pause / resume without deleting.
    client.monitors.pause(monitor.id)
    client.monitors.resume(monitor.id)

    # Inspect the run history (each fire, and whether it minted a job or skipped).
    runs = client.monitors.runs(monitor.id, limit=10)
    for run in runs.items:
        target = run.job_id or "-"
        print(f"  run {run.fired_at}: {run.status} (job={target})")

    # Clean up.
    client.monitors.delete(monitor.id)
    print("deleted monitor")


if __name__ == "__main__":
    main()
