import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, NavLink, Navigate, Link } from "react-router-dom";
import DashboardPage from "./components/Dashboard";
import TradeDetailPage from "./components/TradeDetailPage";
import NewTradePage from "./components/NewTradePage";
import TradeRail from "./components/TradeRail";
import Review from "./components/Review";
import "./index.css";

function Shell() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <h1 className="nav-title">Trading Journal</h1>
          <div className="nav-links">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/review">Review</NavLink>
            <Link to="/trade/new" className="btn btn-sm btn-primary">+ New Trade</Link>
            <Link to="/trade/new?mode=retro" className="btn btn-sm btn-ghost">Log retro</Link>
          </div>
        </nav>
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          <main className="main" style={{ flex: 1, padding: 16, overflowY: "auto" }}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/trade/new" element={<NewTradePage />} />
              <Route path="/trade/:id" element={<TradeDetailPage />} />
              <Route path="/review" element={<Review />} />
              <Route path="/plan" element={<Navigate to="/" replace />} />
              <Route path="/trades" element={<Navigate to="/" replace />} />
              <Route path="/analytics" element={<Navigate to="/review" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <TradeRail />
        </div>
      </div>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Shell />
  </React.StrictMode>
);
