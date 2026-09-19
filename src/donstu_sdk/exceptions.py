from __future__ import annotations

from typing import Any


class DonstuError(Exception):
    """Base exception for the SDK."""


class DonstuNetworkError(DonstuError):
    """The API could not be reached because of a transport or timeout error."""


class DonstuHTTPError(DonstuError):
    """The server returned an unsuccessful HTTP status code."""

    def __init__(self, status_code: int, message: str, *, response_text: str = "") -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response_text = response_text


class DonstuAuthenticationError(DonstuHTTPError):
    """Authentication or authorization failed (HTTP 401/403)."""


class DonstuAPIError(DonstuError):
    """The API returned a valid response envelope with a failed state."""

    def __init__(self, state: Any, message: str, *, payload: Any = None) -> None:
        super().__init__(f"API state={state}: {message or 'unknown error'}")
        self.state = state
        self.message = message
        self.payload = payload


class DonstuProtocolError(DonstuError):
    """The response does not match the JSON format expected by the SDK."""
