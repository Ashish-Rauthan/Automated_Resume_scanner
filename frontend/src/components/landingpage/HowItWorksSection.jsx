import RevealBlock from './RevealBlock'

const STEPS = [
  {
    num: '01',
    title: 'Paste Your Job Description',
    desc: 'Drop in the full JD — responsibilities, requirements, nice-to-haves. Our LLM extracts every required skill, experience level, and keyword automatically.',
    visual: '📋',
  },
  {
    num: '02',
    title: 'Upload Candidate Resumes',
    desc: 'Drag and drop up to 20 PDFs or Word documents in one go. We extract text from every page, table, and text box — even from complex formatted resumes.',
    visual: '📂',
  },
  {
    num: '03',
    title: 'AI Scores & Ranks Everyone',
    desc: "Each resume is parsed by Groq's Llama 3 model, scored against your JD using skill match + semantic similarity, and ranked from best fit to least.",
    visual: '🤖',
  },
  {
    num: '04',
    title: 'Hire With Confidence',
    desc: 'Review the ranked table, click any candidate for a detailed skill breakdown, and download the full report as a CSV to share with your team.',
    visual: '✅',
  },
]

export default function HowItWorksSection() {
  return (
    <section className="lp-section lp-how" id="how-it-works">
      <div className="lp-section-inner">
        <RevealBlock>
          <div className="lp-section-eyebrow" style={{ color: '#93c5fd' }}>How it works</div>
          <h2 className="lp-section-h2 light">Four steps from JD to hire</h2>
          <p className="lp-section-desc light">
            No training, no setup, no configuration.
            Just paste, upload, and let AI do the rest.
          </p>
        </RevealBlock>

        <div className="lp-steps">
          {STEPS.map((s, i) => (
            <RevealBlock key={s.num} delay={i * 80}>
              <div className="lp-step">
                <div className="lp-step-num-wrap">
                  <div className="lp-step-num-bg">{s.visual}</div>
                </div>
                <div className="lp-step-label">Step {s.num}</div>
                <div className="lp-step-title">{s.title}</div>
                <div className="lp-step-desc">{s.desc}</div>
              </div>
            </RevealBlock>
          ))}
        </div>
      </div>
    </section>
  )
}