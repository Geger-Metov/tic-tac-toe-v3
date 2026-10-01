async def _signup_and_login(client, login: str, password: str = "secret123"):
    signup = await client.post("/auth/signup", json={"login": login, "password": password})
    assert signup.status_code == 201, signup.text
    response = await client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, response.text
    return signup.json()["id"], response.json()


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_signup_returns_id(client):
    response = await client.post("/auth/signup", json={"login": "alice", "password": "secret123"})

    assert response.status_code == 201
    assert response.json()["success"] is True


async def test_signup_duplicate_login_conflicts(client):
    await client.post("/auth/signup", json={"login": "bob", "password": "secret123"})
    response = await client.post("/auth/signup", json={"login": "bob", "password": "another-password"})

    assert response.status_code == 409


async def test_signup_short_password_rejected(client):
    response = await client.post("/auth/signup", json={"login": "carol", "password": "123"})

    assert response.status_code == 422


async def test_login_returns_token_pair(client):
    _, tokens = await _signup_and_login(client, "dave")

    assert tokens["type"] == "Bearer"
    assert tokens["accessToken"]
    assert tokens["refreshToken"]


async def test_login_wrong_password(client):
    await client.post("/auth/signup", json={"login": "erin", "password": "secret123"})
    response = await client.post("/auth/login", json={"login": "erin", "password": "wrong-password"})

    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post("/auth/login", json={"login": "nobody", "password": "whatever1"})

    assert response.status_code == 401


async def test_me_with_access_token(client):
    user_id, tokens = await _signup_and_login(client, "frank")

    response = await client.get("/auth/me", headers=bearer(tokens["accessToken"]))

    assert response.status_code == 200
    assert response.json() == {"id": user_id, "login": "frank"}


async def test_protected_endpoint_without_token(client):
    response = await client.post("/game", json={"vs_computer": True})

    assert response.status_code == 401


async def test_basic_auth_no_longer_accepted(client):
    await client.post("/auth/signup", json={"login": "gina", "password": "secret123"})
    # Basic gina:secret123
    response = await client.get("/auth/me", headers={"Authorization": "Basic Z2luYTpzZWNyZXQxMjM="})

    assert response.status_code == 401


async def test_garbage_token_rejected(client):
    response = await client.get("/auth/me", headers=bearer("not.a.jwt"))

    assert response.status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(client):
    _, tokens = await _signup_and_login(client, "hank")

    response = await client.get("/auth/me", headers=bearer(tokens["refreshToken"]))

    assert response.status_code == 401


async def test_access_token_cannot_be_used_for_refresh(client):
    _, tokens = await _signup_and_login(client, "ivy")

    response = await client.post("/auth/token/access", json={"refreshToken": tokens["accessToken"]})

    assert response.status_code == 401


async def test_refresh_access_token_issues_new_working_pair(client):
    user_id, tokens = await _signup_and_login(client, "jack")

    response = await client.post("/auth/token/access", json={"refreshToken": tokens["refreshToken"]})

    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refreshToken"] != tokens["refreshToken"]
    me = await client.get("/auth/me", headers=bearer(new_tokens["accessToken"]))
    assert me.json()["id"] == user_id


async def test_refresh_token_is_single_use(client):
    _, tokens = await _signup_and_login(client, "kate")

    first = await client.post("/auth/token/access", json={"refreshToken": tokens["refreshToken"]})
    second = await client.post("/auth/token/access", json={"refreshToken": tokens["refreshToken"]})

    assert first.status_code == 200
    assert second.status_code == 401


async def test_refresh_refresh_token_rotates_and_is_single_use(client):
    _, tokens = await _signup_and_login(client, "leo")

    first = await client.post("/auth/token/refresh", json={"refreshToken": tokens["refreshToken"]})
    replay = await client.post("/auth/token/refresh", json={"refreshToken": tokens["refreshToken"]})
    chained = await client.post("/auth/token/refresh", json={"refreshToken": first.json()["refreshToken"]})

    assert first.status_code == 200
    assert replay.status_code == 401
    assert chained.status_code == 200
