import RevealBlock from './RevealBlock'

const FEATURES = [
  {
    icon: '⚡',
    title: 'Instant AI Analysis',
    desc: "Upload any resume — PDF or DOCX — and get a full skill extraction and scoring report in under 30 seconds using Groq's blazing-fast LLM inference.",
  },
  {
    icon: '🎯',
    title: 'Precision Skill Matching',
    desc: 'Our hybrid engine combines exact keyword matching, fuzzy aliases, and semantic embeddings to catch skills no regex ever could — like "k8s" matching "Kubernetes".',
  },
  {
    icon: '📊',
    title: 'Ranked Leaderboard',
    desc: 'Every screening session produces a ranked candidate table with scores, strength tags, skill gaps, and a Strong / Moderate / Not a Fit recommendation.',
  },
  {
    icon: '🧠',
    title: 'Semantic Understanding',
    desc: 'Using sentence-transformers, we go beyond keywords — understanding that "built microservices at scale" maps to the "distributed systems" requirement in your JD.',
  },
  {
    icon: '📁',
    title: 'Batch Screening',
    desc: 'Screen up to 20 resumes in a single session. No per-resume clicks, no waiting between candidates. Drop the whole folder and let AI rank them all at once.',
  },
  {
    icon: '📤',
    title: 'One-Click CSV Export',
    desc: "Download a polished, Excel-ready CSV with every candidate's scores, matched skills, and gaps — ready to share with your hiring manager instantly.",
  },
]

export default function FeaturesSection() {
  return (
    <section className="lp-section" id="features">
      <div className="lp-section-inner">
        <RevealBlock>
          <div className="lp-section-eyebrow">What we do</div>
          <h2 className="lp-section-h2">
            Everything you need to<br />hire the right person, fast
          </h2>
          <p className="lp-section-desc">
            No more spreadsheets. No more reading every resume line by line.
            Resume AI handles the heavy lifting so you can focus on the conversation.
          </p>
        </RevealBlock>

        <div className="lp-features-grid">
          {FEATURES.map((f, i) => (
            <RevealBlock key={f.title} delay={i * 60}>
              <div className="lp-feature-card">
                <div className="lp-feature-icon">{f.icon}</div>
                <div className="lp-feature-title">{f.title}</div>
                <div className="lp-feature-desc">{f.desc}</div>
              </div>
            </RevealBlock>
          ))}
        </div>
      </div>
    </section>
  )
}