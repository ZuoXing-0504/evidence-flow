from __future__ import annotations

import asyncio
from typing import Any

import httpx


class ExternalProviderError(RuntimeError):
    pass


async def post_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    service: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    attempts: int = 3,
) -> dict[str, Any]:
    for attempt in range(attempts):
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            if attempt + 1 == attempts:
                raise ExternalProviderError(f"{service} request failed") from exc
            await asyncio.sleep(0.2 * (2**attempt))
            continue

        if (response.status_code == 429 or response.status_code >= 500) and attempt + 1 < attempts:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after is not None else None
            except ValueError:
                delay = None
            if delay is None:
                delay = (1.0 if response.status_code == 429 else 0.2) * (2**attempt)
            await asyncio.sleep(min(max(delay, 0), 30))
            continue
        if not response.is_success:
            raise ExternalProviderError(f"{service} returned HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ExternalProviderError(f"{service} returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise ExternalProviderError(f"{service} returned an invalid response shape")
        return data

    raise ExternalProviderError(f"{service} request failed")
