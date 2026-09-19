from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    path: str
    controller: str
    action: str
    authorize: bool
    allow_anonymous: bool
    params: tuple[dict, ...]
    source: str


class RouteCatalog:
    """Каталог endpoint'ов, извлечённых из WebDekAPI/Controllers."""

    def __init__(self) -> None:
        raw = json.loads(
            files("donstu_sdk.resources").joinpath("routes.json").read_text(encoding="utf-8")
        )
        self._routes = tuple(
            Route(
                method=item["method"],
                path=item["path"],
                controller=item["controller"],
                action=item["action"],
                authorize=bool(item.get("authorize")),
                allow_anonymous=bool(item.get("allow_anonymous")),
                params=tuple(item.get("params") or ()),
                source=item["source"],
            )
            for item in raw
        )

    def __iter__(self) -> Iterable[Route]:
        return iter(self._routes)

    def __len__(self) -> int:
        return len(self._routes)

    def find(self, text: str, *, method: str | None = None) -> list[Route]:
        pattern = re.compile(re.escape(text), re.IGNORECASE)
        wanted_method = method.upper() if method else None
        return [
            route
            for route in self._routes
            if (wanted_method is None or route.method == wanted_method)
            and pattern.search(f"{route.path} {route.controller} {route.action} {route.source}")
        ]

    def exact(self, method: str, path: str) -> Route:
        method = method.upper()
        for route in self._routes:
            if route.method == method and route.path.lower() == path.lower():
                return route
        raise KeyError(f"Unknown route: {method} {path}")
