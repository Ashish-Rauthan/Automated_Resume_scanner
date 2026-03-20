import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api, { getErrorMessage } from '../api/axios'

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatScore(s) {
  if (s == null) return '—'
  return s.toFixed(1)
}

function NewProjectModal({ onClose, onCreate }) {
  const [title, setTitle] = useState('')
  const [desc,  setDesc]  = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required.'); return }
    setLoading(true)
    try {
      const { data } = await api.post('/projects', { title: title.trim(), description: desc.trim() })
      onCreate(data)
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
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 400, marginBottom: 6 }}>
          New screening project
        </h2>
        <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginBottom: 24 }}>
          Give this batch of screenings a memorable title — e.g. "Q3 Backend Hiring".
        </p>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="field">
            <label className="label" htmlFor="proj-title">Project title *</label>
            <input
              id="proj-title" className="input" type="text"
              placeholder="e.g. Backend Engineer — July 2025"
              value={title} onChange={(e) => { setTitle(e.target.value); setError('') }}
              required autoFocus maxLength={255}
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="proj-desc">Description (optional)</label>
            <textarea
              id="proj-desc" className="input"
              placeholder="Any notes about this hiring round…"
              value={desc} onChange={(e) => setDesc(e.target.value)}
              style={{ minHeight: 72, resize: 'vertical' }} maxLength={1000}
            />
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <><span className="spinner" />Creating…</> : 'Create project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Projects() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [projects, setProjects] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [showModal, setShowModal] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    api.get('/projects')
      .then(({ data }) => setProjects(data.projects || []))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = (newProject) => {
    setProjects([newProject, ...projects])
    setShowModal(false)
    navigate(`/projects/${newProject.id}`)
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this project and all its screening results?')) return
    setDeletingId(id)
    try {
      await api.delete(`/projects/${id}`)
      setProjects(projects.filter((p) => p.id !== id))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="app-shell">
      {/* Topbar */}
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
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 28 }}>
          <div>
            <h1 className="page-title">My Projects</h1>
            <p className="page-desc">Each project is a named hiring round with its own screening sessions.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + New project
          </button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 24 }}>{error}</div>}

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[1,2,3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 88 }} />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="empty-state" style={{ marginTop: 60 }}>
            <div className="empty-icon">📁</div>
            <div className="empty-title">No projects yet</div>
            <div className="empty-desc">Create your first project to start screening resumes.</div>
            <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={() => setShowModal(true)}>
              Create first project
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {projects.map((p) => (
              <div
                key={p.id}
                className="card"
                style={{ padding: '20px 24px', cursor: 'pointer', transition: 'box-shadow var(--transition)' }}
                onClick={() => navigate(`/projects/${p.id}`)}
                onMouseEnter={(e) => e.currentTarget.style.boxShadow = 'var(--shadow)'}
                onMouseLeave={(e) => e.currentTarget.style.boxShadow = 'var(--shadow-sm)'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  {/* Icon */}
                  <div style={{
                    width: 44, height: 44, borderRadius: 10,
                    background: 'var(--accent-dim)', color: 'var(--accent)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20, flexShrink: 0,
                  }}>
                    📋
                  </div>

                  {/* Main info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: 15, color: 'var(--ink)', marginBottom: 2 }}>
                      {p.title}
                    </div>
                    {p.description && (
                      <div style={{ fontSize: 13, color: 'var(--ink-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.description}
                      </div>
                    )}
                  </div>

                  {/* Stats */}
                  <div style={{ display: 'flex', gap: 24, flexShrink: 0, alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 18, fontWeight: 500, fontFamily: 'var(--font-serif)', color: 'var(--ink)' }}>
                        {p.candidate_count}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
                        candidates
                      </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 18, fontWeight: 500, fontFamily: 'var(--font-serif)', color: 'var(--ink)' }}>
                        {formatScore(p.top_score)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
                        top score
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 12, color: 'var(--ink-muted)' }}>
                        {formatDate(p.last_run || p.updated_at)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-faint)' }}>last run</div>
                    </div>
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ color: 'var(--red)', padding: '6px 10px' }}
                      disabled={deletingId === p.id}
                      onClick={(e) => handleDelete(p.id, e)}
                      title="Delete project"
                    >
                      {deletingId === p.id ? <span className="spinner spinner-dark" style={{ width: 14, height: 14 }} /> : '🗑'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {showModal && <NewProjectModal onClose={() => setShowModal(false)} onCreate={handleCreate} />}
    </div>
  )
}
