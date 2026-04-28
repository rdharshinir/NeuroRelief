import { useEffect, useState } from 'react'
import axios from 'axios'
import { Users, UserPlus, Star, MapPin, CheckCircle, XCircle } from 'lucide-react'

const API = 'http://localhost:8000'

const SKILL_OPTIONS  = ['medical','first_aid','nursing','doctor','driving','logistics','rescue','swimming','climbing','construction','shelter','counseling','psychology','social_work','cooking','food','transport']
const LANG_OPTIONS   = ['english','tamil','hindi','telugu','malayalam','kannada','urdu','sanskrit']

const avatarColors = ['#5DA3A8','#9B8EC4','#8BB07A','#D4A65A','#D98E8E','#6DB8BE','#B07BA8']
const avatarColor  = (name) => avatarColors[(name?.charCodeAt(0) ?? 0) % avatarColors.length]

const TrustBar = ({ score }) => {
  const pct  = Math.round((score ?? 0) * 100)
  const color = pct >= 80 ? 'var(--accent-sage)' : pct >= 60 ? 'var(--accent-teal)' : 'var(--accent-gold)'
  return (
    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
      <div className="progress-bar" style={{ flex:1 }}>
        <div className="progress-fill" style={{ width:`${pct}%`, background:color }} />
      </div>
      <span style={{ fontSize:12, fontWeight:700, color, minWidth:34 }}>{pct}%</span>
    </div>
  )
}

export default function VolunteersPage() {
  const [volunteers, setVolunteers] = useState([])
  const [loading, setLoading]       = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg]               = useState(null)

  const [form, setForm] = useState({
    name:'', email:'', location_lat:'', location_lon:'',
    trust_score:'0.7', is_available: true,
    skills:[], languages:[],
  })

  const load = async () => {
    try { setLoading(true); const r = await axios.get(`${API}/volunteers/`); setVolunteers(r.data) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const toggleMulti = (field, val) =>
    setForm(f => ({
      ...f,
      [field]: f[field].includes(val) ? f[field].filter(x => x !== val) : [...f[field], val]
    }))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.name.trim()) return
    try {
      setSubmitting(true)
      await axios.post(`${API}/volunteers/`, {
        ...form,
        location_lat: parseFloat(form.location_lat) || 13.0827,
        location_lon: parseFloat(form.location_lon) || 80.2707,
        trust_score:  parseFloat(form.trust_score)  || 0.7,
      })
      setMsg({ type:'success', text:`${form.name} registered successfully!` })
      setForm({ name:'', email:'', location_lat:'', location_lon:'', trust_score:'0.7', is_available:true, skills:[], languages:[] })
      await load()
    } catch (err) {
      setMsg({ type:'error', text: err.response?.data?.detail || 'Registration failed.' })
    } finally {
      setSubmitting(false)
      setTimeout(() => setMsg(null), 4000)
    }
  }

  const toggleAvailability = async (id, current) => {
    await axios.patch(`${API}/volunteers/${id}/availability?is_available=${!current}`)
    await load()
  }

  return (
    <>
      <div className="topbar">
        <div>
          <div className="topbar-title"><Users size={16} style={{display:'inline',marginRight:6}}/>Volunteers</div>
          <div className="topbar-meta">Register · manage availability · view trust scores</div>
        </div>
      </div>

      <div className="page-wrapper">
        {/* Register form */}
        <div className="form-card">
          <div className="form-title"><UserPlus size={16} color="var(--accent-green)"/>Register Volunteer</div>
          {msg && <div className={`alert alert-${msg.type}`}>{msg.type==='success'?'✓':'✗'} {msg.text}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input name="name" className="form-input" placeholder="Priya Sharma" required
                  value={form.name} onChange={e => setForm(f=>({...f,name:e.target.value}))}/>
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input name="email" type="email" className="form-input" placeholder="priya@example.com"
                  value={form.email} onChange={e=>setForm(f=>({...f,email:e.target.value}))}/>
              </div>
              <div className="form-group">
                <label className="form-label">Latitude</label>
                <input name="location_lat" type="number" step="any" className="form-input" placeholder="13.0827"
                  value={form.location_lat} onChange={e=>setForm(f=>({...f,location_lat:e.target.value}))}/>
              </div>
              <div className="form-group">
                <label className="form-label">Longitude</label>
                <input name="location_lon" type="number" step="any" className="form-input" placeholder="80.2707"
                  value={form.location_lon} onChange={e=>setForm(f=>({...f,location_lon:e.target.value}))}/>
              </div>
              <div className="form-group">
                <label className="form-label">Trust Score (0–1)</label>
                <input name="trust_score" type="number" step="0.01" min="0" max="1" className="form-input"
                  value={form.trust_score} onChange={e=>setForm(f=>({...f,trust_score:e.target.value}))}/>
              </div>
            </div>

            {/* Skills chips */}
            <div className="form-group" style={{ marginBottom:14 }}>
              <label className="form-label">Skills</label>
              <div style={{ display:'flex', flexWrap:'wrap', gap:6, marginTop:4 }}>
                {SKILL_OPTIONS.map(s => (
                  <button type="button" key={s}
                    onClick={() => toggleMulti('skills', s)}
                    style={{
                      padding:'4px 10px', borderRadius:999, fontSize:12, fontWeight:500, cursor:'pointer',
                      border:'1px solid', transition:'all 0.15s',
                      background: form.skills.includes(s) ? 'rgba(59,130,246,0.2)' : 'transparent',
                      borderColor: form.skills.includes(s) ? 'var(--accent-blue)' : 'var(--border)',
                      color: form.skills.includes(s) ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Language chips */}
            <div className="form-group" style={{ marginBottom:20 }}>
              <label className="form-label">Languages</label>
              <div style={{ display:'flex', flexWrap:'wrap', gap:6, marginTop:4 }}>
                {LANG_OPTIONS.map(l => (
                  <button type="button" key={l}
                    onClick={() => toggleMulti('languages', l)}
                    style={{
                      padding:'4px 10px', borderRadius:999, fontSize:12, fontWeight:500, cursor:'pointer',
                      border:'1px solid', transition:'all 0.15s',
                      background: form.languages.includes(l) ? 'rgba(155,142,196,0.15)' : 'transparent',
                      borderColor: form.languages.includes(l) ? 'var(--accent-purple)' : 'var(--border)',
                      color: form.languages.includes(l) ? 'var(--accent-purple)' : 'var(--text-secondary)',
                    }}>
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <><span className="spinner" style={{width:14,height:14,borderWidth:2}}/> Registering…</> : <><UserPlus size={14}/> Register</>}
            </button>
          </form>
        </div>

        {/* Table */}
        <div className="section-header">
          <div className="section-title"><Users size={16}/> Registered Volunteers <span className="badge">{volunteers.length}</span></div>
          <button className="btn btn-outline" onClick={load}>Refresh</button>
        </div>

        <div className="table-card">
          {loading ? (
            <div className="loading-state"><div className="spinner"/></div>
          ) : volunteers.length === 0 ? (
            <div className="empty-state"><div className="empty-icon">👤</div><div className="empty-text">No volunteers registered yet</div></div>
          ) : (
            <table>
              <thead>
                <tr><th>Volunteer</th><th>Skills</th><th>Languages</th><th>Location</th><th>Trust Score</th><th>Status</th></tr>
              </thead>
              <tbody>
                {volunteers.map(v => {
                  const initials = v.name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()
                  const bg = avatarColor(v.name)
                  return (
                    <tr key={v.id}>
                      <td>
                        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                          <div className="vol-avatar" style={{ width:32, height:32, background:`${bg}33`, color:bg, fontSize:12 }}>
                            {initials}
                          </div>
                          <div>
                            <div style={{ fontWeight:600, fontSize:13 }}>{v.name}</div>
                            <div style={{ fontSize:11, color:'var(--text-muted)' }}>{v.email ?? '—'}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                          {(v.skills??[]).slice(0,3).map(s=>(
                            <span key={s} style={{ fontSize:10, padding:'2px 7px', borderRadius:999, background:'rgba(93,163,168,0.1)', color:'#5DA3A8', fontWeight:600 }}>{s}</span>
                          ))}
                          {(v.skills??[]).length > 3 && <span style={{fontSize:10,color:'var(--text-muted)'}}>+{v.skills.length-3}</span>}
                        </div>
                      </td>
                      <td>
                        <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
                          {(v.languages??[]).map(l=>(
                            <span key={l} style={{ fontSize:10, padding:'2px 7px', borderRadius:999, background:'rgba(155,142,196,0.1)', color:'#9B8EC4', fontWeight:600 }}>{l}</span>
                          ))}
                        </div>
                      </td>
                      <td style={{ fontSize:11, color:'var(--text-secondary)' }}>
                        <MapPin size={10}/> {v.location_lat?.toFixed(3)}, {v.location_lon?.toFixed(3)}
                      </td>
                      <td style={{ minWidth:130 }}>
                        <TrustBar score={v.trust_score} />
                      </td>
                      <td>
                        <button onClick={() => toggleAvailability(v.id, v.is_available)}
                          className="btn btn-outline" style={{ padding:'4px 10px', fontSize:11 }}>
                          {v.is_available
                            ? <><CheckCircle size={11} color="var(--accent-green)"/> Available</>
                            : <><XCircle size={11} color="var(--accent-red)"/> Busy</>}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
