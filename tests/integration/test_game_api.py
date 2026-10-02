async def _signup(client, login: str, password: str = "secret123") -> tuple[str, dict]:
    response = await client.post("/auth/signup", json={"login": login, "password": password})
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    response = await client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, response.text
    return user_id, {"Authorization": f"Bearer {response.json()['accessToken']}"}


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


# ---- история игр -----------------------------------------------------------

X_WINS = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]


async def _play_moves(client, game_id, players, moves):
    """players = [(headers_X, 1), (headers_O, -1)]; ходы по очереди, X первым."""
    grid = [[0] * 3 for _ in range(3)]
    response = None
    for i, (row, col) in enumerate(moves):
        headers, symbol = players[i % 2]
        grid[row][col] = symbol
        response = await client.patch(
            f"/game/{game_id}",
            json={"board": {"grid": [r[:] for r in grid]}},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    return response.json()


async def _finished_human_game(client, x_headers, o_headers):
    created = await client.post("/game", json={"vs_computer": False}, headers=x_headers)
    game_id = created.json()["id"]
    await client.post(f"/game/{game_id}/join", headers=o_headers)
    final = await _play_moves(client, game_id, [(x_headers, 1), (o_headers, -1)], X_WINS)
    assert final["state"]["status"] == "WIN"
    return game_id


async def test_history_requires_auth(client):
    response = await client.get("/game/history")

    assert response.status_code == 401


async def test_history_is_empty_for_new_user(client):
    _, headers = await _signup(client, "hist_empty")

    response = await client.get("/game/history", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_history_lists_finished_games_for_both_players(client):
    _, alice = await _signup(client, "hist_alice")
    _, bob = await _signup(client, "hist_bob")
    _, carol = await _signup(client, "hist_carol")
    game_id = await _finished_human_game(client, alice, bob)

    for headers in (alice, bob):
        response = await client.get("/game/history", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert [g["id"] for g in body] == [game_id]
        assert body[0]["state"]["status"] == "WIN"
        assert body[0]["created_at"]

    # посторонний пользователь чужую историю не видит
    assert (await client.get("/game/history", headers=carol)).json() == []


async def test_history_excludes_unfinished_games(client):
    _, alice = await _signup(client, "hist_unfinished_a")
    _, bob = await _signup(client, "hist_unfinished_b")
    await client.post("/game", json={"vs_computer": True}, headers=alice)   # идёт
    await client.post("/game", json={"vs_computer": False}, headers=alice)  # ждёт соперника
    finished_id = await _finished_human_game(client, alice, bob)

    response = await client.get("/game/history", headers=alice)

    assert [g["id"] for g in response.json()] == [finished_id]


async def test_game_response_contains_created_at(client):
    _, headers = await _signup(client, "hist_created_at")

    response = await client.post("/game", json={"vs_computer": True}, headers=headers)

    assert response.status_code == 201
    assert response.json()["created_at"]
