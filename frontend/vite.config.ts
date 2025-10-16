import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://127.0.0.1:8001",
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
});
