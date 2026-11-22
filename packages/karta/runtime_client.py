"""HTTP client for the documented control-plane to Pi-runtime contract."""

from __future__ import annotations

import httpx

from .errors import ApiError
from .models import ExecutionRequest, ExecutionResult


class RuntimeClient:
    """Calls the TypeScript Pi runtime over its internal HTTP API."""

    def __init__(self, base_url: str, internal_token: str, timeout: float = 600.0) -> None:
        """Initialise the client.

        Args:
            base_url: Runtime service base URL without a trailing slash.
            internal_token: Shared secret sent in ``X-Karta-Internal-Token``.
            timeout: Request timeout in seconds.

        """
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Karta-Internal-Token": internal_token}
        self._client = httpx.Client(base_url=self._base_url, headers=self._headers, timeout=timeout)

    def health(self) -> bool:
        """Return whether the runtime reports itself healthy."""
        try:
            response = self._client.get("/health")
        except httpx.HTTPError:
            return False
        return response.status_code == 200 and response.json().get("status") == "ok"

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute one task and return the structured runtime result.

        Args:
            request: Fully populated execution contract.

        Returns:
            Parsed execution result.

        Raises:
            ApiError: When the runtime is unreachable or returns an error.

        """
        try:
            response = self._client.post(
                "/v1/execute",
                content=request.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise ApiError(502, "runtime_unavailable", "Pi runtime is unreachable") from exc
        if response.status_code >= 400:
            raise ApiError(502, "runtime_error", f"Pi runtime returned HTTP {response.status_code}")
        try:
            return ExecutionResult.model_validate(response.json())
        except ValueError as exc:
            raise ApiError(
                502, "runtime_contract", "Pi runtime returned an invalid result"
            ) from exc

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
