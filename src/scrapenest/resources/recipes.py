from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scrapenest import _ops
from scrapenest.models import Recipe, RecipeListResponse, RecipeResult, RecipeRun

if TYPE_CHECKING:
    from scrapenest._async_client import AsyncScrapeNestClient
    from scrapenest._client import ScrapeNestClient


def _check_timeout(timeout: int) -> None:
    # Imported lazily: the clients import this module.
    from scrapenest._client import _MAX_BLOCKING_TIMEOUT

    if timeout <= 0:
        raise ValueError("timeout must be greater than 0 seconds")
    if timeout > _MAX_BLOCKING_TIMEOUT:
        raise ValueError(
            f"timeout cannot exceed {_MAX_BLOCKING_TIMEOUT} seconds; "
            "use run() and a webhook (job.completed carries the result) for longer runs"
        )


class RecipesResource:
    """Ready-made scrapers for well-known sites (beta).

    A recipe returns JSON validated against a versioned output schema. Only
    definitive answers are billed (outcome ``ok``, ``ok_empty``, ``not_found``).

    Example::

        result = client.recipes.run_and_wait("github-issues", {"owner": "cli", "repo": "cli"})
        for issue in result.output["issues"]:
            print(issue["number"], issue["title"])
    """

    def __init__(self, client: ScrapeNestClient) -> None:
        self._client = client

    def list(self) -> RecipeListResponse:
        """The recipe catalog with status, health and pricing."""
        return self._client._execute(_ops.list_recipes())

    def get(self, slug: str) -> Recipe:
        """One recipe with its contracts: input/output JSON Schemas, examples, cost."""
        return self._client._execute(_ops.get_recipe(slug))

    def run(
        self,
        slug: str,
        input: dict[str, Any],
        *,
        contract: int | None = None,
        idempotency_token: str | None = None,
    ) -> RecipeRun:
        """Queue a run and return immediately (the job id is in the result).

        Raises ``ValidationError`` (422) with field ``details`` when ``input``
        does not match the contract's input schema.
        """
        return self._client._execute(_ops.run_recipe(slug, input, contract, idempotency_token))

    def result(self, job_id: str) -> RecipeResult:
        """The structured result of a finished recipe job (409 while running)."""
        return self._client._execute(_ops.get_recipe_result(job_id))

    def run_and_wait(
        self,
        slug: str,
        input: dict[str, Any],
        *,
        contract: int | None = None,
        idempotency_token: str | None = None,
        timeout: int = 60,
    ) -> RecipeResult:
        """Run a recipe and block (polling) until its result is available.

        The run continues server-side on timeout; ``ScrapeJobTimeout`` carries
        its job id, so ``result(job_id)`` can collect it later.
        """
        _check_timeout(timeout)
        run = self.run(slug, input, contract=contract, idempotency_token=idempotency_token)
        self._client._await_via_poll(run.job_id, timeout)
        return self.result(run.job_id)


class AsyncRecipesResource:
    """Async variant of :class:`RecipesResource`."""

    def __init__(self, client: AsyncScrapeNestClient) -> None:
        self._client = client

    async def list(self) -> RecipeListResponse:
        return await self._client._execute(_ops.list_recipes())

    async def get(self, slug: str) -> Recipe:
        return await self._client._execute(_ops.get_recipe(slug))

    async def run(
        self,
        slug: str,
        input: dict[str, Any],
        *,
        contract: int | None = None,
        idempotency_token: str | None = None,
    ) -> RecipeRun:
        return await self._client._execute(_ops.run_recipe(slug, input, contract, idempotency_token))

    async def result(self, job_id: str) -> RecipeResult:
        return await self._client._execute(_ops.get_recipe_result(job_id))

    async def run_and_wait(
        self,
        slug: str,
        input: dict[str, Any],
        *,
        contract: int | None = None,
        idempotency_token: str | None = None,
        timeout: int = 60,
    ) -> RecipeResult:
        _check_timeout(timeout)
        run = await self.run(slug, input, contract=contract, idempotency_token=idempotency_token)
        await self._client._await_via_poll(run.job_id, timeout)
        return await self.result(run.job_id)
