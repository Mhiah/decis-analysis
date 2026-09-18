import { useEffect, useMemo, useState } from "react";
import { Header } from "./components/Header";
import { Workstation } from "./components/Workstation";
import { ThemesStrip } from "./components/ThemesStrip";
import { SignalCard } from "./components/SignalCard";
import { StressTestPanel } from "./components/StressTestPanel";
import { DecisionBar } from "./components/DecisionBar";
import { AskDesk } from "./components/AskDesk";
import { LiveQuotesPanel } from "./components/LiveQuotesPanel";
import { ExecutionAssist } from "./components/ExecutionAssist";
import { DeskLoopReview } from "./components/DeskLoopReview";
import { HonestyFaqs } from "./components/HonestyFaqs";
import { ResearchRequestPanel } from "./components/ResearchRequestPanel";
import { generateDeskView, loadDeskSnapshot } from "./lib/deskData";
import {
  consumeDemoReset,
  loadDecisions,
  loadLessons,
  loadResearchRequests,
  loadReviews,
  loadTickets,
  saveDecisions,
  saveLessons,
  saveResearchRequests,
  saveReviews,
  saveTickets,
} from "./lib/deskJournal";
import { isResearchSymbolReady, submitResearchRequest } from "./lib/researchRequest";
import type { MailProvider } from "./lib/researchRequest";
import type {
  DecisionKind,
  DecisionRecord,
  DeskSnapshot,
  DevelopmentLesson,
  PostTradeReview,
  ResearchRequest,
  TicketStub,
} from "./types/desk";
import "./App.css";

// Clean slate when opened with ?reset=1 (before React state hydrates from localStorage)
consumeDemoReset();

export default function App() {
  const [snapshot, setSnapshot] = useState<DeskSnapshot | null>(null);
  const [selectedEventId, setSelectedEventId] = useState("");
  const [activeSection, setActiveSection] = useState("workstation");
  const [decisions, setDecisions] = useState<DecisionRecord[]>(() => loadDecisions());
  const [tickets, setTickets] = useState<TicketStub[]>(() => loadTickets());
  const [reviews, setReviews] = useState<PostTradeReview[]>(() => loadReviews());
  const [lessons, setLessons] = useState<DevelopmentLesson[]>(() => loadLessons());
  const [researchRequests, setResearchRequests] = useState<ResearchRequest[]>(
    () => loadResearchRequests(),
  );
  const [toast, setToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    loadDeskSnapshot()
      .then((data) => {
        if (!alive) return;
        setSnapshot(data);
        setSelectedEventId(data.instruments[0]?.eventId ?? "");
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load desk");
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => saveDecisions(decisions), [decisions]);
  useEffect(() => saveTickets(tickets), [tickets]);
  useEffect(() => saveReviews(reviews), [reviews]);
  useEffect(() => saveLessons(lessons), [lessons]);
  useEffect(() => saveResearchRequests(researchRequests), [researchRequests]);

  useEffect(() => {
    if (!snapshot) return;
    setResearchRequests((prev) => {
      let changed = false;
      const next = prev.map((item) => {
        const complete = isResearchSymbolReady(item.symbol, snapshot.instruments);
        const status = complete ? "completed" : "pending";
        if (item.status === status) return item;
        changed = true;
        return { ...item, status };
      });
      return changed ? next : prev;
    });
  }, [snapshot]);

  const view = useMemo(() => {
    if (!snapshot || !selectedEventId) return null;
    return generateDeskView(snapshot, selectedEventId);
  }, [snapshot, selectedEventId]);

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2800);
  }

  function handleDecide(decision: DecisionKind, note: string) {
    if (!selectedEventId || !view) return;
    const record: DecisionRecord = {
      id: `${Date.now()}`,
      at: new Date().toISOString(),
      decision,
      eventId: selectedEventId,
      ticker: view.focus.ticker,
      token: view.focus.token,
      note: note || undefined,
    };
    setDecisions((prev) => [...prev, record]);
    showToast(`Logged ${decision} — not sent to exchange.`);
  }

  function handleSaveTicket(ticket: TicketStub) {
    setTickets((prev) => [...prev, ticket]);
    showToast("Draft ticket saved — not sent to Bitget.");
  }

  function handleSaveReview(review: PostTradeReview) {
    setReviews((prev) => [...prev, review]);
    showToast("Post-trade review saved locally.");
  }

  function handlePromoteLesson(review: PostTradeReview) {
    const lesson: DevelopmentLesson = {
      id: `${Date.now()}`,
      at: new Date().toISOString(),
      ticker: review.ticker,
      fromReviewId: review.id,
      lesson: review.lesson,
      tag: review.outcome,
    };
    setLessons((prev) => [...prev, lesson]);
    showToast("Lesson promoted to playbook.");
  }

  async function handleResearchRequest(symbol: string, provider: MailProvider) {
    const result = await submitResearchRequest(symbol, provider);
    const record: ResearchRequest = {
      id: `${Date.now()}`,
      at: result.at || new Date().toISOString(),
      symbol: result.symbol,
      status: "pending",
      etaDays: result.etaDays || 3,
    };
    setResearchRequests((prev) => [...prev, record]);
    showToast(`${result.symbol} — finish Send in ${result.provider}.`);
  }

  function handleNavigate(section: string) {
    setActiveSection(section);
    document.getElementById(section)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (loading) {
    return <div className="boot-state">Loading Decis Analysis…</div>;
  }

  if (error || !snapshot || !view) {
    return <div className="boot-state error">{error ?? "No desk data"}</div>;
  }

  return (
    <div className="app-shell">
      <Header
        activeSection={activeSection}
        onNavigate={handleNavigate}
      />

      <main>
        <Workstation
          instruments={snapshot.instruments}
          selectedEventId={selectedEventId}
          view={view}
          onSelect={setSelectedEventId}
        >
          <LiveQuotesPanel
            symbol={view.focus.token}
            ticker={view.focus.ticker}
          />
        </Workstation>
        <h2 className="trading-desk-title" id="trading-desk">
          Trading Desk
        </h2>
        <div className="desk-body-layout">
          <ThemesStrip onNavigate={handleNavigate} />
          <div className="desk-body-main">
            <SignalCard signal={view.signal} />
            <StressTestPanel stress={view.stress} />
            <AskDesk view={view} />
            <DecisionBar
              decisions={decisions}
              focusEventId={selectedEventId}
              onDecide={handleDecide}
            />
            <ExecutionAssist
              focus={view.focus}
              decisions={decisions}
              tickets={tickets}
              onSaveTicket={handleSaveTicket}
            />
            <DeskLoopReview
              focus={view.focus}
              stress={view.stress}
              decisions={decisions}
              reviews={reviews}
              lessons={lessons}
              onSaveReview={handleSaveReview}
              onPromoteLesson={handlePromoteLesson}
            />
            <HonestyFaqs />
            <ResearchRequestPanel
              readyCount={snapshot.instruments.length}
              instruments={snapshot.instruments}
              requests={researchRequests}
              onRequest={handleResearchRequest}
            />
          </div>
        </div>
      </main>

      <footer className="site-endmark" aria-label="Hackathon mark">
        BITGET AI HACKATHON S2
      </footer>

      {toast ? <div className="toast">{toast}</div> : null}
    </div>
  );
}
