import type { ConfidenceChip } from "../types/desk";

interface ConfidenceGaugeProps {
  chips: ConfidenceChip[];
  score: number;
}

/** Radial-style confidence card from evidence quality — not a trading edge claim. */
export function ConfidenceGauge({ chips, score }: ConfidenceGaugeProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const radius = 54;
  const circ = 2 * Math.PI * radius;
  const filled = (clamped / 100) * circ;

  return (
    <article className="dash-card gauge-card">
      <p className="dash-card-label">Read quality</p>
      <div className="gauge-wrap">
        <svg viewBox="0 0 140 140" className="gauge-svg" aria-hidden="true">
          <circle cx="70" cy="70" r={radius} className="gauge-track" />
          <circle
            cx="70"
            cy="70"
            r={radius}
            className="gauge-progress"
            style={{
              strokeDasharray: `${filled} ${circ}`,
            }}
          />
        </svg>
        <div className="gauge-center">
          <strong className="gauge-score tabular">{clamped}</strong>
          <span>evidence</span>
        </div>
      </div>
      <ul className="gauge-chips">
        {chips.slice(0, 3).map((chip) => (
          <li key={chip.id} className={`tone-${chip.tone ?? "neutral"}`}>
            <span>{chip.label}</span>
            <strong className="tabular">{chip.value}</strong>
          </li>
        ))}
      </ul>
    </article>
  );
}
