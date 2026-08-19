"""Unit tests for the LeetCode API client using a mock HTTP transport."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from lcsrs.api.leetcode_client import LeetCodeAPIError, LeetCodeClient


class MockTransport(httpx.MockTransport):
    def __init__(self, pages: list[dict]) -> None:
        self.pages = pages
        self.requests: list[dict] = []
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        assert isinstance(payload, dict)
        variables = payload["variables"]
        self.requests.append({"url": str(request.url), "payload": payload})
        offset = int(variables["offset"])
        idx = offset // 20
        if idx < len(self.pages):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "submissionList": {
                            "lastKey": None,
                            "hasNext": idx + 1 < len(self.pages),
                            "submissions": self.pages[idx]["submissions_dump"],
                        }
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "submissionList": {
                        "lastKey": None,
                        "hasNext": False,
                        "submissions": [],
                    }
                }
            },
        )


def _entry(id_: int, timestamp: int, slug: str, status: str = "Accepted") -> dict:
    return {
        "id": id_,
        "title_slug": slug,
        "title": slug.replace("-", " ").title(),
        "difficulty": "Easy",
        "timestamp": timestamp,
        "status_display": status,
        "runtime": "10 ms",
        "topic_tags": [{"slug": "array"}],
    }


def test_fetch_submissions_returns_normalized_records() -> None:
    now = datetime.now(UTC)
    ts = int(now.timestamp())
    transport = MockTransport([{"submissions_dump": [_entry(1, ts, "two-sum")]}])
    client = LeetCodeClient("cookie", transport=transport)
    try:
        results = client.fetch_submissions(datetime(2020, 1, 1, tzinfo=UTC))
    finally:
        client.close()

    assert len(results) == 1
    r = results[0]
    assert r.id == 1
    assert r.problem_slug == "two-sum"
    assert r.status == "Accepted"
    assert r.runtime_ms == 10
    assert r.tags == ["array"]


def test_fetch_stops_at_since_boundary() -> None:
    base = datetime(2026, 1, 15, tzinfo=UTC)
    since = datetime(2026, 1, 14, tzinfo=UTC)
    # One entry newer than since, one older -> only the newer is returned.
    transport = MockTransport(
        [
            {
                "submissions_dump": [
                    _entry(1, int((base).timestamp()), "newer"),
                    _entry(2, int((since - timedelta(days=1)).timestamp()), "older"),
                ]
            }
        ]
    )
    client = LeetCodeClient("cookie", transport=transport)
    try:
        results = client.fetch_submissions(since)
    finally:
        client.close()
    assert [r.problem_slug for r in results] == ["newer"]


def test_fetch_dedupes_submissions_across_pages() -> None:
    base = datetime(2026, 1, 15, tzinfo=UTC)
    ts = int(base.timestamp())
    transport = MockTransport(
        [
            {"submissions_dump": [_entry(1, ts, "two-sum")]},
            {"submissions_dump": [_entry(1, ts, "two-sum")]},  # duplicate id
        ]
    )
    client = LeetCodeClient("cookie", transport=transport)
    try:
        results = client.fetch_submissions(datetime(2020, 1, 1, tzinfo=UTC))
    finally:
        client.close()
    assert len(results) == 1


def test_fetch_raises_after_retries_on_http_error() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = LeetCodeClient("cookie", transport=httpx.MockTransport(_handler), max_retries=2)
    try:
        with pytest.raises(LeetCodeAPIError):
            client.fetch_submissions(datetime(2020, 1, 1, tzinfo=UTC))
    finally:
        client.close()
