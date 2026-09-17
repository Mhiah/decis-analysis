import { useMemo, useState } from "react";
import type { DecisionRecord, TicketStub } from "../types/desk";

interface ExecutionAssistProps {
  focus: { eventId: string; ticker: string; token: string };
  decisions: DecisionRecord[];
  tickets: TicketStub[];
  onSaveTicket: (ticket: TicketStub) => void;
}

function statusLabel(status: TicketStub["status"]): string {
  return status === "armed_local" || status === "draft" ? "Saved locally" : status;
}

export function ExecutionAssist({
  focus,
  decisions,
  tickets,
  onSaveTicket,
}: ExecutionAssistProps) {
  const sourceDecisions = useMemo(
    () =>
      decisions.filter(
        (d) =>
          d.eventId === focus.eventId &&
          (d.decision === "IDEA" || d.decision === "REVIEW"),
      ),
    [decisions, focus.eventId],
  );

  const [decisionId, setDecisionId] = useState("");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [sizeUsd, setSizeUsd] = useState("250");
  const [thesis, setThesis] = useState("");

  const activeDecisionId = decisionId || sourceDecisions[0]?.id || "";

  function saveDraft() {
    if (!activeDecisionId) return;
    const size = Number(sizeUsd);
    if (!Number.isFinite(size) || size <= 0) return;

    onSaveTicket({
      id: `${Date.now()}`,
      at: new Date().toISOString(),
      decisionId: activeDecisionId,
      eventId: focus.eventId,
      ticker: focus.ticker,
      token: focus.token,
      side,
      sizeUsd: size,
      thesis: thesis.trim() || `Draft ticket for ${focus.ticker}`,
      status: "draft",
    });
    setThesis("");
  }

  const focusTickets = tickets.filter((t) => t.eventId === focus.eventId);

  return (
    <section className="panel-card chapter" id="execution">
      <p className="eyebrow">Execution support</p>
      <p className="section-hint">Draft a local size ticket — never sent</p>

      <div className="stress-grid decision-meaning-grid">
        <article className="stress-card decision-card hold">
          <p className="stress-label">Not an order</p>
          <p>No API keys and no exchange submit. This is a worksheet, not a fill.</p>
        </article>
        <article className="stress-card decision-card review">
          <p className="stress-label">From Review or Idea</p>
          <p>
            Hold means leave it — no draft. Review or Idea means you’re still
            working the name, so you can jot size.
          </p>
        </article>
        <article className="stress-card decision-card idea">
          <p className="stress-label">Next step</p>
          <p>After you save a draft, use Review &amp; develop to score what happened.</p>
        </article>
      </div>

      {sourceDecisions.length === 0 ? (
        <p className="decision-rec">
          Log a <strong>Review</strong> or <strong>Idea</strong> first, then save
          a draft ticket here.
        </p>
      ) : (
        <div className="exec-form">
          <details className="faq-item desk-fold exec-fold">
            <summary>Linked call</summary>
            <label className="desk-fold-field">
              <span className="visually-hidden">Linked call</span>
              <select
                value={activeDecisionId}
                onChange={(e) => setDecisionId(e.target.value)}
              >
                {sourceDecisions.map((d) => (
                  <option key={d.id} value={d.id}>
                    {new Date(d.at).toLocaleString()} · {d.decision}
                  </option>
                ))}
              </select>
            </label>
          </details>
          <label>
            Side
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as "buy" | "sell")}
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label>
            Size (USD)
            <input
              type="number"
              min="1"
              step="1"
              value={sizeUsd}
              onChange={(e) => setSizeUsd(e.target.value)}
            />
          </label>
          <label className="exec-thesis">
            Thesis note
            <input
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Why this size / side…"
            />
          </label>
          <button type="button" className="btn btn-dark" onClick={saveDraft}>
            Save draft ticket
          </button>
        </div>
      )}

      {focusTickets.length > 0 ? (
        <ul className="journal-list">
          {focusTickets
            .slice()
            .reverse()
            .map((t) => (
              <li key={t.id}>
                <strong>
                  {t.side.toUpperCase()} ${t.sizeUsd} {t.token}
                </strong>
                <span>{statusLabel(t.status)}</span>
                <p>{t.thesis}</p>
              </li>
            ))}
        </ul>
      ) : null}
    </section>
  );
}
