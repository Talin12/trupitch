import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-server config. The `/api` proxy forwards every frontend request
// to the local FastAPI server (must be running separately on :8000),
// so the SPA can call relative /api/... paths without hitting CORS —
// though in practice this codebase calls the API via the absolute
// API_BASE constant (see src/types.ts), so this proxy mostly matters
// if that's ever changed to relative URLs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
