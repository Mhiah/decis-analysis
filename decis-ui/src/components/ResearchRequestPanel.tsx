import { useState } from "react";
import type { FocusInstrument, ResearchRequest } from "../types/desk";
import {
  isResearchSymbolReady,
  RESEARCH_INBOX,
  type MailProvider,
} from "../lib/researchRequest";

interface ResearchRequestPanelProps {
  readyCount: number;
  instruments: FocusInstrument[];
  requests: ResearchRequest[];
  onRequest: (symbol: string, provider: MailProvider) => void | Promise<void>;
}

function normalizeSymbol(raw: string): string {
  return raw.trim().toUpperCase().replace(/\s+/g, "");
}

const MAIL_CHOICES: Array<{ id: MailProvider; label: string; hint: string }> = [
  {
    id: "gmail",
    label: "Gmail",
    hint: "Open compose in the browser",
  },
  {
    id: "outlook",
    label: "Outlook on the web",
    hint: "Outlook.com / Microsoft 365 compose",
  },
  {
    id: "default",
    label: "Default mail app",
    hint: "Whatever Windows has set (often Outlook)",
  },
];

export function ResearchRequestPanel({
  readyCount,
  instruments,
  requests,
  onRequest,
}: ResearchRequestPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [sending, setSending] = useState(false);
  const [chooserOpen, setChooserOpen] = useState(false);

  const normalized = normalizeSymbol(symbol);
  const alreadyReady =
    normalized.length > 0 && isResearchSymbolReady(normalized, instruments);

  function openChooser() {
    if (!normalized || alreadyReady || sending) return;
    setChooserOpen(true);
  }

  async function chooseProvider(provider: MailProvider) {
    if (!normalized || alreadyReady || sending) return;
    setSending(true);
    setChooserOpen(false);
    try {
      await onRequest(normalized, provider);
      setSymbol("");
    } finally {
      setSending(false);
    }
  }

  return (
    <details className="panel-card chapter fold-section" id="research-request">
      <summary className="fold-summary">
        <span className="eyebrow">Request research</span>
        <span className="section-hint">Ask for a Bitget rToken not on the desk yet</span>
      </summary>

      <div className="fold-body">
        <div className="faq-list research-request-facts">
          <details className="faq-item">
            <summary>Ready now — {readyCount} requests</summary>
            <p>
              <strong>{readyCount}</strong> Bitget rToken research requests are
              already on this desk — pick them from Focus rToken above.
            </p>
          </details>
          <details className="faq-item">
            <summary>Everything else</summary>
            <p>
              The rest of the Bitget stock rToken list is not pre-built. Request
              one when you need it. Up to 3 days, not instant.
            </p>
          </details>
        </div>

        <div className="research-request-controls">
          <label className="selector-label" htmlFor="research-symbol">
            Request rToken
          </label>
          <div className="research-request-row">
            <input
              id="research-symbol"
              className="instrument-select research-symbol-input"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
              placeholder="e.g. NVDA or RNVDAUSDT"
              aria-label="Bitget rToken or ticker to research"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  openChooser();
                }
              }}
            />
            <button
              type="button"
              className="btn btn-dark"
              disabled={!normalized || alreadyReady || sending}
              onClick={openChooser}
            >
              {sending ? "Opening…" : "Request"}
            </button>
          </div>
          {alreadyReady ? (
            <p className="research-request-status">
              That name is already in the ready set of {readyCount} — use Focus
              rToken above.
            </p>
          ) : (
            <p className="research-request-status">
              Up to 3 days, not instant.
            </p>
          )}
        </div>

        {requests.length > 0 ? (
          <>
            <h3 className="playbook-title">Queued requests</h3>
            <ul className="journal-list">
              {requests
                .slice()
                .reverse()
                .map((item) => {
                  const complete =
                    item.status === "completed" ||
                    isResearchSymbolReady(item.symbol, instruments);
                  return (
                    <li key={item.id} className="research-queue-item">
                      <div className="research-queue-main">
                        <strong>{item.symbol}</strong>
                        <span>
                          {complete
                            ? "On Focus rToken"
                            : `Up to ${item.etaDays} days`}{" "}
                          · {new Date(item.at).toLocaleString()}
                        </span>
                      </div>
                      <span
                        className={`request-status-pill ${
                          complete ? "completed" : "pending"
                        }`}
                      >
                        {complete ? "completed" : "pending"}
                      </span>
                    </li>
                  );
                })}
            </ul>
          </>
        ) : null}
      </div>

      {chooserOpen ? (
        <div
          className="mail-chooser-backdrop"
          role="presentation"
          onClick={() => setChooserOpen(false)}
        >
          <div
            className="mail-chooser"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mail-chooser-title"
            onClick={(event) => event.stopPropagation()}
          >
            <p className="eyebrow">Send request</p>
            <h3 id="mail-chooser-title">Choose how to email</h3>
            <p className="mail-chooser-lede">
              To <strong>{RESEARCH_INBOX}</strong> for{" "}
              <strong>{normalized}</strong>
            </p>
            <div className="mail-chooser-list">
              {MAIL_CHOICES.map((choice) => (
                <button
                  key={choice.id}
                  type="button"
                  className="mail-chooser-option"
                  onClick={() => {
                    void chooseProvider(choice.id);
                  }}
                >
                  <span className="mail-chooser-option-label">{choice.label}</span>
                  <span className="mail-chooser-option-hint">{choice.hint}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="btn btn-secondary mail-chooser-cancel"
              onClick={() => setChooserOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </details>
  );
}
