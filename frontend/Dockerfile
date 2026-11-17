FROM node:26-alpine AS base

RUN npm install -g pnpm@12.18.0
WORKDIR /app

# Зависимости — отдельным слоем: он пересобирается, только когда меняются
# манифесты. Кэш pnpm переживает пересборки (нужен BuildKit).
FROM base AS deps
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN --mount=type=cache,id=pnpm,target=/var/cache/pnpm \
    pnpm install --store-dir /var/cache/pnpm --frozen-lockfile

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

# Итоговый образ — только nginx со статикой, без Node и исходников.
# unprivileged-вариант работает не от root и слушает порт 8080.
FROM nginxinc/nginx-unprivileged:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
