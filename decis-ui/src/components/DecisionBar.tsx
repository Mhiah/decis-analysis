import type { DecisionKind, DecisionRecord } from "../types/desk";

interface DecisionBarProps {
  decisions: DecisionRecord[];
  focusEventId: string;
  disabled?: boolean;
  onDecide: (decision: DecisionKind, note: string) => void;
}

const ACTIONS: Array<{
  kind: DecisionKind;
  label: string;
  meaning: string;
  tone: string;
}> = [
  {
    kind: "HOLD",
    label: "Hold",
    meaning: "Stay flat. Evidence isn’t enough — leave it.",
    tone: "hold",
  },
  {
    kind: "REVIEW",
    label: "Review",
    meaning: "Watchlist. Interesting, not actionable yet.",
    tone: "review",
  },
  {
    kind: "IDEA",
    label: "Idea",
    meaning: "Log for later human work — still not an order.",
    tone: "idea",
  },
];

export function DecisionBar({
  decisions,
  focusEventId,
  disabled,
  onDecide,
}: DecisionBarProps) {
  const focusLog = decisions
    .filter((d) => d.eventId === focusEventId)
    .slice()
    .reverse();

  return (
    <section className="panel-card decision-panel chapter" id="decision">
      <p className="eyebrow">Personalized research workstation</p>
      <p className="section-hint">Pick a verdict</p>

      <div className="verdict-strip" role="group" aria-label="Decision verdicts">
        {ACTIONS.map((action) => (
          <button
            key={action.kind}
            type="button"
            className={`verdict-card ${action.tone}`}
            disabled={disabled}
            onClick={() => onDecide(action.kind, "")}
          >
            <span className="verdict-label">{action.label}</span>
            <span className="verdict-meaning">{action.meaning}</span>
          </button>
        ))}
      </div>

      <p className="advisory-note">
        Research audit only — never sent to Bitget.
      </p>

      <details className="faq-item desk-fold">
        <summary>Decision journal</summary>
        {focusLog.length === 0 ? (
          <p className="decision-rec">No calls logged for this focus yet.</p>
        ) : (
          <ul className="journal-list">
            {focusLog.map((item) => (
              <li key={item.id}>
                <strong>
                  {item.decision}
                  {item.ticker ? ` · ${item.ticker}` : ""}
                </strong>
                <span>{new Date(item.at).toLocaleString()}</span>
                {item.note ? <p className="journal-lesson">{item.note}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}
