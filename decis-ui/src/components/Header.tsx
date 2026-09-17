interface HeaderProps {
  activeSection: string;
  onNavigate: (section: string) => void;
}

const LINKS = [
  { id: "workstation", label: "Event" },
  { id: "trading-desk", label: "Trading Desk" },
  { id: "honesty", label: "FAQ" },
];

export function Header({ activeSection, onNavigate }: HeaderProps) {
  return (
    <header className="site-header">
      <div className="brand-lockup">
        <span className="brand-mark" aria-hidden="true" />
        <div>
          <p className="brand-name">Decis Analysis</p>
          <p className="brand-sub">AI Trading Desk</p>
        </div>
      </div>

      <nav className="nav-capsule" aria-label="Primary">
        {LINKS.map((link) => (
          <button
            key={link.id}
            type="button"
            className={activeSection === link.id ? "nav-link active" : "nav-link"}
            onClick={() => onNavigate(link.id)}
          >
            {link.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
