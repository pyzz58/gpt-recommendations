import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const apiTarget =
    process.env.CRA_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": apiTarget,
        "/health": apiTarget,
        "/capabilities": apiTarget
      }
    },
    build: {
      sourcemap: true,
      chunkSizeWarningLimit: 900
    }
  };
});
