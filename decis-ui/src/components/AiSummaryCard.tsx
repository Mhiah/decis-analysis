import { useEffect, useState } from "react";

interface AiSummaryCardProps {
  summary: string;
  focusLabel: string;
}

export function AiSummaryCard({ summary, focusLabel }: AiSummaryCardProps) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setExpanded(false);
  }, [summary, focusLabel]);

  return (
    <article className={`ai-summary-card${expanded ? " is-expanded" : ""}`}>
      <div className="ai-summary-top">
        <p className="eyebrow">AI summary</p>
        <span className="focus-label">{focusLabel}</span>
      </div>
      <p className="ai-summary-body">{summary}</p>
      <button
        type="button"
        className="ai-summary-more"
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? "See less" : "See more"}
      </button>
    </article>
  );
}
