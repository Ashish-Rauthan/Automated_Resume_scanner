import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api, { getErrorMessage } from '../api/axios'
import ResumeUpload from '../components/ResumeUpload'
import ResultsTable from '../components/ResultsTable'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ── Edit project modal ────────────────────────────────────────
function EditModal({ project, onClose, onSave }) {
  const [title, setTitle]   = useState(project.title)
  const [desc,  setDesc]    = useState(project.description || '')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required.'); return }
    setLoading(true)
    try {
      const { data } = await api.patch(`/projects/${project.id}`,
        { title: title.trim(), description: desc.trim() })
      onSave(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 200, padding: 24,
    }}>
      <div className="card" style={{ width: '100%', maxWidth: 440, padding: 32 }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 400, marginBottom: 20 }}>
          Edit project
        </h2>
        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="field">
            <label className="label">Title *</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus required />
          </div>
          <div className="field">
            <label className="label">Description</label>
            <textarea className="input" value={desc} onChange={(e) => setDesc(e.target.value)}
              style={{ minHeight: 72, resize: 'vertical' }} />
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Session card (collapsible) ────────────────────────────────
function SessionCard({ session, projectId }) {
  const [open,    setOpen]    = useState(false)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const navigate = useNavigate()

  const load = async () => {
    if (results !== null) { setOpen((o) => !o); return }
    setLoading(true)
    try {
      const { data } = await api.get(`/screen/export/${session.session_id}`, {
        responseType: 'text',
      })
    } catch {}
    // Fetch actual result objects via re-screening view
    // We'll get them from the session detail approach
    try {
      const { data } = await api.get(`/projects/${projectId}/sessions`)
      // Results come from the project screening endpoint; use local state approach
    } catch {}
    setLoading(false)
    setOpen(true)
  }

  const downloadCSV = async (e) => {
    e.stopPropagation()
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${BASE_URL}/screen/export/${session.session_id}`,
      { headers: { Authorization: `Bearer ${token}` } })
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `session_${session.session_id.slice(0, 8)}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const recStr = session.top_score != null
    ? (session.top_score >= 70 ? 'Strong Fit' : session.top_score >= 45 ? 'Moderate Fit' : 'Not a Fit')
    : null

  const badgeCls = recStr === 'Strong Fit' ? 'badge-green' : recStr === 'Moderate Fit' ? 'badge-amber' : 'badge-red'

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div
        style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
        onClick={() => setOpen((o) => !o)}
      >
        <div style={{
          fontSize: 13, transform: open ? 'rotate(90deg)' : 'rotate(0)',
          transition: 'transform 200ms', color: 'var(--ink-muted)',
        }}>▶</div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>
            {formatDate(session.created_at)}
          </div>
          {session.jd_preview && (
            <div style={{ fontSize: 12, color: 'var(--ink-muted)', marginTop: 2,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {session.jd_preview}{session.jd_preview.length >= 120 ? '…' : ''}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexShrink: 0 }}>
          <span className="badge badge-blue">{session.candidate_count} candidates</span>
          {recStr && <span className={`badge ${badgeCls}`}>Top: {session.top_score?.toFixed(1)}</span>}
          <button
            className="btn btn-secondary btn-sm"
            onClick={downloadCSV}
            title="Download CSV"
          >
            ↓ CSV
          </button>
        </div>
      </div>

      {open && (
        <SessionResults sessionId={session.session_id} />
      )}
    </div>
  )
}

function SessionResults({ sessionId }) {
  const [rows, setRows]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    // Re-fetch from DB via a dedicated endpoint
    api.get(`/session/${sessionId}/results`)
      .then(({ data }) => setRows(data.results || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) return (
    <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
      <div className="skeleton" style={{ height: 40 }} />
    </div>
  )

  if (!rows || rows.length === 0) return (
    <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)',
      fontSize: 13, color: 'var(--ink-muted)' }}>
      No results found for this session.
    </div>
  )

  return (
    <div style={{ borderTop: '1px solid var(--border)', padding: '0 16px 16px' }}>
      <ResultsTable results={rows} />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────
export default function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [project,  setProject]  = useState(null)
  const [sessions, setSessions] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [showEdit, setShowEdit] = useState(false)

  // screening form
  const [jd,       setJd]       = useState('')
  const [files,    setFiles]     = useState([])
  const [screening, setScreening] = useState(false)
  const [screenErr, setScreenErr] = useState('')
  const [latestResults, setLatestResults] = useState(null)
  const [latestSession, setLatestSession] = useState('')

  const loadProject = useCallback(async () => {
    try {
      const { data } = await api.get(`/projects/${projectId}`)
      setProject(data)
      setSessions(data.sessions || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { loadProject() }, [loadProject])

  const handleScreen = async (e) => {
    e.preventDefault()
    setScreenErr('')
    if (!jd.trim() || jd.trim().length < 50) {
      setScreenErr('Job description must be at least 50 characters.'); return
    }
    if (!files.length) {
      setScreenErr('Please upload at least one resume.'); return
    }
    setScreening(true)
    setLatestResults(null)
    try {
      const formData = new FormData()
      formData.append('job_description', jd)
      files.forEach((f) => formData.append('files', f))
      const { data } = await api.post(`/projects/${projectId}/screen`, formData,
        { headers: { 'Content-Type': 'multipart/form-data' } })
      setLatestResults(data.results || [])
      setLatestSession(data.session_id || '')
      // Reload sessions list
      await loadProject()
      setJd('')
      setFiles([])
    } catch (err) {
      setScreenErr(getErrorMessage(err))
    } finally {
      setScreening(false)
    }
  }

  const downloadCSV = () => {
    if (!latestSession) return
    const token = localStorage.getItem('access_token')
    fetch(`${BASE_URL}/screen/export/${latestSession}`,
      { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `screening_${latestSession.slice(0, 8)}.csv`
        a.click()
        URL.revokeObjectURL(a.href)
      })
  }

  if (loading) return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-logo"><div className="topbar-logo-dot" />Resume AI</div>
      </header>
      <main className="page-body">
        {[1,2,3].map((i) => <div key={i} className="skeleton" style={{ height: 60, marginBottom: 12 }} />)}
      </main>
    </div>
  )

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-logo">
          <div className="topbar-logo-dot" />Resume AI
        </div>
        <div className="topbar-right">
          <span className="topbar-email">{user?.email}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/projects')}>
            ← All projects
          </button>
        </div>
      </header>

      <main className="page-body">
        {error && <div className="alert alert-error" style={{ marginBottom: 24 }}>{error}</div>}

        {/* Project header */}
        {project && (
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 32, flexWrap: 'wrap', gap: 12 }}>
            <div>
              <h1 className="page-title">{project.title}</h1>
              {project.description && (
                <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginTop: 4 }}>{project.description}</p>
              )}
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowEdit(true)}>
              ✏ Edit
            </button>
          </div>
        )}

        {/* ── New screening form ─────────────────────────────── */}
        <div className="card" style={{ padding: 24, marginBottom: 32 }}>
          <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 4 }}>Run a new screening</div>
          <div style={{ fontSize: 13, color: 'var(--ink-muted)', marginBottom: 20 }}>
            Paste a JD and upload resumes — results are saved to this project.
          </div>

          {screenErr && <div className="alert alert-error" style={{ marginBottom: 16 }}>{screenErr}</div>}

          <form onSubmit={handleScreen}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
              <div>
                <div className="label" style={{ marginBottom: 6 }}>Job Description</div>
                <textarea
                  className="input"
                  style={{ minHeight: 200, resize: 'vertical' }}
                  placeholder="Paste full job description here (min 50 chars)…"
                  value={jd}
                  onChange={(e) => { setJd(e.target.value); setScreenErr('') }}
                />
                <div style={{ fontSize: 11, color: 'var(--ink-faint)', textAlign: 'right', marginTop: 4 }}>
                  {jd.length} chars
                </div>
              </div>
              <div>
                <div className="label" style={{ marginBottom: 6 }}>Resumes (PDF / DOCX)</div>
                <ResumeUpload files={files} onChange={setFiles} />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={screening || !jd.trim() || !files.length}
                style={{ minWidth: 180 }}
              >
                {screening
                  ? <><span className="spinner" />Screening…</>
                  : `Screen ${files.length || ''} Resume${files.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </form>
        </div>

        {/* ── Latest results ─────────────────────────────────── */}
        {latestResults && latestResults.length > 0 && (
          <div className="animate-fadeUp" style={{ marginBottom: 32 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 500 }}>
                Latest results — {latestResults.length} candidate{latestResults.length > 1 ? 's' : ''}
              </div>
              <button className="btn btn-secondary btn-sm" onClick={downloadCSV}>
                ↓ Download CSV
              </button>
            </div>
            <ResultsTable results={latestResults} />
          </div>
        )}

        {/* ── Past sessions ──────────────────────────────────── */}
        <div>
          <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 14, color: 'var(--ink)' }}>
            Past screening sessions
            <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--ink-muted)', marginLeft: 8 }}>
              ({sessions.length})
            </span>
          </div>

          {sessions.length === 0 ? (
            <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 14 }}>
              No past sessions yet — run your first screening above.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {sessions.map((s) => (
                <SessionCard key={s.session_id} session={s} projectId={projectId} />
              ))}
            </div>
          )}
        </div>
      </main>

      {showEdit && project && (
        <EditModal
          project={project}
          onClose={() => setShowEdit(false)}
          onSave={(updated) => {
            setProject((p) => ({ ...p, ...updated }))
            setShowEdit(false)
          }}
        />
      )}
    </div>
  )
}
