import { useMemo, useState } from "react";
import type {
  DecisionRecord,
  DevelopmentLesson,
  FocusInstrument,
  PostTradeReview,
  StressTest,
} from "../types/desk";

interface DeskLoopReviewProps {
  focus: FocusInstrument;
  stress: StressTest;
  decisions: DecisionRecord[];
  reviews: PostTradeReview[];
  lessons: DevelopmentLesson[];
  onSaveReview: (review: PostTradeReview) => void;
  onPromoteLesson: (review: PostTradeReview) => void;
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

export function DeskLoopReview({
  focus,
  stress,
  decisions,
  reviews,
  lessons,
  onSaveReview,
  onPromoteLesson,
}: DeskLoopReviewProps) {
  const reviewable = useMemo(
    () =>
      decisions.filter(
        (d) =>
          d.eventId === focus.eventId &&
          (d.decision === "IDEA" || d.decision === "REVIEW"),
      ),
    [decisions, focus.eventId],
  );

  const [decisionId, setDecisionId] = useState("");
  const [outcome, setOutcome] =
    useState<PostTradeReview["outcome"]>("unclear");
  const [whatHappened, setWhatHappened] = useState("");
  const [lesson, setLesson] = useState("");

  const activeId = decisionId || reviewable[0]?.id || "";
  const pathNote = `Event path: first ${pct(focus.firstReturn)} → 180m ${pct(
    focus.horizonReturn,
  )} (${focus.direction} surprise).`;

  const focusReviews = reviews.filter((r) => r.eventId === focus.eventId);
  const promotedIds = new Set(lessons.map((l) => l.fromReviewId));

  function save() {
    if (!activeId) return;
    onSaveReview({
      id: `${Date.now()}`,
      at: new Date().toISOString(),
      decisionId: activeId,
      eventId: focus.eventId,
      ticker: focus.ticker,
      outcome,
      whatHappened:
        whatHappened.trim() ||
        `${pathNote} Review against the logged call using desk evidence only.`,
      vsInvalidation: stress.invalidation[0] ?? "No invalidation listed.",
      lesson: lesson.trim() || "Capture one concrete lesson next time.",
    });
    setWhatHappened("");
    setLesson("");
  }

  return (
    <section className="panel-card chapter" id="posttrade">
      <p className="eyebrow">Review &amp; self-development</p>
      <p className="section-hint">What happened, and what you’ll keep</p>

      <div className="stress-grid decision-meaning-grid">
        <article className="stress-card bull">
          <p className="stress-label">Evidence now</p>
          <p>{pathNote}</p>
        </article>
        <article className="stress-card bear">
          <p className="stress-label">Invalidation check</p>
          <p>{stress.invalidation[0]}</p>
        </article>
        <article className="stress-card invalidate">
          <p className="stress-label">Playbook</p>
          <p>Promote a review lesson so the next Idea starts wiser.</p>
        </article>
      </div>

      {reviewable.length === 0 ? (
        <p className="decision-rec">
          Log a <strong>Review</strong> or <strong>Idea</strong> first, then
          score how the thesis held up.
        </p>
      ) : (
        <div className="exec-form">
          <details className="faq-item desk-fold exec-fold">
            <summary>Logged call</summary>
            <label className="desk-fold-field">
              <span className="visually-hidden">Logged call</span>
              <select
                value={activeId}
                onChange={(e) => setDecisionId(e.target.value)}
              >
                {reviewable.map((d) => (
                  <option key={d.id} value={d.id}>
                    {new Date(d.at).toLocaleString()} · {d.decision}
                  </option>
                ))}
              </select>
            </label>
          </details>
          <label>
            Outcome
            <select
              value={outcome}
              onChange={(e) =>
                setOutcome(e.target.value as PostTradeReview["outcome"])
              }
            >
              <option value="supported">Supported</option>
              <option value="weakened">Weakened</option>
              <option value="invalidated">Invalidated</option>
              <option value="unclear">Unclear</option>
            </select>
          </label>
          <label className="exec-thesis">
            What happened
            <input
              value={whatHappened}
              onChange={(e) => setWhatHappened(e.target.value)}
              placeholder="Path vs thesis in one line…"
            />
          </label>
          <label className="exec-thesis">
            Lesson to keep
            <input
              value={lesson}
              onChange={(e) => setLesson(e.target.value)}
              placeholder="What will you do differently…"
            />
          </label>
          <button type="button" className="btn btn-primary" onClick={save}>
            Save review
          </button>
        </div>
      )}

      {focusReviews.length > 0 ? (
        <ul className="journal-list">
          {focusReviews
            .slice()
            .reverse()
            .map((r) => (
              <li key={r.id}>
                <strong>
                  {r.ticker} · {r.outcome}
                </strong>
                <span>{new Date(r.at).toLocaleString()}</span>
                <p>{r.whatHappened}</p>
                <p className="journal-lesson">{r.lesson}</p>
                {promotedIds.has(r.id) ? (
                  <span className="meta-pill">In playbook</span>
                ) : (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => onPromoteLesson(r)}
                  >
                    Promote to playbook
                  </button>
                )}
              </li>
            ))}
        </ul>
      ) : null}

      {lessons.length > 0 ? (
        <>
          <h3 className="playbook-title">Playbook</h3>
          <ul className="journal-list playbook">
            {lessons
              .slice()
              .reverse()
              .map((l) => (
                <li key={l.id}>
                  <strong>
                    {l.ticker} · {l.tag}
                  </strong>
                  <span>{new Date(l.at).toLocaleString()}</span>
                  <p>{l.lesson}</p>
                </li>
              ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
