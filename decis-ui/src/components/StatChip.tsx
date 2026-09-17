import type { CSSProperties } from "react";
import type { ConfidenceChip } from "../types/desk";

interface StatChipProps {
  chip: ConfidenceChip;
  className?: string;
  style?: CSSProperties;
}

export function StatChip({ chip, className = "", style }: StatChipProps) {
  return (
    <div className={`stat-chip tone-${chip.tone ?? "neutral"} ${className}`} style={style}>
      <span className="stat-chip-label">{chip.label}</span>
      <strong className="stat-chip-value">{chip.value}</strong>
    </div>
  );
}
