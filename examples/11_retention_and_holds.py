"""Read the artifact retention policy and place a legal hold on a job.

Artifacts are purged after `retention_days`. When you need to keep evidence
past that (a dispute, an audit, litigation), place a hold: held artifacts are
exempt from purges until the hold is released, and both actions are recorded
in the audit log with your justification.

Requires a key with the `retention.manage` scope.

Run: SCRAPENEST_API_KEY=sn_live_... python examples/11_retention_and_holds.py
"""

from _common import make_client


def main() -> None:
    client = make_client()

    policy = client.retention.get_policy()
    print(
        f"artifacts kept {policy.retention_days} days "
        f"(org max {policy.max_retention_days}, policy v{policy.policy_version})"
    )

    # Grab a finished job to put under hold. In practice you would know the
    # job id (from your own records or a dispute ticket).
    page = client.jobs.list(status="succeeded", limit=1)
    if not page.items:
        print("no succeeded jobs to hold; run an example scrape first")
        return
    job_id = page.items[0].job_id

    hold = client.retention.create_hold(
        scope_type="job",
        scope_ref=job_id,
        justification="Example: preserving evidence for dispute #4242",
    )
    print(f"hold {hold.hold_id} on job {job_id} ({hold.status})")

    # Active holds across the org - review these periodically so holds do not
    # outlive their reason.
    for h in client.retention.list_holds().items:
        print(f"  {h.scope_type}:{h.scope_ref or 'org-wide'} since {h.created_at:%Y-%m-%d} [{h.status}]")

    release = client.retention.release_hold(
        hold.hold_id, release_notes="Example finished, dispute closed"
    )
    print(f"released at {release.released_at}")


if __name__ == "__main__":
    main()
