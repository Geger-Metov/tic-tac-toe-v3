import { defineConfig, devices } from "@playwright/test";

// Тесты ходят в уже запущенный стек (nginx + app + db + redis): локально это
// `docker compose up`, в CI — задание docker. Своего webServer здесь нет, потому
// что без бэкенда фронтенд проверять не на чем.
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:8080";
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 2 : undefined,
  reporter: isCI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    locale: "ru-RU",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
