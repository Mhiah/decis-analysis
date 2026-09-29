import { askQwen } from "./_qwen.js";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "POST only" });
    return;
  }

  let body = req.body || {};
  if (typeof body === "string") {
    try {
      body = JSON.parse(body || "{}");
    } catch {
      res.status(400).json({ ok: false, error: "invalid JSON body" });
      return;
    }
  }
  const { status, body: out } = await askQwen(body);
  res.status(status).json(out);
}
