import base64


async def _signup(client, login: str, password: str = "secret123") -> tuple[str, dict]:
    response = await client.post("/auth/signup", json={"login": login, "password": password})
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return user_id, {"Authorization": f"Basic {token}"}


async def test_create_game_vs_computer(client):
    _, headers = await _signup(client, "alice_vc")

    response = await client.post("/game", json={"vs_computer": True}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["vs_computer"] is True
    assert body["state"]["status"] == "PLAYER_TURN"


async def test_create_game_vs_human_waits(client):
    _, headers = await _signup(client, "alice_vh")

    response = await client.post("/game", json={"vs_computer": False}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["vs_computer"] is False
    assert body["player_o_id"] is None
    assert body["state"]["status"] == "WAITING_FOR_PLAYER"


async def test_available_games_lists_waiting_game(client):
    alice_id, alice_headers = await _signup(client, "alice_avail")

    created = await client.post("/game", json={"vs_computer": False}, headers=alice_headers)
    game_id = created.json()["id"]

    response = await client.get("/game/available", headers=alice_headers)

    assert response.status_code == 200
    assert any(g["id"] == game_id for g in response.json())


async def test_join_game_starts_turn_order(client):
    alice_id, alice_headers = await _signup(client, "alice_join")
    bob_id, bob_headers = await _signup(client, "bob_join")

    created = await client.post("/game", json={"vs_computer": False}, headers=alice_headers)
    game_id = created.json()["id"]

    response = await client.post(f"/game/{game_id}/join", headers=bob_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["player_o_id"] == bob_id
    assert body["state"]["status"] == "PLAYER_TURN"
    assert body["state"]["player_id"] == alice_id  # X ходит первым


async def test_cannot_join_own_game(client):
    _, alice_headers = await _signup(client, "alice_own")

    created = await client.post("/game", json={"vs_computer": False}, headers=alice_headers)
    game_id = created.json()["id"]

    response = await client.post(f"/game/{game_id}/join", headers=alice_headers)

    assert response.status_code == 409


async def test_move_out_of_turn_rejected(client):
    alice_id, alice_headers = await _signup(client, "alice_turn")
    bob_id, bob_headers = await _signup(client, "bob_turn")

    created = await client.post("/game", json={"vs_computer": False}, headers=alice_headers)
    game_id = created.json()["id"]
    await client.post(f"/game/{game_id}/join", headers=bob_headers)

    board = {"grid": [[-1, 0, 0], [0, 0, 0], [0, 0, 0]]}
    response = await client.patch(f"/game/{game_id}", json={"board": board}, headers=bob_headers)

    assert response.status_code == 409


async def test_full_turn_cycle_vs_human(client):
    alice_id, alice_headers = await _signup(client, "alice_cycle")
    bob_id, bob_headers = await _signup(client, "bob_cycle")

    created = await client.post("/game", json={"vs_computer": False}, headers=alice_headers)
    game_id = created.json()["id"]
    await client.post(f"/game/{game_id}/join", headers=bob_headers)

    board1 = {"grid": [[1, 0, 0], [0, 0, 0], [0, 0, 0]]}
    response = await client.patch(f"/game/{game_id}", json={"board": board1}, headers=alice_headers)
    assert response.status_code == 200
    assert response.json()["state"]["player_id"] == bob_id

    board2 = {"grid": [[1, 0, 0], [0, -1, 0], [0, 0, 0]]}
    response = await client.patch(f"/game/{game_id}", json={"board": board2}, headers=bob_headers)
    assert response.status_code == 200
    assert response.json()["state"]["player_id"] == alice_id


async def test_computer_responds_to_move(client):
    _, headers = await _signup(client, "alice_vs_comp")

    created = await client.post("/game", json={"vs_computer": True}, headers=headers)
    game_id = created.json()["id"]

    board = {"grid": [[0, 0, 0], [0, 1, 0], [0, 0, 0]]}
    response = await client.patch(f"/game/{game_id}", json={"board": board}, headers=headers)

    assert response.status_code == 200
    grid = response.json()["board"]["grid"]
    o_count = sum(row.count(-1) for row in grid)
    assert o_count == 1  # компьютер сходил один раз внутри того же запроса


async def test_get_nonexistent_game_404(client):
    _, headers = await _signup(client, "alice_404")

    response = await client.get(
        "/game/00000000-0000-0000-0000-000000000099", headers=headers
    )

    assert response.status_code == 404


async def test_get_user_by_id(client):
    alice_id, alice_headers = await _signup(client, "alice_lookup")

    response = await client.get(f"/users/{alice_id}", headers=alice_headers)

    assert response.status_code == 200
    assert response.json()["login"] == "alice_lookup"


async def test_get_unknown_user_404(client):
    _, headers = await _signup(client, "alice_unknownuser")

    response = await client.get(
        "/users/00000000-0000-0000-0000-000000000099", headers=headers
    )

    assert response.status_code == 404
