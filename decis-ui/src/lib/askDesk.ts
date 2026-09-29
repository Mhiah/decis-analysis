import type { GeneratedDeskView } from "../types/desk";

export interface AskReply {
  question: string;
  answer: string;
  cites: string[];
  model?: string;
}

const PROMPTS = [
  "What’s the AI summary?",
  "What’s the bear case?",
  "What would invalidate this?",
  "What’s the bull case?",
  "Why Hold vs Review?",
  "What’s the event clock?",
];

export type QwenResult = { reply: AskReply } | { error: string };

/**
 * Ask Qwen (via /api/ask) over the structured desk objects only.
 * On failure returns a short reason for the caller to show.
 */
export async function askQwen(
  view: GeneratedDeskView,
  question: string,
  signal?: AbortSignal,
): Promise<QwenResult> {
  try {
    const { focus, signal: read, stress, evidence, aiSummary } = view;
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        desk: { focus, signal: read, stress, evidence, aiSummary },
      }),
      signal,
    });
    const data = (await res.json().catch(() => null)) as {
      ok?: boolean;
      answer?: string;
      cites?: string[];
      model?: string;
      error?: string;
    } | null;
    if (!res.ok || !data?.ok || !data.answer) {
      return { error: data?.error ?? `HTTP ${res.status}` };
    }
    return {
      reply: {
        question,
        answer: data.answer,
        cites: data.cites ?? [],
        model: data.model,
      },
    };
  } catch (err) {
    return { error: err instanceof Error ? err.message : "request failed" };
  }
}

export { PROMPTS as ASK_PROMPTS };
