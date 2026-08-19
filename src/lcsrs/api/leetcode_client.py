"""LeetCode API client.

A thin, mocked-friendly HTTP client that fetches the authenticated user's
submission history. Auth uses a session cookie (``LEETCODE_SESSION``); the
cookie value is supplied by the caller and never hardcoded here.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from lcsrs.config import LEETCODE_GRAPHQL_URL

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.5
PAGE_SIZE = 20


class LeetCodeAPIError(Exception):
    """Raised when the LeetCode API cannot be reached."""


@dataclass
class RawSubmission:
    """A normalized submission record returned by the client."""

    id: int
    problem_slug: str
    title: str
    difficulty: str
    tags: list[str]
    submitted_at: datetime
    status: str  # Accepted | WrongAnswer | TLE | ...
    runtime_ms: int | None
    attempts_before_ac: int


class LeetCodeClient:
    """Fetch the authenticated user's submissions through GraphQL."""

    def __init__(
        self,
        session_cookie: str,
        *,
        base_url: str = LEETCODE_GRAPHQL_URL,
        timeout: float = 30.0,
        max_retries: int = MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._cookie = session_cookie
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._problem_metadata: dict[str, dict[str, Any]] = {}
        self._client = httpx.Client(
            cookies={"LEETCODE_SESSION": session_cookie},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://leetcode.com/",
                "Origin": "https://leetcode.com",
            },
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LeetCodeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _post_with_retry(self, payload: dict[str, object]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = self._client.post(self._base_url, json=payload)
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    delay = BACKOFF_BASE_SECONDS * (2**attempt)
                    logger.warning("LeetCode request failed (%s); retrying in %.1fs", exc, delay)
                    time.sleep(delay)
        raise LeetCodeAPIError(
            f"LeetCode request failed after {self._max_retries} attempts: {last_error}"
        )

    def fetch_submissions(self, since: datetime) -> list[RawSubmission]:
        """Fetch all submissions submitted at or after ``since`` (UTC).

        Paginates through GraphQL until there are no more pages or a page whose
        oldest submission predates ``since`` is reached.
        """
        since_utc = since.astimezone(UTC)
        results: list[RawSubmission] = []
        offset = 0
        seen: set[int] = set()

        query = """
        query submissionList($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String) {
          submissionList(
            offset: $offset
            limit: $limit
            lastKey: $lastKey
            questionSlug: $questionSlug
          ) {
            lastKey
            hasNext
            submissions {
              id
              title
              titleSlug
              statusDisplay
              runtime
              timestamp
            }
          }
        }
        """

        while True:
            request_payload: dict[str, object] = {
                "query": query,
                "variables": {
                    "offset": offset,
                    "limit": PAGE_SIZE,
                    "lastKey": None,
                    "questionSlug": None,
                },
            }
            response = self._post_with_retry(request_payload)
            try:
                response_payload = response.json()
            except json.JSONDecodeError as exc:
                raise LeetCodeAPIError("LeetCode returned non-JSON response") from exc

            errors = response_payload.get("errors") or []
            if errors:
                message = (
                    errors[0].get("message", "unknown GraphQL error")
                    if isinstance(errors[0], dict)
                    else str(errors[0])
                )
                raise LeetCodeAPIError(f"LeetCode GraphQL error: {message}")

            submission_list = (response_payload.get("data") or {}).get("submissionList")
            if not isinstance(submission_list, dict):
                raise LeetCodeAPIError("LeetCode returned an invalid submission response")

            dump = submission_list.get("submissions") or []
            if not dump:
                break

            page_done = False
            metadata = self._fetch_problem_metadata(dump)
            for entry in dump:
                submission_id_raw = entry.get("id")
                timestamp = entry.get("timestamp")
                if submission_id_raw is None or timestamp is None:
                    continue
                submission_id = int(submission_id_raw)
                submitted_at = datetime.fromtimestamp(int(timestamp), tz=UTC)
                if submitted_at < since_utc:
                    page_done = True
                    break
                if submission_id in seen:
                    continue
                seen.add(submission_id)
                enriched_entry = {**entry, **metadata.get(str(entry.get("titleSlug", "")), {})}
                results.append(_parse_entry(enriched_entry, submitted_at))

            if page_done:
                break
            if not submission_list.get("hasNext", False):
                break
            offset += len(dump)

        return results

    def _fetch_problem_metadata(self, entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Fetch difficulty and tags for submission problems missing metadata."""
        slugs = {
            str(entry.get("titleSlug"))
            for entry in entries
            if not entry.get("difficulty")
            and entry.get("titleSlug")
            and str(entry.get("titleSlug")) not in self._problem_metadata
        }
        if not slugs:
            return self._problem_metadata

        variables: dict[str, str] = {}
        fields: list[str] = []
        aliases: dict[str, str] = {}
        for index, slug in enumerate(sorted(slugs)):
            variable = f"slug{index}"
            alias = f"problem{index}"
            variables[variable] = slug
            aliases[alias] = slug
            fields.append(
                f"{alias}: question(titleSlug: ${variable}) "
                "{ titleSlug difficulty topicTags { slug } }"
            )

        query = "query problemMetadata(" + ", ".join(
            f"${name}: String!" for name in variables
        ) + ") { " + " ".join(fields) + " }"
        try:
            response = self._post_with_retry({"query": query, "variables": variables})
            payload = response.json()
            if payload.get("errors"):
                raise LeetCodeAPIError("LeetCode returned an error while fetching problem metadata")
            data = payload.get("data") or {}
            for alias, slug in aliases.items():
                question = data.get(alias)
                if isinstance(question, dict):
                    self._problem_metadata[slug] = question
        except (LeetCodeAPIError, json.JSONDecodeError) as exc:
            logger.warning("Could not fetch problem metadata: %s", exc)

        return self._problem_metadata


def _parse_entry(entry: dict[str, Any], submitted_at: datetime) -> RawSubmission:
    title = entry.get("title") or ""
    title_slug = entry.get("title_slug") or entry.get("titleSlug") or _slugify(title)
    difficulty = entry.get("difficulty") or "Medium"
    status = entry.get("status_display") or entry.get("status") or "Unknown"
    runtime = entry.get("runtime")
    runtime_ms = _parse_runtime(runtime)
    tags_raw = entry.get("topic_tags") or entry.get("topicTags") or entry.get("tags") or []
    tags: list[str] = []
    for t in tags_raw:
        if isinstance(t, dict):
            slug = t.get("slug")
            if slug:
                tags.append(str(slug))
        else:
            tags.append(str(t))
    return RawSubmission(
        id=int(entry["id"]),
        problem_slug=title_slug,
        title=title,
        difficulty=difficulty,
        tags=tags,
        submitted_at=submitted_at,
        status=status,
        runtime_ms=runtime_ms,
        attempts_before_ac=_count_attempts_before(entry),
    )


def _count_attempts_before(entry: dict[str, Any]) -> int:
    """Estimate attempts-before-accept for the current submission.

    LeetCode's public endpoint does not expose per-submission attempt counts
    directly; this is a best-effort estimate. We treat it as 1 for an accepted
    submission (the common case) and 0 otherwise, keeping the mapper simple.
    """
    status = (entry.get("status_display") or entry.get("status") or "").lower()
    if status == "accepted":
        return 1
    return 0


def _parse_runtime(runtime: object) -> int | None:
    if isinstance(runtime, int):
        return runtime
    if isinstance(runtime, str):
        digits = "".join(ch for ch in runtime if ch.isdigit())
        return int(digits) if digits else None
    return None


def _slugify(title: str) -> str:
    return " ".join(title.lower().split()).replace(" ", "-")
