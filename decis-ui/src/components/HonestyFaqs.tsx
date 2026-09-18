const FAQS = [
  {
    q: "Is this proven alpha?",
    a: "No. Decis surfaces research and stress-tests a thesis. Hold / Review / Idea are your calls, not a claimed edge.",
  },
  {
    q: "What’s the difference between Hold, Review, and Idea?",
    a: "Hold means leave it. Review means watchlist: interesting, not actionable yet. Idea means log it for later human work. None of them are exchange orders.",
  },
  {
    q: "Does the live ticker drive the signal?",
    a: "No. Live quotes are market context only. Signal, stress-test, and Ask answers come from the research snapshot, not the live ticker.",
  },
  {
    q: "How often do research packages update?",
    a: "A GitHub Action polls SEC about every 3 hours, enriches Bitget candles when it can, and rebuilds the desk snapshot. Surprise still needs a pre-event consensus row; without it Surprise shows as —.",
  },
  {
    q: "What is EDGAR acceptance?",
    a: "The SEC timestamp when a filing was accepted. Used as the event clock (t=0) when a precise issuer press-release time isn’t validated. Usually slightly later than true distribution.",
  },
  {
    q: "What does the 180m path mean?",
    a: "The rToken’s return from the event clock through the first ~180 minutes. It shows whether the market absorbed the surprise or fought it, separate from the live Bitget quote.",
  },
  {
    q: "Can Decis place a Bitget order?",
    a: "No. Execution support only drafts a local size ticket in your browser. No API keys, no submit, no fills.",
  },
];

export function HonestyFaqs() {
  return (
    <details className="panel-card honesty-panel chapter fold-section" id="honesty">
      <summary className="fold-summary">
        <span className="eyebrow">FAQ</span>
        <span className="section-hint">Questions a skeptic asks first</span>
      </summary>
      <div className="fold-body faq-list">
        {FAQS.map((item) => (
          <details key={item.q} className="faq-item">
            <summary>{item.q}</summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </details>
  );
}
