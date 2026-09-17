interface ThemesStripProps {
  onNavigate: (section: string) => void;
}

const THEMES = [
  {
    id: "workstation",
    step: "01",
    title: "Workstation",
    blurb: "Focus an rToken and read the evidence beside you.",
  },
  {
    id: "signals",
    step: "02",
    title: "Signal generation",
    blurb: "Material, changed, and what it implies.",
  },
  {
    id: "stress",
    step: "03",
    title: "Decision stress-testing",
    blurb: "Bull, bear, and invalidation before you commit.",
  },
  {
    id: "execution",
    step: "04",
    title: "Execution support",
    blurb: "Draft a local size ticket — never sent.",
  },
  {
    id: "posttrade",
    step: "05",
    title: "Review & self-development",
    blurb: "Score the call and keep the lesson.",
  },
];

export function ThemesStrip({ onNavigate }: ThemesStripProps) {
  return (
    <section className="themes-strip" aria-label="Desk stages">
      {THEMES.map((theme, index) => (
        <button
          key={theme.id}
          type="button"
          className="theme-card"
          style={{ animationDelay: `${index * 60}ms` }}
          onClick={() => onNavigate(theme.id)}
        >
          <span className="theme-step">{theme.step}</span>
          <h3>{theme.title}</h3>
          <p>{theme.blurb}</p>
        </button>
      ))}
    </section>
  );
}
