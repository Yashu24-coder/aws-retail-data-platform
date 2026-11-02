"""Paginated REST extractor with retries.

Used in AWS mode to pull incremental pages from the commerce API. The default
base URL points at a local fixture server so the module is testable without
network access; set API_BASE_URL to the real endpoint in production.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..logging_setup import get_logger

log = get_logger("extract.api")

RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class ApiClient:
    base_url: str
    token: str = ""
    page_size: int = 200
    max_retries: int = 5
    timeout: int = 30

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        import requests  # noqa: PLC0415

        delay = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(
                    f"{self.base_url.rstrip('/')}{path}",
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if resp.status_code in RETRY_STATUS:
                    raise RuntimeError(f"retryable status {resp.status_code}")
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001 - retried, then re-raised
                if attempt == self.max_retries:
                    log.error("giving up on %s after %s attempts: %s", path, attempt, exc)
                    raise
                log.warning("attempt %s/%s failed (%s); retrying in %.1fs",
                            attempt, self.max_retries, exc, delay)
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
        raise RuntimeError("unreachable")

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """Yield every record across all pages, using cursor pagination."""
        params = dict(params or {})
        cursor: str | None = None
        while True:
            page_params = {**params, "limit": self.page_size}
            if cursor:
                page_params["cursor"] = cursor
            payload = self._get(path, page_params)
            records = payload.get("data", [])
            log.info("fetched %s records from %s", len(records), path)
            yield from records
            cursor = payload.get("next_cursor")
            if not cursor or not records:
                return
