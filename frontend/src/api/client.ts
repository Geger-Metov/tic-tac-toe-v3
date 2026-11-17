import type { Game, Grid, Tokens, User } from "./types";

const BASE = "/api";
const ACCESS_KEY = "ttt.access";
const REFRESH_KEY = "ttt.refresh";

export class ApiError extends Error {
  readonly status: number;
  /** Секунд до следующей попытки (из заголовка Retry-After при 429). */
  readonly retryAfter?: number;

  constructor(status: number, message: string, retryAfter?: number) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

// ---- хранилище токенов ------------------------------------------------------
// localStorage может быть недоступен (приватный режим, запрет сайта) — тогда
// просто работаем без сохранения между перезагрузками.

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* хранилище недоступно */
  }
}

export const tokenStore = {
  access: () => read(ACCESS_KEY),
  refresh: () => read(REFRESH_KEY),
  has: () => read(ACCESS_KEY) !== null && read(REFRESH_KEY) !== null,
  save(tokens: Tokens) {
    write(ACCESS_KEY, tokens.accessToken);
    write(REFRESH_KEY, tokens.refreshToken);
  },
  clear() {
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
  },
  accessKey: ACCESS_KEY,
};

let authLostHandler: (() => void) | null = null;
/** Вызывается, когда сессию не удалось продлить: пора показать форму входа. */
export function setAuthLostHandler(handler: (() => void) | null): void {
  authLostHandler = handler;
}

// ---- обновление токенов -----------------------------------------------------
// Refresh-токен одноразовый: бэкенд сразу выдаёт новую пару, а старый
// отзывает. Поэтому два параллельных обновления (несколько запросов с
// протухшим access или две вкладки) нельзя пускать одновременно — второе
// получило бы 401 и разлогинило пользователя.
//  - внутри вкладки все ждут один общий запрос (inflight);
//  - между вкладками обновления выстраиваются в очередь через Web Locks, а
//    опоздавший видит уже новый access-токен и не обновляет повторно.

let inflight: Promise<boolean> | null = null;

async function doRefresh(staleAccess: string | null): Promise<boolean> {
  const current = tokenStore.access();
  if (current !== null && current !== staleAccess) return true; // уже обновили

  const refreshToken = tokenStore.refresh();
  if (refreshToken === null) return false;

  // Сетевая ошибка здесь намеренно не перехватывается: она уходит наверх как
  // «нет связи», а сессия не сбрасывается — сервер ведь ничего не отклонял.
  const res = await fetch(`${BASE}/auth/token/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
  });
  if (!res.ok) return false;
  tokenStore.save((await res.json()) as Tokens);
  return true;
}

function refreshTokens(staleAccess: string | null): Promise<boolean> {
  if (inflight === null) {
    const run = () => doRefresh(staleAccess);
    const task =
      "locks" in navigator
        ? navigator.locks.request("ttt-token-refresh", run)
        : run();
    inflight = task.finally(() => {
      inflight = null;
    });
  }
  return inflight;
}

// ---- запросы ----------------------------------------------------------------

async function toApiError(res: Response): Promise<ApiError> {
  let message = `Ошибка ${res.status}`;
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") message = body.detail;
  } catch {
    /* тело не JSON — оставляем общее сообщение */
  }
  const retry = Number(res.headers.get("Retry-After"));
  return new ApiError(
    res.status,
    message,
    Number.isFinite(retry) && retry > 0 ? retry : undefined,
  );
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  /** false — запрос без токена (вход, регистрация). */
  auth?: boolean;
}

async function request<T>(
  path: string,
  { method = "GET", body, auth = true }: RequestOptions = {},
): Promise<T> {
  const send = (token: string | null) =>
    fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token !== null ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let res: Response;
  const usedToken = auth ? tokenStore.access() : null;
  try {
    res = await send(usedToken);
    if (auth && res.status === 401) {
      if (await refreshTokens(usedToken)) {
        res = await send(tokenStore.access());
      }
      if (res.status === 401) {
        tokenStore.clear();
        authLostHandler?.();
      }
    }
  } catch {
    throw new ApiError(
      0,
      "Нет связи с сервером. Проверьте подключение и попробуйте ещё раз.",
    );
  }

  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

// ---- методы API -------------------------------------------------------------

export const api = {
  async signup(login: string, password: string): Promise<void> {
    await request("/auth/signup", {
      method: "POST",
      body: { login, password },
      auth: false,
    });
  },

  async login(login: string, password: string): Promise<void> {
    const tokens = await request<Tokens>("/auth/login", {
      method: "POST",
      body: { login, password },
      auth: false,
    });
    tokenStore.save(tokens);
  },

  me: () => request<User>("/auth/me"),

  createGameVsComputer: () =>
    request<Game>("/game", { method: "POST", body: { vs_computer: true } }),

  getGame: (id: string) => request<Game>(`/game/${id}`),

  /** Бэкенд принимает доску целиком и сам находит единственное изменение.
   *  В ответе уже есть ответный ход компьютера. */
  makeMove: (id: string, grid: Grid) =>
    request<Game>(`/game/${id}`, {
      method: "PATCH",
      body: { board: { grid } },
    }),
};
