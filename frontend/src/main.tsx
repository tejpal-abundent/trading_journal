import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import TradeChecklist from './components/TradeChecklist'
import TradeList from './components/TradeList'
import Analytics from './components/Analytics'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <h1 className="nav-title">Trading Journal</h1>
          <div className="nav-links">
            <NavLink to="/" end>New Trade</NavLink>
            <NavLink to="/trades">Trades</NavLink>
            <NavLink to="/analytics">Analytics</NavLink>
          </div>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<TradeChecklist />} />
            <Route path="/trades" element={<TradeList />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
