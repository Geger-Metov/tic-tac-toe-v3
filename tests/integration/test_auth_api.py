import base64


def _basic_auth_header(login: str, password: str) -> dict:
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def test_signup_returns_id(client):
    response = await client.post(
        "/auth/signup", json={"login": "alice", "password": "secret123"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "id" in body


async def test_signup_duplicate_login_conflicts(client):
    await client.post("/auth/signup", json={"login": "bob", "password": "secret123"})

    response = await client.post(
        "/auth/signup", json={"login": "bob", "password": "another-password"}
    )

    assert response.status_code == 409


async def test_signup_short_password_rejected(client):
    response = await client.post(
        "/auth/signup", json={"login": "carol", "password": "123"}
    )

    assert response.status_code == 422  # валидация Pydantic (min_length=6)


async def test_login_with_correct_credentials(client):
    signup = await client.post(
        "/auth/signup", json={"login": "dave", "password": "secret123"}
    )
    user_id = signup.json()["id"]

    response = await client.post(
        "/auth/login", headers=_basic_auth_header("dave", "secret123")
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == user_id


async def test_login_with_wrong_password(client):
    await client.post("/auth/signup", json={"login": "erin", "password": "secret123"})

    response = await client.post(
        "/auth/login", headers=_basic_auth_header("erin", "wrong-password")
    )

    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post(
        "/auth/login", headers=_basic_auth_header("no_such_user", "whatever")
    )

    assert response.status_code == 401


async def test_login_without_header(client):
    response = await client.post("/auth/login")

    assert response.status_code == 401


async def test_protected_endpoint_requires_auth(client):
    response = await client.post("/game", json={"vs_computer": True})

    assert response.status_code == 401
