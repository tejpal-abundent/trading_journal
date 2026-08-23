import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/query";
import { Layout } from "./components/Layout";
import Today from "./pages/Today";
import TradeEntry from "./pages/TradeEntry";
import Ledger from "./pages/Ledger";
import Performance from "./pages/Performance";
import Rhythm from "./pages/Rhythm";
import Monthly from "./pages/Monthly";
import Attribution from "./pages/Attribution";
import Policy from "./pages/Policy";
import Accounts from "./pages/Accounts";
import Audit from "./pages/Audit";
import Tearsheet from "./pages/Tearsheet";
import Settings from "./pages/Settings";
import Allocator from "./pages/Allocator";

import "./design/reset.css";
import "./design/tokens.css";
import "./design/typography.css";
import "./design/components.css";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/tej-capital">
        <Routes>
          <Route path="/share/:token" element={<Allocator />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Today />} />
            <Route path="/trades/new" element={<TradeEntry />} />
            <Route path="/ledger" element={<Ledger />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/rhythm" element={<Rhythm />} />
            <Route path="/monthly" element={<Monthly />} />
            <Route path="/attribution" element={<Attribution />} />
            <Route path="/policy" element={<Policy />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/tearsheet/:month" element={<Tearsheet />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
