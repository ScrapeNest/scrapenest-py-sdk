"""Typed request shapes mirroring the OpenAPI job-create bodies.

These are `TypedDict`s (not pydantic models) so the SDK stays dependency-light
while still giving editors autocomplete and type-checkers something to verify.
All validation remains authoritative server-side. Every TypedDict is `total=False`
except where the API requires a field; pass them as keyword arguments to
`client.jobs.create(...)`.
"""

from __future__ import annotations

import sys
from typing import Literal

if sys.version_info >= (3, 11):
    from typing import NotRequired, TypedDict, Unpack
else:  # pragma: no cover
    from typing_extensions import NotRequired, TypedDict, Unpack

__all__ = [
    "Unpack",
    "JobType",
    "HttpMethod",
    "WaitUntil",
    "BrowserEngine",
    "OsName",
    "BrowserExtension",
    "CssExtractionHook",
    "RegexExtractionHook",
    "JsonPathExtractionHook",
    "ExtractionHook",
    "JobExtraction",
    "ClickAction",
    "FillAction",
    "WaitForSelectorAction",
    "WaitForTimeoutAction",
    "EvaluateAction",
    "ScreenshotAction",
    "NavigateAction",
    "JobAction",
    "JobArtifactOptions",
    "JobViewport",
    "JobRetryPolicy",
    "JobProxy",
    "LightJobCreate",
    "StandardJobCreate",
    "StealthJobCreate",
]

JobType = Literal["light", "standard", "stealth"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
WaitUntil = Literal["load", "domcontentloaded", "networkidle", "commit"]
BrowserEngine = Literal["chromium", "stealth"]
OsName = Literal["windows", "macos", "linux"]
BrowserExtension = Literal["ublock", "isdcac"]


# --- Extraction hooks ---------------------------------------------------------

class CssExtractionHook(TypedDict):
    hook_id: str
    type: Literal["css"]
    selector: str
    attribute: NotRequired[str | None]
    all_matches: NotRequired[bool]
    timeout_ms: NotRequired[int]


class RegexExtractionHook(TypedDict):
    hook_id: str
    type: Literal["regex"]
    pattern: str
    flags: NotRequired[str | None]
    group: NotRequired[int]
    all_matches: NotRequired[bool]
    timeout_ms: NotRequired[int]


class JsonPathExtractionHook(TypedDict):
    hook_id: str
    type: Literal["jsonpath"]
    path: str
    all_matches: NotRequired[bool]
    timeout_ms: NotRequired[int]


ExtractionHook = CssExtractionHook | RegexExtractionHook | JsonPathExtractionHook


class JobExtraction(TypedDict):
    hooks: list[ExtractionHook]


# --- Browser actions ----------------------------------------------------------

class ClickAction(TypedDict):
    action: Literal["click"]
    selector: str
    timeout_ms: NotRequired[int]


class FillAction(TypedDict):
    action: Literal["fill"]
    selector: str
    value: str
    timeout_ms: NotRequired[int]


class WaitForSelectorAction(TypedDict):
    action: Literal["wait_for_selector"]
    selector: str
    timeout_ms: NotRequired[int]


class WaitForTimeoutAction(TypedDict):
    action: Literal["wait_for_timeout"]
    timeout_ms: int


class EvaluateAction(TypedDict):
    action: Literal["evaluate"]
    script: str


class ScreenshotAction(TypedDict):
    action: Literal["screenshot"]
    selector: NotRequired[str | None]
    full_page: NotRequired[bool]
    filename: NotRequired[str]


class NavigateAction(TypedDict):
    action: Literal["navigate"]
    url: str
    wait_until: NotRequired[WaitUntil]


JobAction = (
    ClickAction
    | FillAction
    | WaitForSelectorAction
    | WaitForTimeoutAction
    | EvaluateAction
    | ScreenshotAction
    | NavigateAction
)


# --- Shared job options -------------------------------------------------------

class JobArtifactOptions(TypedDict, total=False):
    include_html: bool
    include_response_body: bool
    include_extraction: bool
    include_screenshot: bool
    include_har: bool
    include_console: bool
    block_images: bool
    block_stylesheets: bool
    block_media: bool
    block_fonts: bool
    no_scroll: bool


class JobViewport(TypedDict):
    width: int
    height: int


class JobRetryPolicy(TypedDict):
    max_attempts: int
    retry_on_status: NotRequired[list[int]]
    retry_methods: NotRequired[list[HttpMethod]]


class JobProxy(TypedDict):
    server: str
    bypass: NotRequired[str | None]
    username: NotRequired[str | None]
    password: NotRequired[str | None]


# --- Per-tier create bodies (used by jobs.create overloads) -------------------

class _JobCommonFields(TypedDict):
    target_url: str
    timeout_ms: NotRequired[int]
    tags: NotRequired[list[str]]
    idempotency_token: NotRequired[str]
    headers: NotRequired[dict[str, str]]
    user_agent: NotRequired[str]
    artifact_options: NotRequired[JobArtifactOptions]
    extraction: NotRequired[JobExtraction]


class _BrowserFields(TypedDict, total=False):
    headless: bool
    browser: BrowserEngine
    wait_until: WaitUntil
    navigation_timeout_ms: int
    viewport: JobViewport
    locale: str
    timezone_id: str
    actions: list[JobAction]


class LightJobCreate(_JobCommonFields):
    """HTTP-only job (Light tier)."""

    job_type: Literal["light"]
    method: NotRequired[HttpMethod]
    body: NotRequired[str]
    follow_redirects: NotRequired[bool]
    retry_policy: NotRequired[JobRetryPolicy]


class StandardJobCreate(_JobCommonFields, _BrowserFields):
    """Headless-browser job (Standard tier)."""

    job_type: Literal["standard"]


class StealthJobCreate(_JobCommonFields, _BrowserFields):
    """Anti-blocking browser job (Stealth tier)."""

    job_type: Literal["stealth"]
    os_name: NotRequired[OsName]
    browser_extensions: NotRequired[list[BrowserExtension]]
    proxy: NotRequired[JobProxy]
