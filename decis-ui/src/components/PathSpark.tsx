import type { FocusInstrument } from "../types/desk";

interface PathSparkProps {
  path: FocusInstrument["path"];
}

export function PathSpark({ path }: PathSparkProps) {
  if (!path.length) {
    return <div className="path-spark empty">No path</div>;
  }

  const width = 320;
  const height = 120;
  const pad = 10;
  const xs = path.map((p) => p.t);
  const ys = path.map((p) => p.ret);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 0);
  const sx = (t: number) =>
    pad + ((t - minX) / (maxX - minX || 1)) * (width - pad * 2);
  const sy = (v: number) =>
    height - pad - ((v - minY) / (maxY - minY || 1)) * (height - pad * 2);
  const d = path
    .map((point, index) => `${index === 0 ? "M" : "L"} ${sx(point.t)} ${sy(point.ret)}`)
    .join(" ");

  return (
    <svg className="path-spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Return path">
      <line
        x1={pad}
        x2={width - pad}
        y1={sy(0)}
        y2={sy(0)}
        className="zero-line"
      />
      <path d={d} className="path-line" fill="none" />
    </svg>
  );
}
