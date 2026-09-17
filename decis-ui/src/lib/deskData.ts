import type {
  DeskSnapshot,
  EvidenceItem,
  FocusInstrument,
  GeneratedDeskView,
  SignalRead,
  StressTest,
  ConfidenceChip,
} from "../types/desk";

function pct(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

/** Placeholder snapshot — used only if `/desk_snapshot.json` is missing. */
export const PLACEHOLDER_SNAPSHOT: DeskSnapshot = {
  product: "Decis Analysis",
  track: "AI Trading Desk",
  tagline: "AI processes the research. You make the call.",
  updatedAt: "2026-09-16T00:30:40.454840+00:00",
  posture: {
    strategyEdgeValidated: false,
    calibrationSuccessful: true,
    paperExecutionValidated: false,
    refusalReasons: [
      "CHALLENGER_MEAN_NET_NOT_POSITIVE",
      "FAILED_TO_BEAT_ALL_BASELINES",
      "CHALLENGER_TOOK_ZERO_TRADES",
    ],
    paperRefusalReasons: ["HISTORICAL_BID_ASK_UNAVAILABLE"],
    holdoutDirectionAccuracy: 0.5,
    holdoutMae: 0.04,
  },
  instruments: [
    {
      eventId: "sec-0000002488-26-000121",
      ticker: "AMD",
      token: "RAMDUSDT",
      publishedAt: "2026-08-04T20:15:00+00:00",
      timestampSemantics: "press_release_distribution",
      issuerClockValidated: true,
      direction: "positive",
      surprise: 0.0159,
      importance: "medium",
      horizonReturn: -0.1034,
      firstReturn: -0.0899,
      tradeBlockers: [
        "IMPACT_MODEL_NOT_CALIBRATED",
        "HISTORICAL_QUOTES_UNAVAILABLE",
      ],
      path: [
        { t: 3, ret: -0.02 },
        { t: 15, ret: -0.05 },
        { t: 45, ret: -0.08 },
        { t: 90, ret: -0.095 },
        { t: 180, ret: -0.103 },
      ],
    },
    {
      eventId: "sec-0001628280-26-048078",
      ticker: "JPM",
      token: "RJPMUSDT",
      publishedAt: "2026-07-14T10:30:38+00:00",
      timestampSemantics: "edgar_acceptance",
      issuerClockValidated: false,
      direction: "positive",
      surprise: 0.0295,
      importance: "high",
      horizonReturn: -0.0155,
      firstReturn: 0.0023,
      tradeBlockers: [
        "IMPACT_MODEL_NOT_CALIBRATED",
        "HISTORICAL_QUOTES_UNAVAILABLE",
      ],
      path: [
        { t: 4, ret: 0.002 },
        { t: 30, ret: -0.004 },
        { t: 90, ret: -0.01 },
        { t: 180, ret: -0.015 },
      ],
    },
    {
      eventId: "sec-0001652044-26-000066",
      ticker: "GOOGL",
      token: "RGOOGLUSDT",
      publishedAt: "2026-07-22T20:01:36+00:00",
      timestampSemantics: "edgar_acceptance",
      issuerClockValidated: false,
      direction: "positive",
      surprise: 0.0436,
      importance: "high",
      horizonReturn: -0.0366,
      firstReturn: -0.0199,
      tradeBlockers: [
        "IMPACT_MODEL_NOT_CALIBRATED",
        "HISTORICAL_QUOTES_UNAVAILABLE",
      ],
      path: [
        { t: 5, ret: -0.02 },
        { t: 40, ret: -0.028 },
        { t: 120, ret: -0.034 },
        { t: 180, ret: -0.037 },
      ],
    },
  ],
};

export async function loadDeskSnapshot(): Promise<DeskSnapshot> {
  // Prefer frozen event snapshot (desk/build_desk_snapshot.py → public/desk_snapshot.json).
  // Live API swap later: fetch("/api/desk/snapshot")
  try {
    const res = await fetch("/desk_snapshot.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`snapshot HTTP ${res.status}`);
    const data = (await res.json()) as DeskSnapshot;
    if (!data.instruments?.length) throw new Error("snapshot has no instruments");
    return data;
  } catch {
    return PLACEHOLDER_SNAPSHOT;
  }
}

export function buildSignal(focus: FocusInstrument): SignalRead {
  const first = pct(focus.firstReturn);
  const horizon = pct(focus.horizonReturn);
  const aligned = pathAgrees(focus);
  const faded =
    focus.firstReturn != null &&
    focus.horizonReturn != null &&
    Math.abs(focus.horizonReturn) < Math.abs(focus.firstReturn);

  return {
    material: aligned
      ? `Surprise direction and 180m absorption line up for ${focus.ticker} — the print is usable as a coherent research read.`
      : `Surprise direction and 180m absorption conflict for ${focus.ticker} — the print alone is not a clean story.`,
    changed: faded
      ? `After the first print (${first}), the path faded toward ${horizon} by the 180m mark — initial reaction did not hold.`
      : `From first print (${first}) to 180m (${horizon}), the path ${
          aligned ? "held with the surprise direction" : "kept fighting the surprise direction"
        }.`,
    implies: aligned
      ? "Posture: Review if you have a thesis — still your call, not an Idea by default."
      : "Posture: Hold / keep researching — do not chase the print against the path.",
    confidenceNotes: [],
  };
}

function pathAgrees(focus: FocusInstrument): boolean {
  return (
    (focus.direction === "positive" && (focus.horizonReturn ?? 0) > 0) ||
    (focus.direction === "negative" && (focus.horizonReturn ?? 0) < 0)
  );
}

export function buildStress(focus: FocusInstrument): StressTest {
  const aligned = pathAgrees(focus);

  return {
    thesisSummary: aligned
      ? `${focus.ticker}: surprise and 180m path agree — advisory Review posture, not an order.`
      : `${focus.ticker}: surprise and 180m path diverge — advisory Hold / keep researching.`,
    bullCase: aligned
      ? `Surprise direction and 180m path agree for ${focus.ticker}; a discretionary Review could watch for continuation.`
      : `If the ${focus.direction} surprise was slow to show up in the rToken, a later move toward that direction is still possible — watch, don’t assume.`,
    bearCase: aligned
      ? `Agreement can reverse quickly; a sharp snapback through the first print would weaken the local read.`
      : `Price already moved ${pct(focus.horizonReturn)} while surprise was ${focus.direction} — chasing now fights the observed path.`,
    invalidation: [
      `If the 60–180m path extends further against the ${focus.direction} surprise, drop the idea.`,
      "If the event clock or surprise figure looks wrong after a re-check, restart the read.",
      "If you cannot state a clear invalidation price or time, stay on Hold.",
    ],
    advisoryNote: "Advisory desk only — log Hold / Review / Idea; no exchange ticket is sent.",
  };
}

export function buildEvidence(focus: FocusInstrument): EvidenceItem[] {
  return [
    {
      id: "surprise",
      kind: "surprise",
      title: "Primary surprise",
      detail: `${pct(focus.surprise)} · ${focus.direction} · importance ${focus.importance}`,
      cite: "earnings",
    },
    {
      id: "path",
      kind: "path",
      title: "180m observed path",
      detail: `First ${pct(focus.firstReturn)} → horizon ${pct(focus.horizonReturn)}`,
      cite: "path",
    },
    {
      id: "clock",
      kind: "clock",
      title: "Event clock",
      detail: `${focus.timestampSemantics}${focus.issuerClockValidated ? " · validated" : ""}`,
      cite: "clock",
    },
  ];
}

export function buildChips(focus: FocusInstrument): ConfidenceChip[] {
  return [
    {
      id: "surprise",
      label: "Surprise",
      value: pct(focus.surprise),
      tone: focus.direction === "positive" ? "positive" : "caution",
    },
    {
      id: "path",
      label: "180m",
      value: pct(focus.horizonReturn),
      tone: (focus.horizonReturn ?? 0) >= 0 ? "positive" : "caution",
    },
    {
      id: "clock",
      label: "Clock",
      value: focus.issuerClockValidated ? "issuer" : "EDGAR",
      tone: focus.issuerClockValidated ? "positive" : "neutral",
    },
    {
      id: "align",
      label: "Align",
      value: pathAgrees(focus) ? "agree" : "diverge",
      tone: pathAgrees(focus) ? "positive" : "caution",
    },
  ];
}

export function evidenceConfidenceScore(focus: FocusInstrument): number {
  let score = 42;
  if (focus.issuerClockValidated) score += 18;
  if (pathAgrees(focus)) score += 18;
  if (focus.importance === "high") score += 8;
  if (focus.surprise != null && Math.abs(focus.surprise) >= 0.02) score += 6;
  if (!pathAgrees(focus)) score -= 8;
  return Math.max(18, Math.min(88, score));
}

/** Desk note — interpretation, not a restate of the evidence panel numbers. */
export function buildAiSummary(focus: FocusInstrument): string {
  const aligned = pathAgrees(focus);
  const faded =
    focus.firstReturn != null &&
    focus.horizonReturn != null &&
    Math.abs(focus.horizonReturn) < Math.abs(focus.firstReturn);
  const extended =
    focus.firstReturn != null &&
    focus.horizonReturn != null &&
    Math.abs(focus.horizonReturn) > Math.abs(focus.firstReturn) * 1.15;

  const parts: string[] = [];

  if (aligned) {
    parts.push(
      `For ${focus.ticker}, the print and the rToken are telling the same story so far — that coherence can justify a Review watchlist, not an automatic Idea.`,
    );
  } else {
    parts.push(
      `For ${focus.ticker}, the print and the rToken disagree. Chasing the surprise fights the observed path; default to Hold until something in the evidence changes.`,
    );
  }

  if (faded) {
    parts.push(
      "The first reaction also faded into the 180m horizon, so the open print is weak confirmation at best.",
    );
  } else if (extended && aligned) {
    parts.push(
      "The move extended after the first print, which strengthens the local read — still only advisory.",
    );
  }

  if (!focus.issuerClockValidated) {
    parts.push(
      "Clock is EDGAR acceptance, not a validated issuer wire time, so treat t=0 as slightly soft when you weigh the path.",
    );
  } else {
    parts.push(
      "Issuer clock is validated, so the path timing is on firmer ground than an EDGAR-only event.",
    );
  }

  parts.push(
    "Decis stops at the note — Hold, Review, or Idea stays your call, and nothing is sent to Bitget.",
  );

  return parts.join(" ");
}

export function generateDeskView(
  snapshot: DeskSnapshot,
  eventId: string,
): GeneratedDeskView {
  const focus =
    snapshot.instruments.find((item) => item.eventId === eventId) ??
    snapshot.instruments[0];

  const signal = buildSignal(focus);
  const stress = buildStress(focus);

  return {
    focus,
    signal,
    stress,
    evidence: buildEvidence(focus),
    chips: buildChips(focus),
    confidenceScore: evidenceConfidenceScore(focus),
    aiSummary: buildAiSummary(focus),
  };
}
