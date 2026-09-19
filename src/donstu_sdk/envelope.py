from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import DonstuAPIError


@dataclass(slots=True)
class Envelope:
    """Common ``state/msg/data`` response envelope used by the API."""

    state: Any
    data: Any = None
    msg: str = ""
    raw: Any = None

    @classmethod
    def from_payload(cls, payload: Any) -> "Envelope | None":
        if not isinstance(payload, dict) or "state" not in payload:
            return None
        return cls(
            state=payload.get("state"),
            data=payload.get("data"),
            msg=str(payload.get("msg") or ""),
            raw=payload,
        )

    @property
    def ok(self) -> bool:
        value = str(self.state).lower()
        return self.state == 1 or self.state is True or value in {"success", "1", "true"}

    def ensure_success(self) -> None:
        if not self.ok:
            raise DonstuAPIError(self.state, self.msg, payload=self.raw)

    def unwrap(self) -> Any:
        self.ensure_success()
        return self.data
