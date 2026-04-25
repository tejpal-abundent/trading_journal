import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import PlanForm from './components/PlanForm'
import TradeList from './components/TradeList'
import Review from './components/Review'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <h1 className="nav-title">Trading Journal</h1>
          <div className="nav-links">
            <NavLink to="/plan" end>Plan</NavLink>
            <NavLink to="/trades">Trades</NavLink>
            <NavLink to="/review">Review</NavLink>
          </div>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<Navigate to="/plan" replace />} />
            <Route path="/plan" element={<PlanForm />} />
            <Route path="/trades" element={<TradeList />} />
            <Route path="/review" element={<Review />} />
            <Route path="/analytics" element={<Navigate to="/review" replace />} />
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
