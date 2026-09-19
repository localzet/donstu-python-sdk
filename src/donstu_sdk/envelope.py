from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import DonstuAPIError


@dataclass(slots=True)
class Envelope:
    """Стандартный ответ MMISLab: state/msg/data."""

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
        # RequestState.Success = 1. На части старых ответов возможен bool True.
        return self.state == 1 or self.state is True or str(self.state).lower() == "success"

    def unwrap(self) -> Any:
        if not self.ok:
            raise DonstuAPIError(self.state, self.msg, payload=self.raw)
        return self.data
