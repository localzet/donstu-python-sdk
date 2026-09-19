from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import httpx

from .envelope import Envelope
from .exceptions import (
    DonstuAuthenticationError,
    DonstuHTTPError,
    DonstuNetworkError,
    DonstuProtocolError,
)

DEFAULT_BASE_URL = "https://edu.donstu.ru/api/"


def _normalize_token(token: str | None) -> str | None:
    if token is None:
        return None
    value = token.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value or None


def _drop_none(values: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if values is None:
        return None
    return {key: value for key, value in values.items() if value is not None}


def _api_date(value: date | datetime | str | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()


class _ClientBase:
    def __init__(self, *, base_url: str, token: str | None) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = _normalize_token(token)

    def set_token(self, token: str | None) -> None:
        self.token = _normalize_token(token)

    @staticmethod
    def _normalize_path(path: str) -> str:
        value = path.lstrip("/")
        if value.lower().startswith("api/"):
            value = value[4:]
        return value

    def _request_headers(self, headers: Mapping[str, str] | None) -> dict[str, str]:
        result = dict(headers or {})
        if self.token and not any(key.lower() == "authorization" for key in result):
            result["Authorization"] = f"Bearer {self.token}"
        return result

    @staticmethod
    def _raise_http_error(response: httpx.Response) -> None:
        if not response.is_error:
            return
        error_type = DonstuAuthenticationError if response.status_code in {401, 403} else DonstuHTTPError
        text = response.text
        if len(text) > 4096:
            text = text[:4096] + "…"
        raise error_type(response.status_code, response.reason_phrase, response_text=text)

    @staticmethod
    def _decode(response: httpx.Response, *, unwrap: bool) -> Any:
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
        return envelope.unwrap() if envelope is not None else payload

    @staticmethod
    def _resolve_route(path: str, route_values: Mapping[str, Any] | None) -> str:
        resolved = path
        for key, value in (route_values or {}).items():
            resolved = resolved.replace("{" + key + "}", str(value))
            resolved = resolved.replace("{" + key + "?}", str(value))
        return resolved


class DonstuClient(_ClientBase):
    """Synchronous client for the DONSTU educational API."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool = True,
        client_version: str | None = None,
        fingerprint: str | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        follow_redirects: bool = True,
    ) -> None:
        super().__init__(base_url=base_url, token=token)

        default_headers = {
            "Accept": "application/json",
            "User-Agent": "donstu-sdk/0.2.0",
            **dict(headers or {}),
        }
        if client_version:
            default_headers["Client-Version"] = client_version
        if fingerprint:
            default_headers["fp"] = fingerprint

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify,
            headers=default_headers,
            transport=transport,
            follow_redirects=follow_redirects,
        )
        self.auth = AuthAPI(self)
        self.users = UsersAPI(self)
        self.schedule = ScheduleAPI(self)
        self.mail = MailAPI(self)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "DonstuClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        content: Any = None,
        files: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = self._http.request(
                method.upper(),
                self._normalize_path(path),
                params=_drop_none(params),
                json=json,
                data=data,
                content=content,
                files=files,
                headers=self._request_headers(headers),
            )
        except httpx.HTTPError as exc:
            raise DonstuNetworkError(str(exc)) from exc
        self._raise_http_error(response)
        return response

    def request(self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any) -> Any:
        return self._decode(self.request_raw(method, path, **kwargs), unwrap=unwrap)

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
        """Call an API route that does not yet have a high-level SDK method."""
        return self.request(
            method,
            self._resolve_route(path, route_values),
            params=params,
            json=json,
            unwrap=unwrap,
        )


class AsyncDonstuClient(_ClientBase):
    """Asynchronous client for asyncio/FastAPI/Telegram bot applications."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        verify: bool = True,
        client_version: str | None = None,
        fingerprint: str | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        follow_redirects: bool = True,
    ) -> None:
        super().__init__(base_url=base_url, token=token)

        default_headers = {
            "Accept": "application/json",
            "User-Agent": "donstu-sdk/0.2.0",
            **dict(headers or {}),
        }
        if client_version:
            default_headers["Client-Version"] = client_version
        if fingerprint:
            default_headers["fp"] = fingerprint

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify,
            headers=default_headers,
            transport=transport,
            follow_redirects=follow_redirects,
        )
        self.auth = AsyncAuthAPI(self)
        self.users = AsyncUsersAPI(self)
        self.schedule = AsyncScheduleAPI(self)
        self.mail = AsyncMailAPI(self)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncDonstuClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def request_raw(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        params = kwargs.pop("params", None)
        headers = kwargs.pop("headers", None)
        try:
            response = await self._http.request(
                method.upper(),
                self._normalize_path(path),
                params=_drop_none(params),
                headers=self._request_headers(headers),
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise DonstuNetworkError(str(exc)) from exc
        self._raise_http_error(response)
        return response

    async def request(self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any) -> Any:
        response = await self.request_raw(method, path, **kwargs)
        return self._decode(response, unwrap=unwrap)

    async def call_route(
        self,
        method: str,
        path: str,
        *,
        route_values: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        unwrap: bool = True,
    ) -> Any:
        return await self.request(
            method,
            self._resolve_route(path, route_values),
            params=params,
            json=json,
            unwrap=unwrap,
        )


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
        device_name: str | None = None,
        fingerprint: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"userName": username, "password": password}
        if recaptcha_token is not None:
            body["recaptchaToken"] = recaptcha_token
        if is_parent is not None:
            body["isParent"] = is_parent
        if device_name is not None:
            body["deviceName"] = device_name
        if fingerprint is not None:
            body["fingerprint"] = fingerprint

        result = self.client.request("POST", "TokenAuth", json=body)
        if not isinstance(result, dict):
            raise DonstuProtocolError("TokenAuth returned an unexpected payload")
        inner = Envelope.from_payload(result)
        if inner is not None:
            inner.ensure_success()

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

    def logout(self) -> None:
        self.client.set_token(None)


class UsersAPI(_API):
    def student(self, student_id: int, *, year: str = "") -> Any:
        return self.client.request("GET", "UserInfo/Student", params={"studentID": student_id, "year": year})

    def staff(self, user_id: int) -> Any:
        return self.client.request("GET", "UserInfo/User", params={"userID": user_id})

    def roles(self, user_id: int) -> Any:
        return self.client.request("GET", "UserInfo/UserRoles", params={"userID": user_id})

    def has_role(self, role_name: str, *, user_id: int | None = None) -> Any:
        return self.client.request(
            "GET",
            "UserInfo/UserCheckRole",
            params={"userID": user_id, "roleName": role_name},
        )

    def cards(self, user_ids: Sequence[int]) -> Any:
        return self.client.request("GET", "UserInfo/UserCardInfo", params={"userID": list(user_ids)})

    def group_info(self, **params: Any) -> Any:
        return self.client.request("GET", "UserInfo/GroupInfo", params=params)


class ScheduleAPI(_API):
    def get(
        self,
        *,
        group_id: int | None = None,
        teacher_id: int | None = None,
        teacher_line_id: int | None = None,
        auditorium_line_id: int | None = None,
        department_id: int | None = None,
        student_id: int | None = None,
        year: str | None = None,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        schedule_type: int = 0,
        new_version: bool = False,
        ical: bool = False,
    ) -> Any:
        return self.client.request(
            "GET",
            "Rasp",
            params={
                "idGroup": group_id,
                "idPrepodLine": teacher_line_id,
                "idTeacher": teacher_id,
                "idAudLine": auditorium_line_id,
                "idKaf": department_id,
                "idStudent": student_id,
                "year": year,
                "sdate": _api_date(start_date),
                "edate": _api_date(end_date),
                "type": schedule_type,
                "isNewVer": new_version,
                "iCal": ical,
            },
        )

    def rasp(self, **params: Any) -> Any:
        """Compatibility helper using native API query parameter names."""
        return self.client.request("GET", "Rasp", params=params)

    def current_user(self) -> Any:
        return self.client.request("GET", "CurrentUserRasp")

    def groups(self, *, faculty_id: int | None = None, year: str | None = None) -> Any:
        return self.client.request("GET", "RaspGroupList", params={"facultyID": faculty_id, "year": year})

    def teachers(
        self,
        *,
        faculty_id: int | None = None,
        year: str | None = None,
        semester: int | None = None,
    ) -> Any:
        return self.client.request(
            "GET",
            "RaspTeacherList",
            params={"facultyID": faculty_id, "year": year, "sem": semester},
        )

    def instructors(
        self,
        *,
        faculty_id: int | None = None,
        year: str | None = None,
        semester: int | None = None,
        from_teachers: bool = False,
    ) -> Any:
        return self.client.request(
            "GET",
            "RaspPrepodList",
            params={
                "facultyID": faculty_id,
                "year": year,
                "sem": semester,
                "fromTeachers": from_teachers,
            },
        )

    def auditories(
        self,
        *,
        faculty_id: int | None = None,
        year: str | None = None,
        semester: int | None = None,
    ) -> Any:
        return self.client.request(
            "GET",
            "RaspAudList",
            params={"facultyID": faculty_id, "year": year, "sem": semester},
        )

    def years(self) -> Any:
        return self.client.request("GET", "Rasp/ListYears")

    def available_dates(
        self,
        *,
        group_id: int | None = None,
        teacher_id: int | None = None,
        teacher_line_id: int | None = None,
        auditorium_line_id: int | None = None,
        department_id: int | None = None,
        year: str | None = None,
    ) -> Any:
        return self.client.request(
            "GET",
            "GetRaspDates",
            params={
                "idGroup": group_id,
                "idTeacher": teacher_id,
                "idPrepodLine": teacher_line_id,
                "idAudLine": auditorium_line_id,
                "idKaf": department_id,
                "year": year,
            },
        )

    def last_update(
        self,
        *,
        student_id: int | None = None,
        group_id: int | None = None,
        education_space_id: int | None = None,
    ) -> Any:
        return self.client.request(
            "GET",
            "Rasp/LastUpdateDate",
            params={
                "studentID": student_id,
                "groupID": group_id,
                "educationSpaceID": education_space_id,
            },
        )

    def manager_info(
        self,
        *,
        year: str | None = None,
        education_space_id: int | None = None,
    ) -> Any:
        return self.client.request(
            "GET",
            "RaspManagerInfo",
            params={"year": year, "educationSpaceID": education_space_id},
        )

    def manager(self, **params: Any) -> Any:
        return self.client.request("GET", "RaspManager", params=params)


class MailAPI(_API):
    def inbox(
        self,
        *,
        year: str | None = None,
        search_query: str | None = None,
        message_type: int | None = None,
        item_id: int | None = None,
        message_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        folder_id: int | None = None,
        break_point: int | None = None,
        unread_only: bool = False,
        parent_mode: int = 0,
    ) -> Any:
        return self.client.request(
            "GET",
            "Mail/InboxMail",
            params={
                "year": year,
                "searchQuery": search_query,
                "type": message_type,
                "id": item_id,
                "messageID": message_id,
                "page": page,
                "pageEl": page_size,
                "folderID": folder_id,
                "breakPoint": break_point,
                "unreadMessages": unread_only,
                "modeParent": parent_mode,
            },
        )

    def send(
        self,
        *,
        user_ids: Sequence[int],
        theme: str,
        markdown: str = "",
        message_type: int = 0,
        message: str = "",
        html_message: str = "",
    ) -> Any:
        return self.client.request(
            "POST",
            "Mail/InboxMail",
            json={
                "typeID": message_type,
                "theme": theme,
                "message": message,
                "htmlMessage": html_message,
                "markdownMessage": markdown,
                "userToID": [{"id": user_id} for user_id in user_ids],
            },
        )


class _AsyncAPI:
    def __init__(self, client: AsyncDonstuClient) -> None:
        self.client = client


class AsyncAuthAPI(_AsyncAPI):
    async def login(self, username: str, password: str, **kwargs: Any) -> dict[str, Any]:
        body: dict[str, Any] = {"userName": username, "password": password}
        mapping = {
            "recaptcha_token": "recaptchaToken",
            "is_parent": "isParent",
            "device_name": "deviceName",
            "fingerprint": "fingerprint",
        }
        for source, target in mapping.items():
            if kwargs.get(source) is not None:
                body[target] = kwargs[source]

        result = await self.client.request("POST", "TokenAuth", json=body)
        if not isinstance(result, dict):
            raise DonstuProtocolError("TokenAuth returned an unexpected payload")
        inner = Envelope.from_payload(result)
        if inner is not None:
            inner.ensure_success()
        token = result.get("accessToken")
        nested = result.get("data")
        if not token and isinstance(nested, dict):
            token = nested.get("accessToken")
        if not token:
            raise DonstuProtocolError("TokenAuth succeeded but accessToken is missing")
        self.client.set_token(str(token))
        return result

    async def me(self) -> Any:
        return await self.client.request("GET", "TokenAuth")

    def logout(self) -> None:
        self.client.set_token(None)


class AsyncUsersAPI(_AsyncAPI):
    async def student(self, student_id: int, *, year: str = "") -> Any:
        return await self.client.request("GET", "UserInfo/Student", params={"studentID": student_id, "year": year})

    async def staff(self, user_id: int) -> Any:
        return await self.client.request("GET", "UserInfo/User", params={"userID": user_id})

    async def roles(self, user_id: int) -> Any:
        return await self.client.request("GET", "UserInfo/UserRoles", params={"userID": user_id})

    async def has_role(self, role_name: str, *, user_id: int | None = None) -> Any:
        return await self.client.request(
            "GET",
            "UserInfo/UserCheckRole",
            params={"userID": user_id, "roleName": role_name},
        )

    async def cards(self, user_ids: Sequence[int]) -> Any:
        return await self.client.request("GET", "UserInfo/UserCardInfo", params={"userID": list(user_ids)})


class AsyncScheduleAPI(_AsyncAPI):
    async def get(self, **kwargs: Any) -> Any:
        params = {
            "idGroup": kwargs.get("group_id"),
            "idPrepodLine": kwargs.get("teacher_line_id"),
            "idTeacher": kwargs.get("teacher_id"),
            "idAudLine": kwargs.get("auditorium_line_id"),
            "idKaf": kwargs.get("department_id"),
            "idStudent": kwargs.get("student_id"),
            "year": kwargs.get("year"),
            "sdate": _api_date(kwargs.get("start_date")),
            "edate": _api_date(kwargs.get("end_date")),
            "type": kwargs.get("schedule_type", 0),
            "isNewVer": kwargs.get("new_version", False),
            "iCal": kwargs.get("ical", False),
        }
        return await self.client.request("GET", "Rasp", params=params)

    async def rasp(self, **params: Any) -> Any:
        return await self.client.request("GET", "Rasp", params=params)

    async def current_user(self) -> Any:
        return await self.client.request("GET", "CurrentUserRasp")

    async def groups(self, *, faculty_id: int | None = None, year: str | None = None) -> Any:
        return await self.client.request("GET", "RaspGroupList", params={"facultyID": faculty_id, "year": year})

    async def teachers(self, *, faculty_id: int | None = None, year: str | None = None, semester: int | None = None) -> Any:
        return await self.client.request(
            "GET",
            "RaspTeacherList",
            params={"facultyID": faculty_id, "year": year, "sem": semester},
        )

    async def auditories(self, *, faculty_id: int | None = None, year: str | None = None, semester: int | None = None) -> Any:
        return await self.client.request(
            "GET",
            "RaspAudList",
            params={"facultyID": faculty_id, "year": year, "sem": semester},
        )

    async def years(self) -> Any:
        return await self.client.request("GET", "Rasp/ListYears")

    async def manager(self, **params: Any) -> Any:
        return await self.client.request("GET", "RaspManager", params=params)


class AsyncMailAPI(_AsyncAPI):
    async def inbox(self, **params: Any) -> Any:
        return await self.client.request("GET", "Mail/InboxMail", params=params)

    async def send(
        self,
        *,
        user_ids: Sequence[int],
        theme: str,
        markdown: str = "",
        message_type: int = 0,
        message: str = "",
        html_message: str = "",
    ) -> Any:
        return await self.client.request(
            "POST",
            "Mail/InboxMail",
            json={
                "typeID": message_type,
                "theme": theme,
                "message": message,
                "htmlMessage": html_message,
                "markdownMessage": markdown,
                "userToID": [{"id": user_id} for user_id in user_ids],
            },
        )
