"""Structured API errors for the kartā control plane."""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """An error that maps to a structured JSON HTTP response.

    Attributes:
        status_code: HTTP status code to return.
        code: Stable machine-readable error code.
        message: Human-readable description safe to return to the caller.
        details: Optional additional structured context.

    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the error.

        Args:
            status_code: HTTP status code to return.
            code: Stable machine-readable error code.
            message: Human-readable description safe to return to the caller.
            details: Optional additional structured context.

        """
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
