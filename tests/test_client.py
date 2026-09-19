import asyncio
from datetime import date

import httpx
import pytest

from donstu_sdk import (
    AsyncDonstuClient,
    DonstuAPIError,
    DonstuAuthenticationError,
    DonstuClient,
    DonstuHTTPError,
)


def test_token_is_normalized_and_sent_as_bearer():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token-value"
        return httpx.Response(200, json={"state": 1, "data": {"id": -123}})

    with DonstuClient(
        token="  Bearer token-value  ",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.token == "token-value"
        assert client.auth.me() == {"id": -123}


def test_login_preserves_request_result_and_sets_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/TokenAuth"
        assert request.headers["Content-Type"].startswith("application/json")
        return httpx.Response(
            200,
            json={
                "state": 1,
                "msg": "",
                "data": {
                    "state": 1,
                    "accessToken": "abc",
                    "expiresIn": 3600,
                    "data": {
                        "id": -1,
                        "userName": "Student",
                        "accessToken": "abc",
                        "refreshToken": "refresh",
                    },
                },
            },
        )

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        result = client.auth.login("student", "password")
        assert result["accessToken"] == "abc"
        assert result["expiresIn"] == 3600
        assert client.token == "abc"


def test_login_raises_api_error_for_failed_inner_state():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "state": 1,
                "data": {"state": 0, "msg": "bad credentials", "data": None},
            },
        )

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DonstuAPIError, match="bad credentials"):
            client.auth.login("student", "wrong")


def test_schedule_get_maps_python_arguments_to_api_query():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/Rasp"
        assert request.url.params["idGroup"] == "12345"
        assert request.url.params["sdate"] == "2026-09-21"
        assert request.url.params["edate"] == "2026-09-27"
        assert request.url.params["isNewVer"] == "true"
        assert "idTeacher" not in request.url.params
        return httpx.Response(200, json={"state": 1, "data": [{"id": 1}]})

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        data = client.schedule.get(
            group_id=12345,
            start_date=date(2026, 9, 21),
            end_date=date(2026, 9, 27),
            new_version=True,
        )
        assert data == [{"id": 1}]


def test_schedule_groups_uses_readable_python_parameters():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/RaspGroupList"
        assert request.url.params["facultyID"] == "5"
        assert request.url.params["year"] == "2026-2027"
        return httpx.Response(200, json={"state": 1, "data": []})

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        assert client.schedule.groups(faculty_id=5, year="2026-2027") == []


def test_request_does_not_force_json_content_type_for_multipart():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Content-Type"].startswith("multipart/form-data")
        return httpx.Response(200, json={"state": 1, "data": True})

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        result = client.request(
            "POST",
            "Upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert result is True


def test_http_authentication_error_is_specialized():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DonstuAuthenticationError) as exc_info:
            client.auth.me()
        assert exc_info.value.status_code == 401


def test_other_http_errors_are_donstu_http_error():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="oops")

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DonstuHTTPError) as exc_info:
            client.request("GET", "Anything")
        assert exc_info.value.response_text == "oops"


def test_call_route_substitutes_route_values():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/Example/42"
        return httpx.Response(200, json={"state": 1, "data": "ok"})

    with DonstuClient(transport=httpx.MockTransport(handler)) as client:
        result = client.call_route(
            "GET",
            "/api/Example/{id}",
            route_values={"id": 42},
        )
        assert result == "ok"


def test_async_client_has_same_schedule_surface():
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer async-token"
            assert request.url.path == "/api/Rasp"
            assert request.url.params["idTeacher"] == "77"
            return httpx.Response(200, json={"state": 1, "data": ["lesson"]})

        async with AsyncDonstuClient(
            token="async-token",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.schedule.get(teacher_id=77)
            assert result == ["lesson"]

    asyncio.run(scenario())
