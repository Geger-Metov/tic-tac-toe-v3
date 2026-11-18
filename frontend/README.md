# frontend

React 19 + TypeScript + Vite. Вход, регистрация и игра с компьютером. Общая картина — в корневом `README.md`.

```bash
pnpm install
pnpm dev          # http://localhost:5173, /api проксируется на localhost:8000 (см. vite.config.ts)
pnpm typecheck    # tsc -b
pnpm lint         # eslint
pnpm format       # prettier --write .
pnpm build        # typecheck + сборка в dist/
```

- `src/api/` — клиент API (`client.ts`: токены в localStorage, единое обновление при 401) и типы ответов.
- `src/auth/` — контекст авторизации; `src/components/` — формы, доска, экран игры.
- Прод-образ (`Dockerfile`): сборка в Node, раздача nginx, `/api/*` проксируется на `app`.
