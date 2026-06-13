"""Shared HTTP helper for Horizon API calls with retry/backoff.

Horizon occasionally returns transient 5xx/429 responses under load;
ingestion modules use `get_with_retry` instead of calling `httpx` directly
so those are retried with exponential backoff rather than failing the
whole pipeline run.
"""

import time

import httpx

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retry(
    client: httpx.Client,
    url: str,
    params: dict | None = None,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> httpx.Response:
    """GET `url` via `client`, retrying transient failures with exponential backoff.

    Retries on connection errors and on `_RETRYABLE_STATUS_CODES` responses.
    Raises the underlying `httpx` exception (or calls `raise_for_status`) if
    all attempts fail.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.get(url, params=params)
        except httpx.TransportError as exc:
            last_exception = exc
        else:
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response
            last_exception = httpx.HTTPStatusError(
                f"Retryable status {response.status_code} from {url}",
                request=response.request,
                response=response,
            )

        if attempt < max_retries:
            time.sleep(backoff_seconds * (2**attempt))

    assert last_exception is not None
    raise last_exception
