import pytest

X_WINS = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]  # X берёт верхнюю строку
DRAW_MOVES = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0), (2, 2)]
NIL_UUID = "00000000-0000-0000-0000-000000000000"  # COMPUTER_ID


async def _signup(client, login: str, password: str = "secret123") -> dict:
    response = await client.post("/auth/signup", json={"login": login, "password": password})
    assert response.status_code == 201, response.text
    response = await client.post("/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def _play_human_game(client, x_headers, o_headers, moves):
    """Создаёт игру X против O и играет ходы по очереди (X первым)."""
    created = await client.post("/game", json={"vs_computer": False}, headers=x_headers)
    game_id = created.json()["id"]
    await client.post(f"/game/{game_id}/join", headers=o_headers)

    players = [(x_headers, 1), (o_headers, -1)]
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


async def _play_out_vs_computer(client, headers):
    """Человек ходит в первую свободную клетку, пока игра не закончится."""
    created = await client.post("/game", json={"vs_computer": True}, headers=headers)
    game = created.json()
    for _ in range(9):
        if game["state"]["status"] != "PLAYER_TURN":
            break
        grid = [row[:] for row in game["board"]["grid"]]
        row, col = next((r, c) for r in range(3) for c in range(3) if grid[r][c] == 0)
        grid[row][col] = 1
        response = await client.patch(
            f"/game/{game['id']}", json={"board": {"grid": grid}}, headers=headers
        )
        assert response.status_code == 200, response.text
        game = response.json()
    assert game["state"]["status"] in ("WIN", "DRAW")
    return game


async def _leaderboard(client, headers, n=100):
    response = await client.get("/leaderboard", params={"n": n}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_leaderboard_requires_auth(client):
    response = await client.get("/leaderboard")

    assert response.status_code == 401


@pytest.mark.parametrize("n", [0, -1, 101])
async def test_leaderboard_rejects_invalid_n(client, n):
    headers = await _signup(client, f"lb_invalid_{abs(n)}")

    response = await client.get("/leaderboard", params={"n": n}, headers=headers)

    assert response.status_code == 422


async def test_leaderboard_default_n_works(client):
    headers = await _signup(client, "lb_default")

    response = await client.get("/leaderboard", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) <= 10


async def test_leaderboard_ranks_by_win_ratio(client):
    alice = await _signup(client, "lb_alice")
    bob = await _signup(client, "lb_bob")
    carol = await _signup(client, "lb_carol")
    dave = await _signup(client, "lb_dave")
    eve = await _signup(client, "lb_eve")
    frank = await _signup(client, "lb_frank")

    await _play_human_game(client, alice, bob, X_WINS)    # alice побеждает
    await _play_human_game(client, alice, bob, X_WINS)    # alice побеждает
    await _play_human_game(client, bob, alice, X_WINS)    # bob побеждает
    await _play_human_game(client, carol, dave, DRAW_MOVES)  # ничья
    await _play_human_game(client, eve, frank, X_WINS)    # eve побеждает

    # В dev-БД могут лежать чужие данные, поэтому смотрим только на своих.
    ours = [e for e in await _leaderboard(client, alice) if e["login"].startswith("lb_")]

    # eve 1/1, alice 2/3, bob 1/3, потом нули: при равной доле и равных
    # победах порядок по логину (carol, dave, frank).
    assert [e["login"] for e in ours] == [
        "lb_eve", "lb_alice", "lb_bob", "lb_carol", "lb_dave", "lb_frank",
    ]
    ratios = {e["login"]: e["win_ratio"] for e in ours}
    assert ratios["lb_eve"] == pytest.approx(1.0)
    assert ratios["lb_alice"] == pytest.approx(2 / 3)
    assert ratios["lb_bob"] == pytest.approx(1 / 3)
    assert ratios["lb_carol"] == pytest.approx(0.0)
    assert ratios["lb_frank"] == pytest.approx(0.0)


async def test_leaderboard_entry_has_uuid_and_login(client):
    alice = await _signup(client, "lb_fields_a")
    bob = await _signup(client, "lb_fields_b")
    await _play_human_game(client, alice, bob, X_WINS)
    me = (await client.get("/auth/me", headers=alice)).json()

    entry = next(e for e in await _leaderboard(client, alice) if e["login"] == "lb_fields_a")

    assert entry["user_id"] == me["id"]
    assert set(entry) == {"user_id", "login", "win_ratio"}


async def test_leaderboard_limits_to_n(client):
    alice = await _signup(client, "lb_limit_a")
    bob = await _signup(client, "lb_limit_b")
    await _play_human_game(client, alice, bob, X_WINS)

    response = await client.get("/leaderboard", params={"n": 1}, headers=alice)

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_leaderboard_ignores_unfinished_games(client):
    alice = await _signup(client, "lb_unfinished")
    await client.post("/game", json={"vs_computer": False}, headers=alice)  # ждёт соперника
    await client.post("/game", json={"vs_computer": True}, headers=alice)   # идёт

    assert [e for e in await _leaderboard(client, alice) if e["login"] == "lb_unfinished"] == []


async def test_leaderboard_excludes_computer_but_counts_games_against_it(client):
    alice = await _signup(client, "lb_vs_computer")
    await _play_out_vs_computer(client, alice)  # человек не может обыграть минимакс

    board = await _leaderboard(client, alice)

    assert all(e["user_id"] != NIL_UUID for e in board)
    entry = next(e for e in board if e["login"] == "lb_vs_computer")
    assert entry["win_ratio"] == pytest.approx(0.0)
