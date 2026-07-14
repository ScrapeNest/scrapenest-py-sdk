"""Provision a least-privilege API key for a CI pipeline, then rotate it.

Good hygiene for machine credentials: give each consumer its own key, scope it
to the operations it actually performs, pin it to known egress IPs, and rotate
on a calendar (or immediately after a suspected leak).

Requires a key with the `api_keys.manage` scope.

Run: SCRAPENEST_API_KEY=sn_live_... python examples/10_api_key_hygiene.py
"""

from _common import make_client


def main() -> None:
    client = make_client()

    # A key for a CI pipeline that submits jobs and fetches results - nothing
    # else. It cannot manage keys, webhooks, or org settings.
    created = client.api_keys.create(
        name="ci-nightly-crawl",
        description="Nightly product crawl, runs from CI",
        scopes=["jobs.create", "jobs.read", "artifacts.read"],
        allowed_cidrs=["203.0.113.0/24"],  # your CI egress range
        rate_limit_rpm=60,
    )
    # The token is shown exactly once - pipe it straight into your secret store.
    print(f"created {created.name}: {created.token[:16]}... (scopes: {', '.join(created.scopes)})")

    # Audit what exists. Prefixes let you match keys against config without
    # ever seeing a full token again.
    for key in client.api_keys.list():
        last_used = key.last_used_at or "never"
        print(f"  {key.prefix} {key.name} [{key.status}] last used: {last_used}")

    # Rotation invalidates the old token immediately (no overlap window):
    # deploy the new token to the consumer right away.
    rotation = client.api_keys.rotate(created.api_key_id)
    print(f"rotated: new prefix {rotation.prefix}")

    # Decommission when the pipeline is retired. The reason lands in the
    # org audit log.
    client.api_keys.revoke(created.api_key_id, reason="example cleanup")
    print("revoked")


if __name__ == "__main__":
    main()
