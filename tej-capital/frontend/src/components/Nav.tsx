import { NavLink } from "react-router-dom";
import "../design/components.css";

const currentMonth = new Date().toISOString().slice(0, 7);

const LINKS: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Today", end: true },
  { to: "/trades/new", label: "Trade Entry" },
  { to: "/ledger", label: "Ledger" },
  { to: "/performance", label: "Performance" },
  { to: "/rhythm", label: "Rhythm" },
  { to: "/monthly", label: "Monthly" },
  { to: "/attribution", label: "Attribution" },
  { to: "/policy", label: "Policy" },
  { to: "/accounts", label: "Accounts" },
  { to: "/audit", label: "Audit" },
  { to: `/tearsheet/${currentMonth}`, label: "Tearsheet" },
  { to: "/settings", label: "Settings" },
];

export function Nav() {
  return (
    <nav className="nav" aria-label="Primary">
      <div className="nav__brand">
        T<span className="nav__brand-mark" aria-hidden="true">&amp;</span>M CAPITAL
      </div>
      <ul className="nav__list">
        {LINKS.map((link) => (
          <li key={link.label}>
            <NavLink
              to={link.to}
              end={link.end}
              className={({ isActive }) => clsxNav(isActive)}
            >
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function clsxNav(isActive: boolean) {
  return isActive ? "nav__link nav__link--active" : "nav__link";
}
