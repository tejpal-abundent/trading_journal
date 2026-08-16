import type { ReactNode } from "react";
import "../design/components.css";

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="section-header">
      <h2 className="section-header__title">{title}</h2>
      {action && <div className="section-header__action">{action}</div>}
    </div>
  );
}
