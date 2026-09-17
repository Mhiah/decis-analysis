import type {
  DecisionRecord,
  DevelopmentLesson,
  PostTradeReview,
  ResearchRequest,
  TicketStub,
} from "../types/desk";

const KEYS = {
  decisions: "decis.journal.decisions",
  tickets: "decis.journal.tickets",
  reviews: "decis.journal.reviews",
  lessons: "decis.journal.lessons",
  researchRequests: "decis.journal.researchRequests",
} as const;
function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function loadDecisions(): DecisionRecord[] {
  return read(KEYS.decisions, []);
}

export function saveDecisions(items: DecisionRecord[]) {
  write(KEYS.decisions, items);
}

export function loadTickets(): TicketStub[] {
  return read(KEYS.tickets, []);
}

export function saveTickets(items: TicketStub[]) {
  write(KEYS.tickets, items);
}

export function loadReviews(): PostTradeReview[] {
  return read(KEYS.reviews, []);
}

export function saveReviews(items: PostTradeReview[]) {
  write(KEYS.reviews, items);
}

export function loadLessons(): DevelopmentLesson[] {
  return read(KEYS.lessons, []);
}

export function saveLessons(items: DevelopmentLesson[]) {
  write(KEYS.lessons, items);
}

export function loadResearchRequests(): ResearchRequest[] {
  const items = read<Array<ResearchRequest & { status?: string }>>(
    KEYS.researchRequests,
    [],
  );
  return items.map((item) => ({
    ...item,
    status:
      item.status === "complete" || item.status === "completed"
        ? "completed"
        : "pending",
  }));
}

export function saveResearchRequests(items: ResearchRequest[]) {
  write(KEYS.researchRequests, items);
}

/** Wipe all local journal keys (decisions, tickets, reviews, lessons, research queue). */
export function clearJournal() {
  for (const key of Object.values(KEYS)) {
    localStorage.removeItem(key);
  }
}

/**
 * If the URL has ?reset=1, clear the journal once and strip the param.
 * Use for a clean demo slate in whatever browser origin you're on.
 */
export function consumeDemoReset(): boolean {
  if (typeof window === "undefined") return false;
  const url = new URL(window.location.href);
  if (!url.searchParams.has("reset")) return false;
  clearJournal();
  url.searchParams.delete("reset");
  const next = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState({}, "", next);
  return true;
}