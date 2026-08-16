import { Link } from "react-router-dom";
import "../design/components.css";

export type EmptyStateCta = { label: string; to: string };

export type EmptyStateProps = {
  title: string;
  body: string;
  cta?: EmptyStateCta;
};

/**
 * Centered, ink-3 text. Never says "no data" — always says what to do next
 * (Product Brief §4.1). Used both as the generic empty-state affordance and
 * as the scaffold placeholder for pages that don't yet have real content.
 */
export function EmptyState({ title, body, cta }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      <p className="empty-state__body">{body}</p>
      {cta && (
        <Link className="btn btn--primary empty-state__cta" to={cta.to}>
          {cta.label}
        </Link>
      )}
    </div>
  );
}

/**
 * The canonical first-use empty state — the ONE screen that carries the
 * whole product (Product Brief §4.1). Copy is verbatim; never reword it.
 */
export function NoMarksYetEmptyState() {
  return (
    <EmptyState
      title="No marks yet"
      body="Enter today's closing equity and your record begins."
    />
  );
}
