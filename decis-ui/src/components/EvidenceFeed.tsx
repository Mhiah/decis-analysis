import type { EvidenceItem } from "../types/desk";

interface EvidenceFeedProps {
  items: EvidenceItem[];
}

export function EvidenceFeed({ items }: EvidenceFeedProps) {
  return (
    <div className="evidence-feed">
      <p className="eyebrow">Evidence feed</p>
      <ul>
        {items.map((item) => (
          <li key={item.id} className={`evidence-item kind-${item.kind}`}>
            <div>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </div>
            {item.cite ? <span className="cite">{item.cite}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
