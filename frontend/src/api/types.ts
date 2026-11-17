// Типы повторяют ответы бэкенда (web/model/response_model.py).

export type GameStatus = "WAITING_FOR_PLAYER" | "PLAYER_TURN" | "DRAW" | "WIN";

/** Клетка: 0 — пусто, 1 — X, -1 — O. */
export type Cell = -1 | 0 | 1;
export type Grid = Cell[][];

export interface Game {
  id: string;
  board: { grid: Grid };
  player_x_id: string;
  player_o_id: string | null;
  vs_computer: boolean;
  state: {
    status: GameStatus;
    /** Чей ход (PLAYER_TURN) или победитель (WIN). */
    player_id?: string | null;
  };
  created_at: string;
}

export interface Tokens {
  accessToken: string;
  refreshToken: string;
}

export interface User {
  id: string;
  login: string;
}
