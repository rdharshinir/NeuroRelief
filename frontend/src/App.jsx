import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileText, Users, Zap, Activity } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import ReportsPage from './pages/ReportsPage'
import VolunteersPage from './pages/VolunteersPage'
import SignalsPage from './pages/SignalsPage'

const NAV = [
  { to: '/',          label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/signals',   label: 'Signals',    icon: Zap },
  { to: '/reports',   label: 'Reports',    icon: FileText },
  { to: '/volunteers',label: 'Volunteers', icon: Users },
]

export default function App() {
  return (
    <div className="app-layout">
      {/* ── Sidebar ─────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">
            <div className="logo-icon">🧠</div>
            <div>
              <div className="logo-text">NeuroRelief</div>
              <div className="logo-sub">Bio-Inspired Coordination</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-label">Navigation</div>
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            <span className="status-dot" />
            API Connected
            <br />
            <span style={{ paddingLeft: '14px' }}>localhost:8000</span>
          </div>
        </div>
      </aside>

      {/* ── Main ────────────────────── */}
      <main className="main-content">
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/signals"    element={<SignalsPage />} />
          <Route path="/reports"    element={<ReportsPage />} />
          <Route path="/volunteers" element={<VolunteersPage />} />
        </Routes>
      </main>
    </div>
  )
}
