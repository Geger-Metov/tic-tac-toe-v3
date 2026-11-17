import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { Game, Grid, User } from "../api/types";
import { Board } from "./Board";

const GAME_KEY = "ttt.game"; // id текущей партии: на бэкенде пока нет «моих активных игр»

function storedGameId(): string | null {
  try {
    return localStorage.getItem(GAME_KEY);
  } catch {
    return null;
  }
}

function storeGameId(id: string | null): void {
  try {
    if (id === null) localStorage.removeItem(GAME_KEY);
    else localStorage.setItem(GAME_KEY, id);
  } catch {
    /* ignore */
  }
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return error.message;
    if (error.status === 409)
      return "Ход не принят: партия уже изменилась. Доска обновлена.";
    if (error.status === 400) return "Ход не принят. Доска обновлена.";
  }
  return "Что-то пошло не так. Попробуйте ещё раз.";
}

function statusText(game: Game | null, user: User, busy: boolean): string {
  if (game === null) return "Начните партию";
  const { status, player_id } = game.state;
  if (status === "WIN")
    return player_id === user.id ? "Вы победили!" : "Победил компьютер";
  if (status === "DRAW") return "Ничья";
  if (busy) return "Компьютер отвечает…";
  return player_id === user.id ? "Ваш ход" : "Ход компьютера";
}

export function GamePage({
  user,
  onLogout,
}: {
  user: User;
  onLogout: () => void;
}) {
  const [game, setGame] = useState<Game | null>(null);
  // Загружаем партию только если id сохранён с прошлого раза.
  const [loading, setLoading] = useState(() => storedGameId() !== null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Продолжаем партию, начатую до перезагрузки страницы.
  useEffect(() => {
    let cancelled = false;
    const id = storedGameId();
    if (id === null) return;
    api
      .getGame(id)
      .then((g) => {
        if (!cancelled && g.vs_computer && g.player_x_id === user.id)
          setGame(g);
        else if (!cancelled) storeGameId(null);
      })
      .catch((e) => {
        // Игры нет или она чужая — забываем; при сетевой ошибке тоже не страшно.
        if (e instanceof ApiError && (e.status === 404 || e.status === 403))
          storeGameId(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user.id]);

  const startGame = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createGameVsComputer();
      storeGameId(created.id);
      setGame(created);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const myTurn =
    game !== null &&
    game.state.status === "PLAYER_TURN" &&
    game.state.player_id === user.id;

  const onCellClick = async (row: number, col: number) => {
    if (game === null || busy || !myTurn || game.board.grid[row][col] !== 0)
      return;

    const previous = game;
    // Игрок — создатель партии, то есть X (1). Рисуем свой ход сразу, не ждём ответа.
    const grid: Grid = game.board.grid.map((r) => [...r]);
    grid[row][col] = 1;
    setGame({ ...game, board: { grid } });
    setBusy(true);
    setError(null);

    try {
      // В ответе уже есть ответ компьютера.
      setGame(await api.makeMove(game.id, grid));
    } catch (e) {
      setGame(previous);
      setError(describeError(e));
      if (e instanceof ApiError && (e.status === 400 || e.status === 409)) {
        try {
          setGame(await api.getGame(previous.id));
        } catch {
          /* оставляем откат к предыдущему состоянию */
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const finished =
    game !== null &&
    (game.state.status === "WIN" || game.state.status === "DRAW");
  const emptyGrid: Grid = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];

  return (
    <div className="page">
      <header className="topbar">
        <span className="who">{user.login}</span>
        <button type="button" className="link" onClick={onLogout}>
          Выйти
        </button>
      </header>

      <main className="game">
        <h1
          className={`status${finished ? " status-final" : ""}`}
          aria-live="polite"
        >
          {loading ? "Загрузка…" : statusText(game, user, busy)}
        </h1>

        <Board
          grid={game?.board.grid ?? emptyGrid}
          interactive={myTurn && !busy}
          onCellClick={onCellClick}
        />

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {!loading && (
          <button
            type="button"
            className="primary"
            onClick={startGame}
            disabled={busy}
          >
            {game === null ? "Играть с компьютером" : "Новая партия"}
          </button>
        )}
        {!loading && game === null && (
          <p className="hint">Вы играете крестиками и ходите первым.</p>
        )}
      </main>
    </div>
  );
}
