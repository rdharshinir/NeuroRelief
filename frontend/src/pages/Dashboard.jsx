import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity, Users, AlertTriangle, FileText, MapPin, TrendingUp, Zap } from 'lucide-react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const API = 'http://localhost:8000'

// ── Colour helpers ────────────────────────────────────────────
const priorityClass = (score) => {
  if (score >= 4)  return 'critical'
  if (score >= 2.5) return 'high'
  if (score >= 1.5) return 'medium'
  return 'low'
}

// Warm palette colors for the volunteer theme
const THEME = {
  teal: '#5DA3A8', gold: '#D4A65A', sage: '#8BB07A', coral: '#D98E8E',
  purple: '#9B8EC4', cyan: '#6DB8BE',
}

const typeEmoji = { medical:'🏥', food:'🍛', shelter:'🏠', rescue:'🚨', counseling:'💬', transport:'🚌' }

const avatarColors = [
  '#5DA3A8','#9B8EC4','#8BB07A','#D4A65A','#D98E8E','#6DB8BE','#B07BA8'
]
const avatarColor = (name) => avatarColors[name?.charCodeAt(0) % avatarColors.length]

// ── StatCard ─────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color, glow }) {
  return (
    <div className="stat-card" style={{ boxShadow: glow }}>
      <div className="stat-icon" style={{ background: `${color}22` }}>
        <Icon size={22} color={color} />
      </div>
      <div className="stat-info">
        <div className="stat-value" style={{ color }}>{value ?? '—'}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  )
}

// ── VolunteerBadge ────────────────────────────────────────────
function VolBadge({ vol }) {
  const initials = vol.volunteer_name?.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase()
  const bg = avatarColor(vol.volunteer_name)
  return (
    <div className="vol-badge">
      <div className="vol-avatar" style={{ background: `${bg}33`, color: bg }}>{initials}</div>
      <span className="vol-name">{vol.volunteer_name}</span>
      <span className="vol-score">{(vol.total * 100).toFixed(0)}%</span>
    </div>
  )
}

// ── SignalCard ────────────────────────────────────────────────
function SignalCard({ sig }) {
  const cls   = priorityClass(sig.priority_score)
  const emoji = typeEmoji[sig.issue_type] ?? '📍'
  const typeKey = sig.issue_type?.toLowerCase()

  return (
    <div className={`signal-card priority-${cls}`}>
      <div className="signal-top">
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          <span className={`signal-type-badge ${typeKey || 'default'}`}>
            {emoji} {sig.issue_type}
          </span>
          <div className="signal-meta">
            <span><MapPin size={11}/> {sig.center_lat?.toFixed(4)}, {sig.center_lon?.toFixed(4)}</span>
            <span><FileText size={11}/> {sig.report_count} report{sig.report_count !== 1 ? 's' : ''}</span>
            <span className={`status-pill ${sig.status}`}>{sig.status}</span>
          </div>
        </div>

        <div className="signal-scores">
          <div className="score-item">
            <div className="score-value" style={{ color: cls === 'critical' ? 'var(--accent-coral)' : cls === 'high' ? 'var(--accent-gold)' : 'var(--accent-teal)' }}>
              {sig.priority_score?.toFixed(2)}
            </div>
            <div className="score-label">Priority</div>
          </div>
          <div className="score-item">
            <div className="score-value" style={{ color:'var(--text-secondary)' }}>
              {sig.urgency_score?.toFixed(2)}
            </div>
            <div className="score-label">Urgency</div>
          </div>
        </div>
      </div>

      {/* Priority bar */}
      <div className="progress-bar" style={{ marginBottom: sig.top_volunteers?.length ? 12 : 0 }}>
        <div className="progress-fill" style={{
          width: `${Math.min(sig.priority_score / 6 * 100, 100)}%`,
          background: cls === 'critical' ? 'var(--accent-coral)'
                    : cls === 'high'     ? 'var(--accent-gold)'
                    : cls === 'medium'   ? 'var(--accent-teal)'
                    : 'var(--accent-sage)',
        }} />
      </div>

      {/* Volunteer matches */}
      {sig.top_volunteers?.length > 0 && (
        <div className="volunteer-matches">
          <div className="matches-label">Top Volunteer Matches</div>
          <div className="matches-row">
            {sig.top_volunteers.map((v, i) => <VolBadge key={i} vol={v} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Fix Leaflet container size ────────────────────────────────
function MapResizer() {
  const map = useMap()
  useEffect(() => {
    // Staggered invalidateSize calls to handle layout paint timing
    const timers = [100, 300, 600, 1200].map(ms =>
      setTimeout(() => map.invalidateSize(), ms)
    )

    // ResizeObserver for dynamic container changes
    const container = map.getContainer()?.parentElement
    let resizeObserver
    if (container && window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => map.invalidateSize())
      resizeObserver.observe(container)
    }

    const handleResize = () => map.invalidateSize()
    window.addEventListener('resize', handleResize)

    return () => {
      timers.forEach(t => clearTimeout(t))
      window.removeEventListener('resize', handleResize)
      resizeObserver?.disconnect()
    }
  }, [map])
  return null
}

// ── Map View ───────────────────────────────────────────
function MapView({ signals }) {
  const center = [13.06, 80.24] // Chennai approx

  return (
    <div className="map-container-wrapper">
      <MapContainer center={center} zoom={12} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <MapResizer />
        {/* Dark map theme from CartoDB Dark Matter */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />
        {signals.map((s) => {
          const colors = { medical:'#FF6B6B', food:'#FFD93D', shelter:'#6BCBCF', rescue:'#C59BFF', counseling:'#95E07A', transport:'#6DB8BE' }
          const color = colors[s.issue_type] ?? '#8A9A8A'
          
          const icon = L.divIcon({
            className: 'custom-marker-icon',
            html: `<div style="
              background: ${color};
              width: 16px; height: 16px;
              border-radius: 50%;
              box-shadow: 0 0 12px ${color}, 0 0 24px ${color}55;
              border: 2px solid rgba(255,255,255,0.85);
            "></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
          })

          return (
            <Marker key={s.id} position={[s.center_lat, s.center_lon]} icon={icon}>
              <Popup>
                <div className="dark-map-popup">
                  <strong>{s.issue_type}</strong>
                  <span>Priority: {s.priority_score?.toFixed(2)}</span>
                  <span>Reports: {s.report_count}</span>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}

// ── Dashboard Page ────────────────────────────────────────────
export default function Dashboard() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  const load = async () => {
    try {
      setLoading(true)
      const res = await axios.get(`${API}/dashboard/`)
      setData(res.data)
      setError(null)
    } catch (e) {
      setError('Cannot reach API – make sure the backend is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])

  return (
    <>
      {/* Top bar */}
      <div className="topbar">
        <div>
          <div className="topbar-title">🧠 Command Dashboard</div>
          <div className="topbar-meta">Auto-refreshes every 30 s</div>
        </div>
        <button className="btn btn-primary" onClick={load}>
          <Activity size={14}/> Refresh
        </button>
      </div>

      <div className="page-wrapper">
        {/* Error */}
        {error && <div className="alert alert-error">⚠️ {error}</div>}

        {/* Stats */}
        <div className="stats-grid">
          <StatCard icon={AlertTriangle} label="Open Signals"      value={data?.total_open_signals}   color="var(--accent-coral)"  glow="var(--shadow-glow-red)" />
          <StatCard icon={Users}         label="Volunteers"         value={data?.total_volunteers}      color="var(--accent-sage)"   glow="var(--shadow-glow-green)" />
          <StatCard icon={FileText}      label="Reports Today"     value={data?.total_reports_today}   color="var(--accent-teal)"   glow="var(--shadow-glow-blue)" />
          <StatCard icon={TrendingUp}    label="Top Priority"      value={data?.top_signals?.[0]?.priority_score?.toFixed(2) ?? '—'} color="var(--accent-gold)" />
        </div>

        {/* Map */}
        <div className="section-header">
          <div className="section-title"><MapPin size={16}/> Signal Map</div>
        </div>
        <div style={{ marginBottom: 24 }}>
          <MapView signals={data?.top_signals ?? []} />
        </div>

        {/* Signals list */}
        <div className="section-header">
          <div className="section-title">
            <Zap size={16}/> Priority Signals
            <span className="badge">{data?.top_signals?.length ?? 0}</span>
          </div>
        </div>

        {loading && !data ? (
          <div className="loading-state"><div className="spinner"/><span>Loading signals…</span></div>
        ) : data?.top_signals?.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">📭</div><div className="empty-text">No active signals. Submit a report to get started.</div></div>
        ) : (
          <div className="signals-list">
            {data?.top_signals?.map(sig => <SignalCard key={sig.id} sig={sig} />)}
          </div>
        )}
      </div>
    </>
  )
}
