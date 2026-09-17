import type { StressTest } from "../types/desk";

interface StressTestPanelProps {
  stress: StressTest;
}

export function StressTestPanel({ stress }: StressTestPanelProps) {
  return (
    <section className="panel-card stress-panel chapter" id="stress">
      <p className="eyebrow">Decision stress-testing</p>
      <p className="section-hint">Argue both sides before you commit</p>
      <div className="stress-grid">
        <article className="stress-card bull">
          <p className="stress-label">Bull case</p>
          <p>{stress.bullCase}</p>
        </article>
        <article className="stress-card bear">
          <p className="stress-label">Bear case</p>
          <p>{stress.bearCase}</p>
        </article>
        <article className="stress-card invalidate">
          <p className="stress-label">Invalidation</p>
          <ul>
            {stress.invalidation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>
      <p className="advisory-note">{stress.advisoryNote}</p>
    </section>
  );
}
