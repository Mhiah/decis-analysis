import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { FocusInstrument, GeneratedDeskView } from "../types/desk";
import { AiSummaryCard } from "./AiSummaryCard";

interface WorkstationProps {
  instruments: FocusInstrument[];
  selectedEventId: string;
  view: GeneratedDeskView;
  onSelect: (eventId: string) => void;
  children?: ReactNode;
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function pathAgrees(focus: FocusInstrument): boolean {
  return (
    (focus.direction === "positive" && (focus.horizonReturn ?? 0) > 0) ||
    (focus.direction === "negative" && (focus.horizonReturn ?? 0) < 0)
  );
}

function clockLabel(focus: FocusInstrument): string {
  return focus.timestampSemantics.replace(/_/g, " ").toUpperCase();
}

export function Workstation({
  instruments,
  selectedEventId,
  view,
  onSelect,
  children,
}: WorkstationProps) {
  const { focus, aiSummary } = view;
  const aligned = pathAgrees(focus);
  const pathTone =
    (focus.horizonReturn ?? 0) > 0
      ? "tone-up"
      : (focus.horizonReturn ?? 0) < 0
        ? "tone-down"
        : "";
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  const selected =
    instruments.find((item) => item.eventId === selectedEventId) ??
    instruments[0];

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <section className="workstation" id="workstation">
      <div className="workstation-hero">
        <h1>
          Turn evidence into <em>a clear call.</em>
        </h1>
        <p className="trust-line">RESEARCH ONLY · YOU KEEP THE CALL</p>

        <div className="hero-controls">
          <label className="selector-label" htmlFor="instrument-select">
            Focus rToken
          </label>
          <div className="instrument-picker" ref={wrapRef}>
            <button
              id="instrument-select"
              type="button"
              className="instrument-select instrument-select-trigger"
              aria-haspopup="listbox"
              aria-expanded={open}
              aria-controls={listId}
              onClick={() => setOpen((value) => !value)}
            >
              {selected
                ? `${selected.ticker} · ${selected.token}`
                : "Select rToken"}
            </button>
            {open ? (
              <ul
                id={listId}
                className="instrument-menu"
                role="listbox"
                aria-label="Focus rToken"
              >
                {instruments.map((item) => {
                  const active = item.eventId === selectedEventId;
                  return (
                    <li key={item.eventId} role="presentation">
                      <button
                        type="button"
                        role="option"
                        aria-selected={active}
                        className={
                          active
                            ? "instrument-option active"
                            : "instrument-option"
                        }
                        onClick={() => {
                          onSelect(item.eventId);
                          setOpen(false);
                        }}
                      >
                        {item.ticker} · {item.token}
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
        </div>
      </div>

      <div className="desk-layout">
        <div className="workstation-main">
          <aside className="evidence-panel" aria-label="Event evidence">
            <div className="evidence-panel-head">
              <div>
                <p className="eyebrow">Event evidence</p>
                <h2>
                  {focus.ticker} · {focus.token}
                </h2>
              </div>
              <span className="meta-pill">{focus.importance.toUpperCase()}</span>
            </div>

            <dl className="evidence-grid">
              <div>
                <dt>Surprise</dt>
                <dd className="tabular">{pct(focus.surprise)}</dd>
                <p className="evidence-hint">
                  {focus.direction} · print vs expectations
                </p>
              </div>
              <div>
                <dt>180m path</dt>
                <dd className={`tabular ${pathTone}`}>
                  {pct(focus.horizonReturn)}
                </dd>
                <p className="evidence-hint">
                  {aligned ? "Agrees with surprise" : "Diverges from surprise"}
                </p>
              </div>
              <div className="evidence-clock">
                <dt>Event clock</dt>
                <dd>{clockLabel(focus)}</dd>
                <p className="evidence-hint">
                  {focus.issuerClockValidated
                    ? "Issuer release time validated"
                    : "SEC acceptance fallback · not issuer wire time"}
                </p>
              </div>
            </dl>

            <p className="live-footnote">
              Frozen research snapshot · news vs absorption vs clock quality
            </p>
          </aside>

          <AiSummaryCard
            summary={aiSummary}
            focusLabel={`${focus.ticker} / ${focus.token}`}
          />
        </div>

        {children}
      </div>
    </section>
  );
}
