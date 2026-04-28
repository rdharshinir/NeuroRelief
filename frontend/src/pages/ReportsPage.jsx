import { useEffect, useState } from 'react'
import axios from 'axios'
import { FileText, Send, MapPin, Clock, AlertCircle } from 'lucide-react'

const API = 'http://localhost:8000'

const ISSUE_TYPES = ['medical','food','shelter','rescue','counseling','transport','other']
const typeEmoji   = { medical:'🏥', food:'🍛', shelter:'🏠', rescue:'🚨', counseling:'💬', transport:'🚌', other:'📍' }

const severityColor = [,'#8BB07A','#6DB8BE','#5DA3A8','#D4A65A','#D98E8E']
const severityLabel = [,'Low','Moderate','High','Urgent','Critical']

export default function ReportsPage() {
  const [reports, setReports]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg]           = useState(null)

  const [form, setForm] = useState({
    location_lat:  '', location_lon:  '',
    issue_type:    'medical', description: '',
    reporter_name: '',
  })

  const loadReports = async () => {
    try {
      setLoading(true)
      const res = await axios.get(`${API}/reports/?limit=50`)
      setReports(res.data)
    } finally { setLoading(false) }
  }

  useEffect(() => { loadReports() }, [])

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.description.trim()) return
    try {
      setSubmitting(true)
      await axios.post(`${API}/reports/`, {
        ...form,
        location_lat: parseFloat(form.location_lat) || 13.0827,
        location_lon: parseFloat(form.location_lon) || 80.2707,
      })
      setMsg({ type:'success', text:'Report submitted! Signal fusion ran automatically.' })
      setForm({ location_lat:'', location_lon:'', issue_type:'medical', description:'', reporter_name:'' })
      await loadReports()
    } catch (err) {
      setMsg({ type:'error', text: err.response?.data?.detail || 'Failed to submit report.' })
    } finally {
      setSubmitting(false)
      setTimeout(() => setMsg(null), 4000)
    }
  }

  return (
    <>
      <div className="topbar">
        <div>
          <div className="topbar-title"><FileText size={16} style={{display:'inline',marginRight:6}}/>Community Reports</div>
          <div className="topbar-meta">Submit needs · Auto-fused into signals</div>
        </div>
      </div>

      <div className="page-wrapper">
        {/* Submit form */}
        <div className="form-card">
          <div className="form-title"><Send size={16} color="var(--accent-blue)"/>Submit a Report</div>
          {msg && <div className={`alert alert-${msg.type}`}>{msg.type==='success'?'✓':'✗'} {msg.text}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Issue Type</label>
                <select name="issue_type" className="form-select" value={form.issue_type} onChange={handleChange}>
                  {ISSUE_TYPES.map(t => <option key={t} value={t}>{typeEmoji[t]} {t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Reporter Name (optional)</label>
                <input name="reporter_name" className="form-input" placeholder="Your name" value={form.reporter_name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label className="form-label">Latitude</label>
                <input name="location_lat" type="number" step="any" className="form-input" placeholder="13.0827" value={form.location_lat} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label className="form-label">Longitude</label>
                <input name="location_lon" type="number" step="any" className="form-input" placeholder="80.2707" value={form.location_lon} onChange={handleChange} />
              </div>
            </div>
            <div className="form-group" style={{ marginBottom:16 }}>
              <label className="form-label">Description *</label>
              <textarea name="description" className="form-textarea" required
                placeholder="Describe the situation… include severity words like 'urgent', 'critical', 'severe' for higher priority"
                value={form.description} onChange={handleChange} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <><span className="spinner" style={{width:14,height:14,borderWidth:2}}/> Submitting…</> : <><Send size={14}/> Submit Report</>}
            </button>
          </form>
        </div>

        {/* Reports table */}
        <div className="section-header">
          <div className="section-title"><AlertCircle size={16}/> Recent Reports <span className="badge">{reports.length}</span></div>
          <button className="btn btn-outline" onClick={loadReports}><Clock size={13}/> Refresh</button>
        </div>

        <div className="table-card">
          {loading ? (
            <div className="loading-state"><div className="spinner"/></div>
          ) : reports.length === 0 ? (
            <div className="empty-state"><div className="empty-icon">📭</div><div className="empty-text">No reports yet</div></div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Severity</th>
                  <th>Location</th>
                  <th>Reporter</th>
                  <th>Time</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {reports.map(r => (
                  <tr key={r.id}>
                    <td>
                      <span className={`signal-type-badge ${r.issue_type}`} style={{fontSize:11}}>
                        {typeEmoji[r.issue_type]??'📍'} {r.issue_type}
                      </span>
                    </td>
                    <td style={{ maxWidth:260, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', color:'var(--text-secondary)' }}>
                      {r.description}
                    </td>
                    <td>
                      <span style={{ color: severityColor[r.severity], fontWeight:700, fontSize:12 }}>
                        {severityLabel[r.severity] ?? r.severity}
                      </span>
                    </td>
                    <td style={{ fontSize:11, color:'var(--text-secondary)' }}>
                      <MapPin size={10}/> {r.location_lat?.toFixed(3)}, {r.location_lon?.toFixed(3)}
                    </td>
                    <td style={{ fontSize:12 }}>{r.reporter_name ?? '—'}</td>
                    <td style={{ fontSize:11, color:'var(--text-muted)', whiteSpace:'nowrap' }}>
                      {new Date(r.timestamp).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}
                    </td>
                    <td style={{ fontSize:11, color:'var(--accent-cyan)', fontFamily:'monospace' }}>
                      {r.signal_id ? r.signal_id.slice(0,8)+'…' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
