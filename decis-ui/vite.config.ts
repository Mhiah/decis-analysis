import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy live quotes to the local Bitget sidecar (desk/live_quotes.py).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/live": {
        target: "http://127.0.0.1:8788",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/live/, ""),
      },
    },
  },
});
