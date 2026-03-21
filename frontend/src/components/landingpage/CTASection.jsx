import { Link } from 'react-router-dom'
import RevealBlock from './RevealBlock'

export default function CTASection() {
  return (
    <section className="lp-cta">
      <div className="lp-cta-bg" />
      <div className="lp-cta-inner">
        <RevealBlock>
          <h2 className="lp-cta-h2">
            Ready to hire<br /><em>smarter</em>?
          </h2>
          <p className="lp-cta-sub">
            Create your free account and screen your first batch of resumes
            in under two minutes. No credit card required.
          </p>
          <Link to="/signup" className="lp-cta-btn">
            Get started for free →
          </Link>
        </RevealBlock>
      </div>
    </section>
  )
}