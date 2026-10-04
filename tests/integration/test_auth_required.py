import pytest

ANY_UUID = "00000000-0000-0000-0000-000000000099"
BOARD = {"board": {"grid": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]}}

# Каждый защищённый эндпоинт, с корректным запросом (чтобы 401 нельзя было
# спутать с 422 от валидации тела). Открытыми остаются только signup, login и
# два refresh-эндпоинта.
PROTECTED = [
    ("GET", "/auth/me", None),
    ("POST", "/game", {"vs_computer": True}),
    ("GET", "/game/available", None),
    ("GET", "/game/history", None),
    ("GET", f"/game/{ANY_UUID}", None),
    ("POST", f"/game/{ANY_UUID}/join", None),
    ("PATCH", f"/game/{ANY_UUID}", BOARD),
    ("GET", f"/users/{ANY_UUID}", None),
    ("GET", "/leaderboard", None),
]
IDS = [f"{method} {path}" for method, path, _ in PROTECTED]


@pytest.mark.parametrize("method,path,body", PROTECTED, ids=IDS)
async def test_requires_token(client, method, path, body):
    response = await client.request(method, path, json=body)

    assert response.status_code == 401


@pytest.mark.parametrize("method,path,body", PROTECTED, ids=IDS)
async def test_rejects_garbage_token(client, method, path, body):
    response = await client.request(
        method, path, json=body, headers={"Authorization": "Bearer not.a.jwt"}
    )

    assert response.status_code == 401
