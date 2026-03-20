import React, { useState } from 'react'

function ScoreBar({ score }) {
  const color = score >= 70 ? '#0d7d4d' : score >= 45 ? '#92530a' : '#b91c1c'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
      <div className="score-bar-track" style={{ flex: 1 }}>
        <div
          className="score-bar-fill"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span style={{ fontSize: 13, fontWeight: 500, color, minWidth: 36 }}>
        {score.toFixed(1)}
      </span>
    </div>
  )
}

function RecommendationBadge({ rec }) {
  const cls =
    rec === 'Strong Fit'   ? 'badge badge-green' :
    rec === 'Moderate Fit' ? 'badge badge-amber' :
                             'badge badge-red'
  return <span className={cls}>{rec}</span>
}

function TagList({ items, variant }) {
  if (!items?.length) return <span style={{ color: 'var(--ink-faint)', fontSize: 12 }}>None</span>
  return (
    <div className="tag-list">
      {items.map((item) => (
        <span key={item} className={`tag ${variant === 'green' ? 'tag-green' : 'tag-red'}`}>
          {item}
        </span>
      ))}
    </div>
  )
}

function CandidateDetail({ result }) {
  return (
    <div className="detail-panel">
      <div className="detail-header">
        <span style={{ fontSize: 13, fontWeight: 500 }}>Detailed breakdown</span>
        <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--ink-muted)' }}>
          <span>Skill match: <strong>{result.skill_match_score?.toFixed(1)}%</strong></span>
          <span>Semantic: <strong>{result.semantic_score?.toFixed(1)}%</strong></span>
        </div>
      </div>
      <div className="detail-body">
        <div className="detail-section">
          <h4>Matched skills</h4>
          <TagList items={result.strengths} variant="green" />
        </div>
        <div className="detail-section">
          <h4>Missing skills</h4>
          <TagList items={result.gaps} variant="red" />
        </div>
      </div>
    </div>
  )
}

export default function ResultsTable({ results }) {
  const [expanded, setExpanded] = useState(null)

  if (!results?.length) return null

  const toggle = (filename) =>
    setExpanded((prev) => (prev === filename ? null : filename))

  return (
    <div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 40 }}>#</th>
              <th>Candidate</th>
              <th>File</th>
              <th style={{ minWidth: 160 }}>Score</th>
              <th>Recommendation</th>
              <th style={{ width: 60 }}></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => {
              const isOpen = expanded === r.filename
              return (
                <React.Fragment key={r.filename}>
                  <tr
                    style={{ cursor: 'pointer' }}
                    onClick={() => toggle(r.filename)}
                  >
                    <td>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        width: 26, height: 26, borderRadius: '50%',
                        background: r.rank === 1 ? 'var(--ink)' : 'var(--surface-2)',
                        color: r.rank === 1 ? '#fff' : 'var(--ink-muted)',
                        fontSize: 12, fontWeight: 500,
                      }}>
                        {r.rank}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>
                        {r.candidate_name || '—'}
                      </div>
                    </td>
                    <td>
                      <span style={{
                        fontSize: 12, color: 'var(--ink-muted)',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        {r.filename}
                      </span>
                    </td>
                    <td><ScoreBar score={r.score} /></td>
                    <td><RecommendationBadge rec={r.recommendation} /></td>
                    <td>
                      <span style={{
                        fontSize: 18, color: 'var(--ink-faint)',
                        transition: 'transform 200ms',
                        display: 'inline-block',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0)',
                      }}>
                        ▾
                      </span>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr>
                      <td colSpan={6} style={{ padding: '0 16px 16px', background: 'var(--surface)' }}>
                        <CandidateDetail result={r} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
