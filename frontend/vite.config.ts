import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ command }) => ({
  // Base diferente para desenvolvimento e build
  base: command === "build" ? "/static/frontend/" : "/",
  appType: "spa",
  define: {
    __BUILD_ID__: JSON.stringify(process.env.RENDER_GIT_COMMIT || new Date().toISOString()),
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../static/frontend"),
    emptyOutDir: true,
    sourcemap: true,
  },
  publicDir: path.resolve(__dirname, "public"),
}));
