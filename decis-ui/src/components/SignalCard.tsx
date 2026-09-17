import type { SignalRead } from "../types/desk";

interface SignalCardProps {
  signal: SignalRead;
}

export function SignalCard({ signal }: SignalCardProps) {
  const rows = [
    { key: "Material", value: signal.material, tone: "bull" },
    { key: "Changed", value: signal.changed, tone: "bear" },
    { key: "Implies", value: signal.implies, tone: "invalidate" },
  ];

  return (
    <section className="panel-card signal-card chapter" id="signals">
      <p className="eyebrow">Signal generation</p>
      <p className="section-hint">What the evidence means</p>
      <div className="stress-grid">
        {rows.map((row) => (
          <article key={row.key} className={`stress-card ${row.tone}`}>
            <p className="stress-label">{row.key}</p>
            <p>{row.value}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
