import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Serve /api/ask in `vite dev` with the same Qwen handler Vercel uses.
function qwenAskDev(env: Record<string, string>): Plugin {
  return {
    name: "decis-qwen-ask-dev",
    configureServer(server) {
      server.middlewares.use("/api/ask", async (req, res) => {
        const chunks: Buffer[] = [];
        for await (const chunk of req) chunks.push(chunk as Buffer);
        let payload = {};
        try {
          payload = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
        } catch {
          // askQwen answers 400 for an empty payload.
        }
        const modulePath = new URL("./api/_qwen.js", import.meta.url).href;
        const { askQwen } = await import(/* @vite-ignore */ modulePath);
        const { status, body } = await askQwen(payload, { ...process.env, ...env });
        res.statusCode = status;
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(body));
      });
    },
  };
}

// Proxy live quotes to the local Bitget sidecar (desk/live_quotes.py).
export default defineConfig(({ mode }) => ({
  plugins: [react(), qwenAskDev(loadEnv(mode, process.cwd(), ""))],
  server: {
    proxy: {
      "/api/live": {
        target: "http://127.0.0.1:8788",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/live/, ""),
      },
    },
  },
}));
