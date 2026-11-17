import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Фронтенд ходит в API по относительному адресу /api/...: в разработке его
// проксирует Vite, в продакшене — nginx (см. nginx.conf). Оба срезают
// префикс /api, поэтому бэкенд остаётся без префикса, а для браузера всё —
// один origin, и CORS не нужен.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000", // uvicorn / compose-порт APP_PORT
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
