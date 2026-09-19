import httpx

from donstu_sdk import DonstuClient


def test_login_unwraps_nested_tokenauth_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/TokenAuth"
        return httpx.Response(
            200,
            json={
                "state": 1,
                "msg": "",
                "data": {
                    "state": 1,
                    "accessToken": "abc",
                    "data": {"id": -1, "accessToken": "abc"},
                },
            },
        )

    client = DonstuClient(transport=httpx.MockTransport(handler))
    result = client.auth.login("student", "password")
    assert result["accessToken"] == "abc"
    assert client.token == "abc"
    client.close()


def test_student_uses_bearer_and_query():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        assert request.url.path == "/api/UserInfo/Student"
        assert request.url.params["studentID"] == "-123"
        return httpx.Response(200, json={"state": 1, "data": {"studentID": -123}})

    client = DonstuClient(token="token", transport=httpx.MockTransport(handler))
    data = client.users.student(-123)
    assert data["studentID"] == -123
    client.close()


def test_catalog_is_packaged():
    client = DonstuClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert len(client.catalog) > 1000
    assert client.catalog.exact("GET", "/api/Rasp").controller == "RaspController"
    client.close()
