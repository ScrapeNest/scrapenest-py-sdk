from __future__ import annotations

import json
from datetime import datetime

import httpx
import pytest

from conftest import async_client, sync_client
from scrapenest import ScrapeJobTimeout, ValidationError

SUMMARY = {
    "slug": "github-issues",
    "title": "GitHub repository issues",
    "description": "Issues of a public GitHub repository.",
    "category": "code_hosting",
    "status": "beta",
    "available": True,
    "health": "operational",
    "billing_unit": "page",
    "credit_multiplier": 1,
    "contracts": [1],
}
DETAIL = {
    **SUMMARY,
    "contracts": [
        {
            "contract": 1,
            "input_schema": {"type": "object", "required": ["owner", "repo"]},
            "output_schema": {"type": "object", "required": ["issues"]},
            "example_input": {"owner": "cli", "repo": "cli"},
            "example_output": None,
            "deprecated_at": None,
            "sunset_at": None,
            "engine": "light",
            "credits_per_unit": 1,
        }
    ],
}
RUN = {
    "job_id": "job-1",
    "status": "queued",
    "created_at": "2026-10-09T08:00:00+00:00",
    "recipe": {"slug": "github-issues", "contract": 1, "impl": 3},
}
RESULT = {
    "job_id": "job-1",
    "status": "succeeded",
    "recipe": {"slug": "github-issues", "contract": 1, "impl": 3, "outcome": "ok"},
    "captured_at": "2026-10-09T08:00:05+00:00",
    "output": {"issues": [{"number": 1, "title": "Bug"}], "pages_fetched": 1},
}


def job(status: str) -> dict:
    return {
        "job_id": "job-1",
        "job_type": "light",
        "status": status,
        "target_url": "https://api.github.com/repos/cli/cli/issues",
        "tags": [],
        "created_at": "2026-10-09T08:00:00+00:00",
        "completed_at": "2026-10-09T08:00:05+00:00" if status == "succeeded" else None,
        "failure_reason": None,
        "artifact_ids": [],
        "artifacts": [],
    }


def router(seen: list[httpx.Request], statuses: list[str] | None = None):
    states = list(statuses or ["succeeded"])

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/v1/recipes":
            return httpx.Response(200, json={"items": [SUMMARY], "total": 1})
        if path == "/v1/recipes/github-issues":
            return httpx.Response(200, json=DETAIL)
        if path == "/v1/recipes/github-issues/runs":
            return httpx.Response(201, json=RUN)
        if path == "/v1/jobs/job-1":
            return httpx.Response(200, json=job(states.pop(0) if len(states) > 1 else states[0]))
        if path == "/v1/jobs/job-1/result":
            return httpx.Response(200, json=RESULT)
        return httpx.Response(404, json={"error": {"code": "recipe_not_found", "message": "not found"}})

    return handler


def test_list_and_get_parse_the_catalog() -> None:
    client = sync_client(router([]))

    catalog = client.recipes.list()
    assert catalog.total == 1
    assert catalog.items[0].health == "operational"
    assert catalog.items[0].contracts == [1]

    recipe = client.recipes.get("github-issues")
    contract = recipe.contracts[0]
    assert contract.input_schema["required"] == ["owner", "repo"]
    assert contract.engine == "light" and contract.credits_per_unit == 1


def test_run_sends_only_the_given_fields() -> None:
    seen: list[httpx.Request] = []
    client = sync_client(router(seen))

    run = client.recipes.run(
        "github-issues", {"owner": "cli", "repo": "cli"}, idempotency_token="tok-12345678"
    )

    assert json.loads(seen[0].content) == {
        "input": {"owner": "cli", "repo": "cli"},
        "idempotency_token": "tok-12345678",
    }
    assert run.job_id == "job-1" and run.recipe.impl == 3
    assert run.created_at == datetime.fromisoformat("2026-10-09T08:00:00+00:00")


def test_result_exposes_outcome_and_billing() -> None:
    result = sync_client(router([])).recipes.result("job-1")

    assert result.outcome == "ok" and result.billed is True
    assert result.recipe.slug == "github-issues"
    assert result.output == {"issues": [{"number": 1, "title": "Bug"}], "pages_fetched": 1}


def test_run_and_wait_polls_then_fetches_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapenest._client.time.sleep", lambda _: None)
    seen: list[httpx.Request] = []
    client = sync_client(router(seen, ["queued", "running", "succeeded"]))

    result = client.recipes.run_and_wait("github-issues", {"owner": "cli", "repo": "cli"})

    assert result.outcome == "ok"
    paths = [r.url.path for r in seen]
    assert paths == [
        "/v1/recipes/github-issues/runs",
        "/v1/jobs/job-1",
        "/v1/jobs/job-1",
        "/v1/jobs/job-1",
        "/v1/jobs/job-1/result",
    ]


def test_run_and_wait_times_out_with_the_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr("scrapenest._client.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("scrapenest._client.time.sleep", lambda _: None)

    with pytest.raises(ScrapeJobTimeout) as err:
        sync_client(router([], ["running"])).recipes.run_and_wait(
            "github-issues", {"owner": "cli", "repo": "cli"}, timeout=30
        )
    assert err.value.job_id == "job-1"


@pytest.mark.parametrize("timeout", [0, 121])
def test_run_and_wait_rejects_out_of_range_timeouts(timeout: int) -> None:
    with pytest.raises(ValueError):
        sync_client(router([])).recipes.run_and_wait("github-issues", {}, timeout=timeout)


def test_invalid_input_raises_validation_error_with_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "error": {
                    "code": "invalid_recipe_input",
                    "message": "Input does not match.",
                    "details": [{"field": "repo", "message": "required"}],
                }
            },
        )

    with pytest.raises(ValidationError) as err:
        sync_client(handler).recipes.run("github-issues", {"owner": "cli"})
    assert err.value.details == [{"field": "repo", "message": "required"}]


async def test_async_run_and_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("scrapenest._async_client.asyncio.sleep", no_sleep)
    client = async_client(router([], ["running", "succeeded"]))

    catalog = await client.recipes.list()
    result = await client.recipes.run_and_wait("github-issues", {"owner": "cli", "repo": "cli"})

    assert catalog.items[0].slug == "github-issues"
    assert result.billed and result.output is not None
