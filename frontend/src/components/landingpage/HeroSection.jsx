import { Link } from 'react-router-dom'

const MOCK_ROWS = [
  { rank: 1, name: "Priya Sharma",   score: 88, bar: '88%', barColor: '#3b82f6', badge: 'Strong Fit',  bc: 'g' },
  { rank: 2, name: "James O'Brien",  score: 74, bar: '74%', barColor: '#60a5fa', badge: 'Strong Fit',  bc: 'g' },
  { rank: 3, name: "Ananya Gupta",   score: 51, bar: '51%', barColor: '#fbbf24', badge: 'Moderate',    bc: 'a' },
]

export default function HeroSection() {
  return (
    <section className="lp-hero">
      <div className="lp-hero-bg" />
      <div className="lp-hero-grid" />
      <div className="lp-hero-inner">
        <div className="lp-hero-badge">
          <div className="lp-hero-badge-dot" />
          Powered by Groq · Llama 3.3 · Sentence Transformers
        </div>

        <h1 className="lp-hero-h1">
          Screen resumes<br />
          <em>10× faster</em> with AI
        </h1>

        <p className="lp-hero-sub">
          Paste a job description, upload resumes, and get every candidate
          ranked, scored, and explained — in seconds, not hours.
        </p>

        <div className="lp-hero-actions">
          <Link to="/signup" className="lp-hero-cta">
            Start screening free →
          </Link>
          <a href="#how-it-works" className="lp-hero-ghost">
            See how it works
          </a>
        </div>

        {/* Mock results card */}
        <div className="lp-hero-card">
          <div className="lp-hero-card-bar">
            <div className="lp-dot lp-dot-r" />
            <div className="lp-dot lp-dot-y" />
            <div className="lp-dot lp-dot-g" />
          </div>
          <div className="lp-hero-card-body">
            <div className="lp-mock-row header">
              <span>#</span>
              <span>Candidate</span>
              <span>Score</span>
              <span>Match</span>
              <span>Result</span>
            </div>
            {MOCK_ROWS.map((r) => (
              <div key={r.rank} className="lp-mock-row row">
                <div className={`lp-rank-pill lp-rank-${r.rank}`}>{r.rank}</div>
                <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13 }}>{r.name}</span>
                <div className="lp-mock-bar-wrap">
                  <div className="lp-mock-bar" style={{ width: r.bar, background: r.barColor }} />
                </div>
                <span style={{ color: 'rgba(255,255,255,0.55)', fontSize: 12, fontFamily: 'var(--mono)' }}>
                  {r.score}
                </span>
                <span className={`lp-mock-badge ${r.bc}`}>{r.badge}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}