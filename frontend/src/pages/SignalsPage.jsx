import { useEffect, useState } from 'react'
import axios from 'axios'
import { Zap, RefreshCw, UserCheck, MapPin, BarChart2 } from 'lucide-react'

const API = 'http://localhost:8000'

const typeEmoji   = { medical:'🏥', food:'🍛', shelter:'🏠', rescue:'🚨', counseling:'💬', transport:'🚌' }
const priorityClass = s => s>=4?'critical':s>=2.5?'high':s>=1.5?'medium':'low'

const avatarColors = ['#5DA3A8','#9B8EC4','#8BB07A','#D4A65A','#D98E8E','#6DB8BE']
const avatarColor  = n => avatarColors[(n?.charCodeAt(0)??0) % avatarColors.length]

export default function SignalsPage() {
  const [signals,  setSignals]  = useState([])
  const [matches,  setMatches]  = useState({})   // signalId → [volunteers]
  const [loading,  setLoading]  = useState(true)
  const [matching, setMatching] = useState({})   // signalId → bool
  const [assigning, setAssigning] = useState({})
  const [msg, setMsg] = useState(null)

  const load = async () => {
    try { setLoading(true); const r = await axios.get(`${API}/signals/?limit=50`); setSignals(r.data) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const runMatch = async (id) => {
    setMatching(m => ({...m, [id]:true}))
    try {
      const r = await axios.get(`${API}/match/${id}?top_n=3`)
      setMatches(m => ({...m, [id]: r.data}))
    } finally { setMatching(m => ({...m, [id]:false})) }
  }

  const assignTop = async (id) => {
    setAssigning(a => ({...a, [id]:true}))
    try {
      await axios.post(`${API}/match/${id}/assign?top_n=3`)
      setMsg({ type:'success', text:'Top 3 volunteers assigned to signal!' })
      await load()
    } catch (e) {
      setMsg({ type:'error', text: e.response?.data?.detail ?? 'Assignment failed.' })
    } finally {
      setAssigning(a => ({...a, [id]:false}))
      setTimeout(() => setMsg(null), 4000)
    }
  }

  const refreshPriority = async (id) => {
    await axios.post(`${API}/signals/${id}/refresh-priority`)
    await load()
  }

  return (
    <>
      <div className="topbar">
        <div>
          <div className="topbar-title"><Zap size={16} style={{display:'inline',marginRight:6}}/>Fused Signals</div>
          <div className="topbar-meta">Corroboration-weighted need signals · ranked by priority</div>
        </div>
        <button className="btn btn-primary" onClick={load}><RefreshCw size={13}/> Refresh All</button>
      </div>

      <div className="page-wrapper">
        {msg && <div className={`alert alert-${msg.type}`}>{msg.type==='success'?'✓':'✗'} {msg.text}</div>}

        <div className="section-header">
          <div className="section-title">
            <BarChart2 size={16}/> All Signals
            <span className="badge">{signals.length}</span>
          </div>
        </div>

        {loading ? (
          <div className="loading-state"><div className="spinner"/><span>Loading signals…</span></div>
        ) : signals.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⚡</div>
            <div className="empty-text">No signals yet. Submit reports to generate signals.</div>
          </div>
        ) : (
          <div className="signals-list">
            {signals.map(sig => {
              const cls   = priorityClass(sig.priority_score)
              const vols  = matches[sig.id] ?? []
              const busy  = matching[sig.id]
              const abusy = assigning[sig.id]

              return (
                <div key={sig.id} className={`signal-card priority-${cls}`}>
                  {/* Header row */}
                  <div className="signal-top">
                    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                        <span className={`signal-type-badge ${sig.issue_type?.toLowerCase()||'default'}`}>
                          {typeEmoji[sig.issue_type]??'📍'} {sig.issue_type}
                        </span>
                        <span className={`status-pill ${sig.status}`}>{sig.status}</span>
                      </div>
                      <div className="signal-meta">
                        <span><MapPin size={11}/> {sig.center_lat?.toFixed(4)}, {sig.center_lon?.toFixed(4)}</span>
                        <span>📋 {sig.report_count} report{sig.report_count!==1?'s':''}</span>
                        <span style={{fontSize:10,color:'var(--text-muted)',fontFamily:'monospace'}}>
                          ID: {sig.id?.slice(0,8)}…
                        </span>
                      </div>
                    </div>

                    {/* Score block */}
                    <div className="signal-scores">
                      <div className="score-item">
                        <div className="score-value" style={{ color:
                          cls==='critical'?'var(--accent-coral)':cls==='high'?'var(--accent-gold)':'var(--accent-teal)' }}>
                          {sig.priority_score?.toFixed(3)}
                        </div>
                        <div className="score-label">Priority</div>
                      </div>
                      <div className="score-item">
                        <div className="score-value" style={{color:'var(--text-secondary)', fontSize:15}}>
                          {sig.urgency_score?.toFixed(3)}
                        </div>
                        <div className="score-label">Urgency</div>
                      </div>
                      <div className="score-item">
                        <div className="score-value" style={{color:'var(--text-secondary)', fontSize:15}}>
                          {sig.base_severity?.toFixed(1)}
                        </div>
                        <div className="score-label">Base Sev.</div>
                      </div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="progress-bar" style={{marginBottom:12}}>
                    <div className="progress-fill" style={{
                      width:`${Math.min(sig.priority_score/6*100,100)}%`,
                      background:cls==='critical'?'var(--accent-coral)':cls==='high'?'var(--accent-gold)':cls==='medium'?'var(--accent-teal)':'var(--accent-sage)',
                    }}/>
                  </div>

                  {/* Action buttons */}
                  <div style={{ display:'flex', gap:8, flexWrap:'wrap', marginBottom: vols.length ? 14 : 0 }}>
                    <button className="btn btn-outline" style={{fontSize:12,padding:'6px 12px'}}
                      onClick={() => runMatch(sig.id)} disabled={busy}>
                      {busy ? <><span className="spinner" style={{width:12,height:12,borderWidth:2}}/> Matching…</>
                             : <><UserCheck size={13}/> Find Volunteers</>}
                    </button>
                    <button className="btn btn-primary" style={{fontSize:12,padding:'6px 12px'}}
                      onClick={() => assignTop(sig.id)} disabled={abusy || sig.status==='resolved'}>
                      {abusy ? <><span className="spinner" style={{width:12,height:12,borderWidth:2}}/> Assigning…</>
                              : '⚡ Assign Top 3'}
                    </button>
                    <button className="btn btn-outline" style={{fontSize:12,padding:'6px 12px'}}
                      onClick={() => refreshPriority(sig.id)}>
                      <RefreshCw size={12}/> Decay
                    </button>
                  </div>

                  {/* Volunteer matches */}
                  {vols.length > 0 && (
                    <div className="volunteer-matches">
                      <div className="matches-label">Match Results (4-axis engine)</div>
                      <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                        {vols.map((v, i) => {
                          const bg = avatarColor(v.volunteer_name)
                          const initials = v.volunteer_name?.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()
                          return (
                            <div key={i} style={{
                              display:'flex', alignItems:'center', gap:10,
                              background:'rgba(255,255,255,0.03)', borderRadius:8,
                              padding:'10px 12px', border:'1px solid var(--border)',
                            }}>
                              <div className="vol-avatar" style={{width:32,height:32,background:`${bg}33`,color:bg,fontSize:12}}>
                                {initials}
                              </div>
                              <div style={{flex:1}}>
                                <div style={{fontWeight:600,fontSize:13}}>{v.volunteer_name}</div>
                                <div style={{display:'flex',gap:12,marginTop:4,fontSize:11}}>
                                  <span style={{color:'var(--accent-teal)'}}>Skill {(v.skill_score*100).toFixed(0)}%</span>
                                  <span style={{color:'var(--accent-sage)'}}>Dist {(v.distance_score*100).toFixed(0)}%</span>
                                  <span style={{color:'var(--accent-purple)'}}>Lang {(v.language_score*100).toFixed(0)}%</span>
                                  <span style={{color:'var(--accent-gold)'}}>Trust {(v.trust_score*100).toFixed(0)}%</span>
                                </div>
                              </div>
                              <div style={{textAlign:'right'}}>
                                <div style={{fontSize:20,fontWeight:800,color:i===0?'var(--accent-sage)':'var(--text-primary)'}}>
                                  {(v.total*100).toFixed(0)}%
                                </div>
                                <div style={{fontSize:10,color:'var(--text-muted)'}}>match</div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
