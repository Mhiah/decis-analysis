import type { GeneratedDeskView } from "../types/desk";

export interface AskReply {
  question: string;
  answer: string;
  cites: string[];
  /** "desk" = deterministic template; "qwen" = Qwen grounded on the same objects. */
  source?: "desk" | "qwen";
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

/** Constrained NL answers — only from structured desk objects, no free invention. */
export function askDesk(view: GeneratedDeskView, rawQuestion: string): AskReply {
  const q = rawQuestion.trim().toLowerCase();
  const { focus, signal, stress, aiSummary } = view;
  const ticker = focus.ticker;

  if (!q) {
    return {
      question: rawQuestion,
      answer:
        "Ask about the AI summary, bull/bear case, invalidation, Hold vs Review, or the event clock.",
      cites: [],
    };
  }

  if (/ai summary|desk note|how to read|summary/.test(q) && !/thesis/.test(q)) {
    return {
      question: rawQuestion,
      answer: aiSummary,
      cites: ["aiSummary"],
    };
  }

  if (/bear|oppos|against/.test(q)) {
    return {
      question: rawQuestion,
      answer: stress.bearCase,
      cites: ["stress.bearCase"],
    };
  }

  if (/invalid|kill|wrong|break/.test(q)) {
    return {
      question: rawQuestion,
      answer: stress.invalidation.join(" "),
      cites: ["stress.invalidation"],
    };
  }

  if (/bull|upside|long|supportive/.test(q)) {
    return {
      question: rawQuestion,
      answer: stress.bullCase,
      cites: ["stress.bullCase"],
    };
  }

  if (/thesis|one.?line/.test(q)) {
    return {
      question: rawQuestion,
      answer: stress.thesisSummary,
      cites: ["stress.thesisSummary"],
    };
  }

  if (/imply|implies|posture|hold|review|idea|call|decide/.test(q)) {
    return {
      question: rawQuestion,
      answer: `${signal.implies} ${stress.advisoryNote} For ${ticker}: Hold = leave it; Review = watchlist; Idea = log for later. None are orders.`,
      cites: ["signal.implies", "stress.advisoryNote"],
    };
  }

  if (/clock|edgar|issuer|time|when/.test(q)) {
    return {
      question: rawQuestion,
      answer: `${ticker} clock is ${focus.timestampSemantics.replace(/_/g, " ")}${
        focus.issuerClockValidated
          ? " (issuer validated)."
          : " (EDGAR acceptance fallback, not issuer wire time)."
      }`,
      cites: ["focus.timestampSemantics", "focus.issuerClockValidated"],
    };
  }

  if (/chang|after print|first print|path|material|matter|surpris|evidence/.test(q)) {
    return {
      question: rawQuestion,
      answer:
        "Those facts are in Event evidence and Signal generation on the desk. Ask for the AI summary, bull/bear, invalidation, or Hold vs Review instead.",
      cites: ["desk.redirect_to_panels"],
    };
  }

  return {
    question: rawQuestion,
    answer:
      "I only answer from this focus’s desk objects. Try: AI summary, bear case, invalidation, bull case, Hold vs Review, or event clock.",
    cites: ["desk.refuse_unsupported"],
  };
}

/**
 * Ask Qwen (via /api/ask) over the same structured desk objects.
 * Returns null when Qwen is not configured or fails, so the caller keeps the
 * deterministic answer.
 */
export async function askQwen(
  view: GeneratedDeskView,
  question: string,
  signal?: AbortSignal,
): Promise<AskReply | null> {
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
    if (!res.ok) return null;
    const data = (await res.json()) as {
      ok?: boolean;
      answer?: string;
      cites?: string[];
      model?: string;
    };
    if (!data.ok || !data.answer) return null;
    return {
      question,
      answer: data.answer,
      cites: data.cites ?? [],
      source: "qwen",
      model: data.model,
    };
  } catch {
    return null;
  }
}

export { PROMPTS as ASK_PROMPTS };
