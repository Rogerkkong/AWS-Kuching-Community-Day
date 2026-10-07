import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev only: `npm run dev` proxies /api and /health to a running local API
// (start it with `python -m app.desktop --browser` and set VITE_API=http://127.0.0.1:<port>).
const api = process.env.VITE_API ?? "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  build: { outDir: "dist", emptyOutDir: true, assetsInlineLimit: 0, chunkSizeWarningLimit: 900 },
  server: { proxy: { "/api": api, "/health": api } },
});
