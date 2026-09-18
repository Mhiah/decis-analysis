/** Swappable desk data contracts — replace adapters with live API later. */

export type DecisionKind = "HOLD" | "REVIEW" | "IDEA";

export interface ConfidenceChip {
  id: string;
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "caution" | "critical";
}

export interface EvidenceItem {
  id: string;
  kind: "surprise" | "path" | "clock" | "consensus" | "blocker" | "gate";
  title: string;
  detail: string;
  cite?: string;
}

export interface SignalRead {
  material: string;
  changed: string;
  implies: string;
  confidenceNotes: string[];
}

export interface StressTest {
  thesisSummary: string;
  bullCase: string;
  bearCase: string;
  invalidation: string[];
  advisoryNote: string;
}

export type ResearchStatus = "ready" | "pending_surprise" | "pending_path";

export interface FocusInstrument {
  eventId: string;
  ticker: string;
  token: string;
  publishedAt: string;
  timestampSemantics: string;
  issuerClockValidated: boolean;
  direction: "positive" | "negative" | "neutral" | string;
  surprise: number | null;
  importance: string;
  horizonReturn: number | null;
  firstReturn: number | null;
  tradeBlockers: string[];
  path: Array<{ t: number; ret: number }>;
  /** Optional: incomplete packages from scheduled SEC refresh. */
  researchStatus?: ResearchStatus;
}

export interface DeskPosture {
  strategyEdgeValidated: boolean;
  calibrationSuccessful: boolean;
  paperExecutionValidated: boolean;
  refusalReasons: string[];
  paperRefusalReasons: string[];
  holdoutDirectionAccuracy: number | null;
  holdoutMae: number | null;
}

export interface DeskSnapshot {
  product: string;
  track: string;
  tagline: string;
  updatedAt: string | null;
  schemaVersion?: string;
  posture: DeskPosture;
  instruments: FocusInstrument[];
  gates?: {
    events: number;
    issuerClocksValidated: number;
    immutableConsensus: number;
    calibration: string;
    paper: string;
    live: string;
    researchSource?: string;
  };
}

export interface DecisionRecord {
  id: string;
  at: string;
  decision: DecisionKind;
  eventId: string;
  ticker?: string;
  token?: string;
  note?: string;
}

/** Local execution ticket stub — never submitted to an exchange. */
export interface TicketStub {
  id: string;
  at: string;
  decisionId: string;
  eventId: string;
  ticker: string;
  token: string;
  side: "buy" | "sell";
  sizeUsd: number;
  thesis: string;
  status: "draft" | "armed_local";
}

/** Local post-trade review against desk evidence (not a broker fill). */
export interface PostTradeReview {
  id: string;
  at: string;
  decisionId: string;
  eventId: string;
  ticker: string;
  outcome: "supported" | "weakened" | "invalidated" | "unclear";
  whatHappened: string;
  vsInvalidation: string;
  lesson: string;
}

export interface DevelopmentLesson {
  id: string;
  at: string;
  ticker: string;
  fromReviewId: string;
  lesson: string;
  tag: string;
}

/** Local queue for a Bitget rToken research package not yet on the desk. */
export interface ResearchRequest {
  id: string;
  at: string;
  symbol: string;
  note?: string;
  status: "pending" | "completed";
  etaDays: number;
}

/** Shape returned by AI signal generation (local or API). */
export interface GeneratedDeskView {
  focus: FocusInstrument;
  signal: SignalRead;
  stress: StressTest;
  evidence: EvidenceItem[];
  chips: ConfidenceChip[];
  aiSummary: string;
  /** 0–100 evidence-quality score for the gauge (not a trading edge). */
  confidenceScore: number;
}
