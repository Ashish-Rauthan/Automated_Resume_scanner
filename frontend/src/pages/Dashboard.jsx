import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import api, { getErrorMessage } from '../api/axios'
import ResumeUpload from '../components/ResumeUpload'
import ResultsTable from '../components/ResultsTable'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Summary cards ──────────────────────────────────────────────
function SummaryCards({ results }) {
  const total    = results.length
  const strong   = results.filter((r) => r.recommendation === 'Strong Fit').length
  const moderate = results.filter((r) => r.recommendation === 'Moderate Fit').length
  const avg      = total ? (results.reduce((s, r) => s + r.score, 0) / total).toFixed(1) : '—'
  const top      = results[0]

  return (
    <div className="summary-grid">
      {[
        { label: 'Total candidates', value: total,    sub: 'resumes screened' },
        { label: 'Strong fit',       value: strong,   sub: `score ≥ 70` },
        { label: 'Moderate fit',     value: moderate, sub: `score 45–69` },
        { label: 'Average score',    value: avg,      sub: 'out of 100' },
      ].map(({ label, value, sub }) => (
        <div key={label} className="card summary-card">
          <div className="summary-label">{label}</div>
          <div className="summary-value">{value}</div>
          <div className="summary-sub">{sub}</div>
        </div>
      ))}
      {top && (
        <div className="card summary-card" style={{ gridColumn: 'span 2' }}>
          <div className="summary-label">Top candidate</div>
          <div style={{ fontSize: 18, fontWeight: 500, marginTop: 4 }}>
            {top.candidate_name || top.filename}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <span className={`badge ${top.recommendation === 'Strong Fit' ? 'badge-green' : 'badge-amber'}`}>
              {top.recommendation}
            </span>
            <span className="badge badge-blue">Score {top.score}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Loading skeleton ───────────────────────────────────────────
function LoadingSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {[1, 2, 3].map((i) => (
        <div key={i} className="skeleton" style={{ height: 56, animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { user, logout } = useAuth()

  // Form state
  const [jd,      setJd]      = useState('')
  const [files,   setFiles]   = useState([])

  // Results state
  const [results,   setResults]   = useState([])
  const [sessionId, setSessionId] = useState('')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')
  const [hasRun,    setHasRun]    = useState(false)

  // ── Screen handler ───────────────────────────────────────────
  const handleScreen = async (e) => {
    e.preventDefault()
    setError('')

    if (!jd.trim() || jd.trim().length < 50) {
      setError('Job description must be at least 50 characters.')
      return
    }
    if (!files.length) {
      setError('Please upload at least one PDF resume.')
      return
    }

    setLoading(true)
    setResults([])
    setHasRun(false)

    try {
      const formData = new FormData()
      formData.append('job_description', jd)
      files.forEach((f) => formData.append('files', f))

      const { data } = await api.post('/screen', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setResults(data.results || [])
      setSessionId(data.session_id || '')
      setHasRun(true)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  // ── CSV download ─────────────────────────────────────────────
  const handleDownloadCSV = () => {
    if (!sessionId) return
    const token = localStorage.getItem('access_token')
    const url   = `${BASE_URL}/screen/export/${sessionId}`
    // Open in a hidden anchor to trigger download with auth header
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `resume_screening_${sessionId.slice(0, 8)}.csv`
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch(() => setError('CSV download failed. Please try again.'))
  }

  // ── Reset ────────────────────────────────────────────────────
  const handleReset = () => {
    setJd(''); setFiles([]); setResults([])
    setSessionId(''); setHasRun(false); setError('')
  }

  return (
    <div className="app-shell">
      {/* ── Top bar ─────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="topbar-logo-dot" />
          Resume AI
        </div>
        <div className="topbar-right">
          <span className="topbar-email">{user?.email}</span>
          <button className="btn btn-ghost btn-sm" onClick={logout}>Sign out</button>
        </div>
      </header>

      <main className="page-body">
        {/* ── Page header ──────────────────────────────────── */}
        <div className="page-header">
          <h1 className="page-title">Resume Screening</h1>
          <p className="page-desc">
            Paste a job description, upload resumes, and get AI-ranked candidates instantly.
          </p>
        </div>

        {/* ── Error ────────────────────────────────────────── */}
        {error && (
          <div className="alert alert-error animate-fadeIn" style={{ marginBottom: 24 }}>
            {error}
          </div>
        )}

        {/* ── Input form ───────────────────────────────────── */}
        {!hasRun && (
          <form onSubmit={handleScreen} className="animate-fadeUp">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              {/* JD column */}
              <div className="card" style={{ padding: 24 }}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 4 }}>
                    Job Description
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
                    Paste the full JD — skills, requirements, responsibilities
                  </div>
                </div>
                <textarea
                  className="input"
                  style={{ minHeight: 320, resize: 'vertical' }}
                  placeholder="We are looking for a Senior Backend Engineer with 4+ years of Python experience…"
                  value={jd}
                  onChange={(e) => { setJd(e.target.value); setError('') }}
                  required
                />
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-faint)', textAlign: 'right' }}>
                  {jd.length} characters {jd.length < 50 && jd.length > 0 && '(min 50)'}
                </div>
              </div>

              {/* Upload column */}
              <div className="card" style={{ padding: 24 }}>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 4 }}>
                    Candidate Resumes
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
                    Upload one or multiple PDF resumes to screen
                  </div>
                </div>
                <ResumeUpload files={files} onChange={setFiles} />

                {files.length > 0 && (
                  <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--surface-2)', borderRadius: 'var(--radius)', fontSize: 13, color: 'var(--ink-muted)' }}>
                    {files.length} resume{files.length > 1 ? 's' : ''} ready to screen
                  </div>
                )}
              </div>
            </div>

            {/* Submit */}
            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={loading || !jd.trim() || !files.length}
                style={{ minWidth: 200 }}
              >
                {loading ? (
                  <><span className="spinner" />Screening {files.length} resume{files.length > 1 ? 's' : ''}…</>
                ) : (
                  `Screen ${files.length || ''} Resume${files.length !== 1 ? 's' : ''}`
                )}
              </button>
            </div>
          </form>
        )}

        {/* ── Loading state ─────────────────────────────────── */}
        {loading && (
          <div className="animate-fadeIn" style={{ marginTop: 32 }}>
            <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--ink-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="spinner spinner-dark" />
              Extracting text, parsing with AI, and scoring candidates…
            </div>
            <LoadingSkeleton />
          </div>
        )}

        {/* ── Results ──────────────────────────────────────── */}
        {hasRun && results.length > 0 && (
          <div className="animate-fadeUp">
            {/* Results header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 500 }}>
                  {results.length} candidate{results.length > 1 ? 's' : ''} ranked
                </div>
                <div style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 2 }}>
                  Click any row to see skill breakdown · Session {sessionId.slice(0, 8)}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handleDownloadCSV}
                >
                  ↓ Download CSV
                </button>
                <button className="btn btn-ghost btn-sm" onClick={handleReset}>
                  New screening
                </button>
              </div>
            </div>

            <SummaryCards results={results} />
            <ResultsTable results={results} />
          </div>
        )}

        {/* ── Empty results ─────────────────────────────────── */}
        {hasRun && results.length === 0 && !loading && (
          <div className="empty-state animate-fadeIn">
            <div className="empty-icon">🔍</div>
            <div className="empty-title">No results returned</div>
            <div className="empty-desc">The resumes may have been unreadable. Try different PDFs.</div>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={handleReset}>
              Try again
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
