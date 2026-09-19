from __future__ import annotations

from typing import Any


class DonstuError(Exception):
    """Базовая ошибка SDK."""


class DonstuHTTPError(DonstuError):
    """HTTP-ошибка до разбора внутреннего MMISLab envelope."""

    def __init__(self, status_code: int, message: str, *, response_text: str = "") -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.response_text = response_text


class DonstuAPIError(DonstuError):
    """MMISLab вернул state != 1."""

    def __init__(self, state: Any, message: str, *, payload: Any = None) -> None:
        super().__init__(f"MMISLab state={state}: {message or 'unknown error'}")
        self.state = state
        self.message = message
        self.payload = payload


class DonstuProtocolError(DonstuError):
    """Ответ не соответствует ожидаемому формату API."""
