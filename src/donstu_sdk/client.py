from __future__ import annotations

from typing import Any, Mapping
import httpx

from .catalog import RouteCatalog
from .envelope import Envelope
from .exceptions import DonstuHTTPError, DonstuProtocolError


class DonstuClient:
    """Синхронный клиент MMISLab/DSTU API.

    SDK НЕ генерирует JWT.
    Для авторизации используйте login/password или уже выданный bearer token.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://edu.donstu.ru/api/",
        token: str | None = None,
        timeout: float = 30.0,
        verify: bool = True,
        client_version: str | None = None,
        fingerprint: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.catalog = RouteCatalog()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "donstu-sdk/0.1.0",
        }
        if client_version:
            headers["Client-Version"] = client_version
        if fingerprint:
            headers["fp"] = fingerprint

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify,
            headers=headers,
            transport=transport,
        )

        # Высокоуровневые группы API.
        self.auth = AuthAPI(self)
        self.users = UsersAPI(self)
        self.schedule = ScheduleAPI(self)
        self.mail = MailAPI(self)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "DonstuClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def set_token(self, token: str | None) -> None:
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        unwrap: bool = True,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        request_headers = dict(headers or {})
        if self.token and "Authorization" not in request_headers:
            request_headers["Authorization"] = f"Bearer {self.token}"

        # При base_url .../api/ можно передавать и "/api/X", и "X".
        relative_path = self._normalize_path(path)
        response = self._http.request(
            method.upper(),
            relative_path,
            params=self._drop_none(params),
            json=json,
            data=data,
            files=files,
            headers=request_headers,
        )
        if response.is_error:
            raise DonstuHTTPError(
                response.status_code,
                response.reason_phrase,
                response_text=response.text,
            )

        if not response.content:
            return None
        try:
            payload = response.json()
        except ValueError as exc:
            if unwrap:
                raise DonstuProtocolError("API returned a non-JSON response") from exc
            return response.content

        if not unwrap:
            return payload

        envelope = Envelope.from_payload(payload)
        return envelope.unwrap() if envelope else payload

    def call_route(
        self,
        method: str,
        path: str,
        *,
        route_values: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        unwrap: bool = True,
    ) -> Any:
        """Вызвать произвольный endpoint из route catalog.

        Пример: call_route("GET", "/api/UserInfo/Student", params={"studentID": -123}).
        Для шаблонов вида /{id} передайте route_values={"id": 123}.
        """
        resolved = path
        for key, value in (route_values or {}).items():
            resolved = resolved.replace("{" + key + "}", str(value))
            resolved = resolved.replace("{" + key + "?}", str(value))
        return self.request(method, resolved, params=params, json=json, unwrap=unwrap)

    @staticmethod
    def _drop_none(values: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if values is None:
            return None
        return {key: value for key, value in values.items() if value is not None}

    def _normalize_path(self, path: str) -> str:
        value = path.lstrip("/")
        if value.lower().startswith("api/"):
            value = value[4:]
        return value


class _API:
    def __init__(self, client: DonstuClient) -> None:
        self.client = client


class AuthAPI(_API):
    def login(
        self,
        username: str,
        password: str,
        *,
        recaptcha_token: str | None = None,
        is_parent: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"userName": username, "password": password}
        if recaptcha_token is not None:
            body["recaptchaToken"] = recaptcha_token
        if is_parent is not None:
            body["isParent"] = is_parent

        outer_data = self.client.request("POST", "TokenAuth", json=body)
        # Актуальный TokenAuth заворачивает RequestResult внутрь RespondView.
        inner = Envelope.from_payload(outer_data)
        result = inner.unwrap() if inner else outer_data
        if not isinstance(result, dict):
            raise DonstuProtocolError("TokenAuth returned an unexpected payload")

        token = result.get("accessToken")
        nested = result.get("data")
        if not token and isinstance(nested, dict):
            token = nested.get("accessToken")
        if not token:
            raise DonstuProtocolError("TokenAuth succeeded but accessToken is missing")
        self.client.set_token(str(token))
        return result

    def me(self) -> Any:
        return self.client.request("GET", "TokenAuth")


class UsersAPI(_API):
    def student(self, student_id: int, *, year: str = "") -> Any:
        return self.client.request(
            "GET", "UserInfo/Student", params={"studentID": student_id, "year": year}
        )

    def staff(self, user_id: int) -> Any:
        return self.client.request("GET", "UserInfo/User", params={"userID": user_id})

    def roles(self, user_id: int) -> Any:
        return self.client.request("GET", "UserInfo/UserRoles", params={"userID": user_id})

    def group_info(self, **params: Any) -> Any:
        return self.client.request("GET", "UserInfo/GroupInfo", params=params)


class ScheduleAPI(_API):
    def rasp(self, **params: Any) -> Any:
        """Обычное расписание /api/Rasp.

        Поддерживаемые параметры из исходников: idGroup, idPrepodLine, idTeacher,
        idAudLine, idKaf, idStudent, year, sdate, edate, type, isNewVer, iCal.
        """
        return self.client.request("GET", "Rasp", params=params)

    def manager(self, **params: Any) -> Any:
        """Расписание SchoolX/elite через /api/RaspManager."""
        return self.client.request("GET", "RaspManager", params=params)

    def manager_info(self, *, year: str | None = None, education_space_id: int | None = None) -> Any:
        return self.client.request(
            "GET",
            "RaspManagerInfo",
            params={"year": year, "educationSpaceID": education_space_id},
        )

    def groups(self, *, faculty_id: int | None = None, year: str | None = None) -> Any:
        return self.client.request(
            "GET", "RaspGroupList", params={"facultyID": faculty_id, "year": year}
        )


class MailAPI(_API):
    def inbox(self, **params: Any) -> Any:
        return self.client.request("GET", "Mail/InboxMail", params=params)

    def send(
        self,
        *,
        user_ids: list[int],
        theme: str,
        markdown: str,
        type_id: int = 0,
        message: str = "",
        html_message: str = "",
    ) -> Any:
        body = {
            "typeID": type_id,
            "theme": theme,
            "message": message,
            "htmlMessage": html_message,
            "markdownMessage": markdown,
            "userToID": [{"id": user_id} for user_id in user_ids],
        }
        return self.client.request("POST", "Mail/InboxMail", json=body)
