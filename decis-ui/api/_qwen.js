// Qwen (Alibaba Cloud Model Studio) grounded Ask. Shared by the Vercel route
// (api/ask.js) and the Vite dev middleware. Files prefixed with _ are not routes.
//
// Env:
//   DASHSCOPE_API_KEY  required; Model Studio API key
//   QWEN_MODEL         optional; default qwen-plus
//   QWEN_BASE_URL      optional; default international OpenAI-compatible endpoint

const DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
const DEFAULT_MODEL = "qwen-plus";
const MAX_QUESTION = 500;

const SYSTEM_PROMPT = [
  "You are the Ask panel of Decis Analysis, a research desk for Bitget stock rTokens around earnings.",
  "Answer ONLY from the DESK JSON the user message provides. Never use outside knowledge, prices, news, or forecasts.",
  "If the desk objects do not contain the answer, say so plainly and suggest what the desk can answer.",
  "Never recommend placing, sizing, or timing an order. Hold / Review / Idea are research audit actions, not trades.",
  "Never claim a proven trading edge; the desk posture is strategyEdgeValidated: false.",
  "Keep answers to at most 4 sentences.",
  'Reply as JSON: {"answer": string, "cites": string[]} where each cite is one of the ALLOWED CITES keys you actually used.',
].join(" ");

/** Keys a Qwen answer may cite; mirrors the deterministic askDesk cites. */
export function allowedCites(desk) {
  const cites = [
    "aiSummary",
    "signal.material",
    "signal.changed",
    "signal.implies",
    "signal.confidenceNotes",
    "stress.thesisSummary",
    "stress.bullCase",
    "stress.bearCase",
    "stress.invalidation",
    "stress.advisoryNote",
    "focus.timestampSemantics",
    "focus.issuerClockValidated",
    "focus.tradeBlockers",
  ];
  for (const item of desk?.evidence ?? []) {
    if (item && typeof item.id === "string") cites.push(`evidence.${item.id}`);
  }
  return cites;
}

function pickDesk(desk) {
  const { focus = {}, signal = {}, stress = {}, evidence = [], aiSummary = "" } = desk ?? {};
  return {
    focus: {
      ticker: focus.ticker,
      token: focus.token,
      publishedAt: focus.publishedAt,
      timestampSemantics: focus.timestampSemantics,
      issuerClockValidated: focus.issuerClockValidated,
      direction: focus.direction,
      surprise: focus.surprise,
      importance: focus.importance,
      horizonReturn: focus.horizonReturn,
      firstReturn: focus.firstReturn,
      tradeBlockers: focus.tradeBlockers,
    },
    signal,
    stress,
    evidence: evidence.map(({ id, kind, title, detail }) => ({ id, kind, title, detail })),
    aiSummary,
  };
}

/**
 * Returns { status, body }. body is { ok, answer, cites, model } on success,
 * or { ok: false, error } so the client can keep its deterministic answer.
 */
export async function askQwen({ question, desk }, env = process.env, fetchImpl = fetch) {
  const apiKey = env.DASHSCOPE_API_KEY;
  if (!apiKey) {
    return { status: 503, body: { ok: false, error: "Qwen not configured (DASHSCOPE_API_KEY unset)" } };
  }
  const q = typeof question === "string" ? question.trim().slice(0, MAX_QUESTION) : "";
  if (!q || !desk || typeof desk !== "object") {
    return { status: 400, body: { ok: false, error: "question and desk are required" } };
  }

  const model = env.QWEN_MODEL || DEFAULT_MODEL;
  const baseUrl = (env.QWEN_BASE_URL || DEFAULT_BASE_URL).replace(/\/+$/, "");
  const allowed = allowedCites(desk);
  const userContent = [
    `QUESTION: ${q}`,
    `ALLOWED CITES: ${JSON.stringify(allowed)}`,
    `DESK JSON: ${JSON.stringify(pickDesk(desk))}`,
  ].join("\n\n");

  let upstream;
  try {
    upstream = await fetchImpl(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        temperature: 0.2,
        max_tokens: 400,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userContent },
        ],
      }),
    });
  } catch (err) {
    return { status: 502, body: { ok: false, error: err instanceof Error ? err.message : "Qwen fetch failed" } };
  }

  const data = await upstream.json().catch(() => null);
  if (!upstream.ok) {
    const msg = data?.error?.message || data?.message || `Qwen HTTP ${upstream.status}`;
    return { status: 502, body: { ok: false, error: msg } };
  }

  let parsed;
  try {
    parsed = JSON.parse(data?.choices?.[0]?.message?.content ?? "");
  } catch {
    return { status: 502, body: { ok: false, error: "Qwen reply was not JSON" } };
  }
  const answer = typeof parsed?.answer === "string" ? parsed.answer.trim() : "";
  if (!answer) {
    return { status: 502, body: { ok: false, error: "Qwen reply had no answer" } };
  }
  // Drop any cite the model invented; the desk only shows cites it can back.
  const cites = Array.isArray(parsed.cites)
    ? [...new Set(parsed.cites.filter((c) => allowed.includes(c)))]
    : [];

  return { status: 200, body: { ok: true, answer, cites, model: data?.model || model } };
}
