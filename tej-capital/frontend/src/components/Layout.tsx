import { Outlet } from "react-router-dom";
import { Nav } from "./Nav";
import "../design/components.css";

export function Layout() {
  return (
    <div className="app-shell">
      <Nav />
      <div className="app-shell__main">
        <header className="app-shell__header">
          <span className="app-shell__header-title">Fund Console</span>
        </header>
        <main className="app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
