import RevealBlock from './RevealBlock'

const PROVIDE_ITEMS = [
  {
    icon: '🏆',
    title: 'Overall Score (0–100)',
    desc: 'A single weighted score combining skill match, semantic similarity, and real-world project experience — calibrated to mirror how a senior recruiter thinks.',
  },
  {
    icon: '✅',
    title: 'Matched Skills Breakdown',
    desc: "Every JD skill we found in the resume is listed explicitly. Hover a candidate row to see exactly what ticked — no black box.",
  },
  {
    icon: '🚫',
    title: 'Skill Gap Analysis',
    desc: "Every required skill that's missing from a resume is flagged clearly, so you know what to ask in the interview before you book it.",
  },
  {
    icon: '📝',
    title: 'Strong / Moderate / Not a Fit Label',
    desc: 'A plain-English hiring recommendation is generated for each candidate based on configurable score thresholds — no jargon.',
  },
]

const SKILL_BARS = [
  { skill: 'Python',     pct: 98 },
  { skill: 'FastAPI',    pct: 95 },
  { skill: 'PostgreSQL', pct: 88 },
  { skill: 'Docker',     pct: 82 },
  { skill: 'AWS',        pct: 76 },
  { skill: 'Kubernetes', pct: 60 },
  { skill: 'Redis',      pct: 45 },
  { skill: 'Kafka',      pct: 12 },
]

export default function WhatWeProvideSection() {
  return (
    <section className="lp-section" id="what-we-provide">
      <div className="lp-section-inner">
        <RevealBlock>
          <div className="lp-section-eyebrow">What we provide</div>
          <h2 className="lp-section-h2">
            A complete picture<br />of every candidate
          </h2>
          <p className="lp-section-desc">
            We don't just give you a number. We explain exactly why a candidate
            scored the way they did, what they bring, and what's missing.
          </p>
        </RevealBlock>

        <div className="lp-provide-grid">
          <RevealBlock>
            <div className="lp-provide-list">
              {PROVIDE_ITEMS.map((item, i) => (
                <RevealBlock key={item.title} delay={i * 70}>
                  <div className="lp-provide-item">
                    <div className="lp-provide-icon">{item.icon}</div>
                    <div>
                      <div className="lp-provide-item-title">{item.title}</div>
                      <div className="lp-provide-item-desc">{item.desc}</div>
                    </div>
                  </div>
                </RevealBlock>
              ))}
            </div>
          </RevealBlock>

          <RevealBlock delay={100}>
            <div className="lp-provide-visual">
              <div className="lp-pv-header">
                📊 &nbsp;Skill match · Priya Sharma
              </div>
              <div className="lp-pv-body">
                {SKILL_BARS.map(({ skill, pct }) => (
                  <div key={skill} className="lp-skill-row">
                    <div className="lp-skill-name">{skill}</div>
                    <div className="lp-skill-track">
                      <div
                        className="lp-skill-fill"
                        style={{
                          width: `${pct}%`,
                          opacity: pct < 30 ? 0.35 : 1,
                          background: pct < 30
                            ? 'linear-gradient(90deg,#b91c1c,#ef4444)'
                            : undefined,
                        }}
                      />
                    </div>
                    <div className="lp-skill-pct">{pct}%</div>
                  </div>
                ))}
                <div style={{
                  marginTop: 16, padding: '12px 14px',
                  background: 'rgba(13,125,77,0.12)',
                  border: '1px solid rgba(74,222,128,0.2)',
                  borderRadius: 10, color: '#4ade80', fontSize: 13,
                }}>
                  ✓ &nbsp;<strong>Strong Fit</strong> — 88.4 / 100 &nbsp;·&nbsp; 6/8 skills matched
                </div>
              </div>
            </div>
          </RevealBlock>
        </div>
      </div>
    </section>
  )
}