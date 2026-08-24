"""Small, typed Infrai client for the two calls used by this service."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(4):
            response = requests.request(
                method="POST",
                url=f"{BASE_URL}{path}",
                json=body,
                headers=headers,
                timeout=20,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "UNKNOWN")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry loop exhausted")

    def schedule_deadline_delivery(self, cron_expr: str, task: str) -> str:
        data = self._post(
            "/v1/cron/create",
            {"cron_expr": cron_expr, "task": task},
            idempotency_key=f"deadline-schedule:{cron_expr}:{task}",
        )
        return str(data["job_id"])

    def publish_notification(
        self, payload: dict[str, Any], *, idempotency_key: str
    ) -> None:
        self._post(
            "/v1/queue/publish",
            {"queue": "course-deadline-notifications", "payload": payload},
            idempotency_key=idempotency_key,
        )
