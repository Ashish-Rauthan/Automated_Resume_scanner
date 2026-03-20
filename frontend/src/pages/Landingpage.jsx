import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

/* ── Intersection Observer hook for scroll reveals ── */
function useReveal(threshold = 0.15) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect() } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return [ref, visible]
}

function RevealBlock({ children, delay = 0, className = '' }) {
  const [ref, visible] = useReveal()
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(32px)',
        transition: `opacity 650ms ${delay}ms cubic-bezier(0.22,1,0.36,1), transform 650ms ${delay}ms cubic-bezier(0.22,1,0.36,1)`,
      }}
    >
      {children}
    </div>
  )
}

/* ── Animated counter ── */
function Counter({ target, suffix = '' }) {
  const [count, setCount] = useState(0)
  const [ref, visible] = useReveal(0.3)
  useEffect(() => {
    if (!visible) return
    let start = 0
    const step = target / 60
    const timer = setInterval(() => {
      start += step
      if (start >= target) { setCount(target); clearInterval(timer) }
      else setCount(Math.floor(start))
    }, 16)
    return () => clearInterval(timer)
  }, [visible, target])
  return <span ref={ref}>{count}{suffix}</span>
}

const FEATURES = [
  {
    icon: '⚡',
    title: 'Instant AI Analysis',
    desc: 'Upload any resume — PDF or DOCX — and get a full skill extraction and scoring report in under 30 seconds using Groq\'s blazing-fast LLM inference.',
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
    desc: 'Download a polished, Excel-ready CSV with every candidate\'s scores, matched skills, and gaps — ready to share with your hiring manager instantly.',
  },
]

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
    desc: 'Each resume is parsed by Groq\'s Llama 3 model, scored against your JD using skill match + semantic similarity, and ranked from best fit to least.',
    visual: '🤖',
  },
  {
    num: '04',
    title: 'Hire With Confidence',
    desc: 'Review the ranked table, click any candidate for a detailed skill breakdown, and download the full report as a CSV to share with your team.',
    visual: '✅',
  },
]

const STATS = [
  { value: 20, suffix: '+', label: 'Resumes per session' },
  { value: 30, suffix: 's', label: 'Average screening time' },
  { value: 95, suffix: '%', label: 'Skill detection accuracy' },
  { value: 3, suffix: 'x', label: 'Faster than manual review' },
]

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
          --ink:       #0e0e0f;
          --ink-m:     #6b6b78;
          --ink-f:     #a8a8b3;
          --surface:   #fafaf8;
          --surf2:     #f2f2ef;
          --border:    #e0e0da;

          --dark:      #0b0f1a;
          --dark2:     #111827;
          --dark3:     #1e293b;
          --dark-b:    rgba(255,255,255,0.08);

          --accent:    #1a56db;
          --accent2:   #3b82f6;
          --gold:      #f59e0b;

          --serif:     'DM Serif Display', Georgia, serif;
          --sans:      'DM Sans', system-ui, sans-serif;
          --mono:      'DM Mono', monospace;

          --r:         12px;
          --rl:        20px;
        }

        html { scroll-behavior: smooth; }

        body {
          font-family: var(--sans);
          background: var(--surface);
          color: var(--ink);
          -webkit-font-smoothing: antialiased;
          overflow-x: hidden;
        }

        a { text-decoration: none; color: inherit; }
        button { font-family: var(--sans); cursor: pointer; border: none; }
        img { max-width: 100%; display: block; }

        /* ══════════════════════════════════════
           NAV
        ══════════════════════════════════════ */
        .lp-nav {
          position: fixed;
          top: 0; left: 0; right: 0;
          z-index: 200;
          padding: 0 40px;
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          transition: background 300ms ease, box-shadow 300ms ease, backdrop-filter 300ms ease;
        }
        .lp-nav.scrolled {
          background: rgba(11,15,26,0.88);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          box-shadow: 0 1px 0 rgba(255,255,255,0.06);
        }
        .lp-nav-logo {
          display: flex;
          align-items: center;
          gap: 9px;
          font-family: var(--serif);
          font-size: 19px;
          color: #fff;
        }
        .lp-nav-logo-dot {
          width: 28px; height: 28px;
          background: #fff;
          border-radius: 8px;
        }
        .lp-nav-links {
          display: flex;
          align-items: center;
          gap: 32px;
          list-style: none;
        }
        @media (max-width: 768px) { .lp-nav-links { display: none; } }
        .lp-nav-links a {
          font-size: 14px;
          color: rgba(255,255,255,0.72);
          transition: color 150ms ease;
        }
        .lp-nav-links a:hover { color: #fff; }
        .lp-nav-cta {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .lp-btn-ghost {
          font-size: 14px;
          font-weight: 500;
          color: rgba(255,255,255,0.8);
          background: none;
          padding: 8px 16px;
          border-radius: var(--r);
          transition: color 150ms ease, background 150ms ease;
        }
        .lp-btn-ghost:hover { color: #fff; background: rgba(255,255,255,0.08); }

        .lp-btn-primary {
          font-size: 14px;
          font-weight: 500;
          color: var(--dark);
          background: #fff;
          padding: 8px 20px;
          border-radius: var(--r);
          transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
        }
        .lp-btn-primary:hover {
          background: #f0f0ee;
          transform: translateY(-1px);
          box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }
        .lp-btn-primary:active { transform: translateY(0); }

        /* ══════════════════════════════════════
           HERO
        ══════════════════════════════════════ */
        .lp-hero {
          min-height: 100vh;
          background: var(--dark);
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
          padding: 120px 40px 80px;
        }

        /* Background mesh */
        .lp-hero-bg {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 70% 60% at 20% 40%, rgba(26,86,219,0.18) 0%, transparent 70%),
            radial-gradient(ellipse 50% 50% at 80% 20%, rgba(59,130,246,0.12) 0%, transparent 60%),
            radial-gradient(ellipse 40% 40% at 60% 80%, rgba(245,158,11,0.07) 0%, transparent 60%);
          pointer-events: none;
        }

        /* Subtle grid overlay */
        .lp-hero-grid {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
          background-size: 60px 60px;
          pointer-events: none;
        }

        .lp-hero-inner {
          position: relative;
          z-index: 2;
          max-width: 900px;
          width: 100%;
          text-align: center;
        }

        .lp-hero-badge {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          background: rgba(26,86,219,0.15);
          border: 1px solid rgba(26,86,219,0.35);
          color: #93c5fd;
          font-size: 12.5px;
          font-weight: 500;
          padding: 6px 14px;
          border-radius: 100px;
          margin-bottom: 28px;
          letter-spacing: 0.03em;
          animation: fadeDown 600ms 100ms both;
        }
        .lp-hero-badge-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: #3b82f6;
          animation: pulse 2s ease infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }

        .lp-hero-h1 {
          font-family: var(--serif);
          font-size: clamp(42px, 7vw, 80px);
          font-weight: 400;
          color: #fff;
          line-height: 1.1;
          margin-bottom: 24px;
          letter-spacing: -0.01em;
          animation: fadeDown 600ms 200ms both;
        }
        .lp-hero-h1 em {
          font-style: italic;
          color: #93c5fd;
        }

        .lp-hero-sub {
          font-size: clamp(15px, 2vw, 18px);
          color: rgba(255,255,255,0.58);
          line-height: 1.7;
          max-width: 560px;
          margin: 0 auto 40px;
          animation: fadeDown 600ms 300ms both;
        }

        .lp-hero-actions {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 14px;
          flex-wrap: wrap;
          animation: fadeDown 600ms 400ms both;
        }

        .lp-hero-cta {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: #fff;
          color: var(--dark);
          font-size: 15px;
          font-weight: 600;
          padding: 13px 28px;
          border-radius: var(--r);
          transition: transform 160ms ease, box-shadow 160ms ease;
        }
        .lp-hero-cta:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 32px rgba(0,0,0,0.35);
        }
        .lp-hero-cta:active { transform: translateY(0); }

        .lp-hero-ghost {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(255,255,255,0.07);
          color: rgba(255,255,255,0.85);
          font-size: 15px;
          font-weight: 500;
          padding: 13px 28px;
          border-radius: var(--r);
          border: 1px solid rgba(255,255,255,0.12);
          transition: background 160ms ease, border-color 160ms ease;
        }
        .lp-hero-ghost:hover {
          background: rgba(255,255,255,0.12);
          border-color: rgba(255,255,255,0.22);
        }

        @keyframes fadeDown {
          from { opacity:0; transform: translateY(-16px); }
          to   { opacity:1; transform: translateY(0); }
        }

        /* Hero mockup card */
        .lp-hero-card {
          margin: 60px auto 0;
          max-width: 720px;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.09);
          border-radius: 18px;
          overflow: hidden;
          box-shadow: 0 40px 80px rgba(0,0,0,0.5);
          animation: fadeDown 700ms 550ms both;
        }
        .lp-hero-card-bar {
          height: 40px;
          background: rgba(255,255,255,0.04);
          border-bottom: 1px solid rgba(255,255,255,0.07);
          display: flex;
          align-items: center;
          padding: 0 16px;
          gap: 8px;
        }
        .lp-dot { width:10px;height:10px;border-radius:50%; }
        .lp-dot-r { background:#ff5f57; }
        .lp-dot-y { background:#ffbd2e; }
        .lp-dot-g { background:#28ca40; }

        .lp-hero-card-body { padding: 24px; }
        .lp-mock-row {
          display: grid;
          grid-template-columns: 28px 1fr 120px 80px 100px;
          gap: 12px;
          align-items: center;
          padding: 10px 12px;
          border-radius: 8px;
          margin-bottom: 8px;
          font-size: 13px;
        }
        .lp-mock-row.header {
          color: rgba(255,255,255,0.35);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.07em;
          text-transform: uppercase;
        }
        .lp-mock-row.row {
          background: rgba(255,255,255,0.04);
          color: rgba(255,255,255,0.8);
          border: 1px solid rgba(255,255,255,0.06);
        }
        .lp-rank-pill {
          width: 22px; height: 22px;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 11px; font-weight: 600;
        }
        .lp-rank-1 { background:#fff; color:var(--dark); }
        .lp-rank-2 { background:rgba(255,255,255,0.12); color:rgba(255,255,255,0.7); }
        .lp-rank-3 { background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.5); }

        .lp-mock-bar-wrap {
          height: 5px;
          background: rgba(255,255,255,0.1);
          border-radius: 3px;
          overflow: hidden;
        }
        .lp-mock-bar { height: 100%; border-radius: 3px; }

        .lp-mock-badge {
          font-size: 11px; font-weight: 500;
          padding: 3px 8px;
          border-radius: 100px;
          white-space: nowrap;
        }
        .lp-mock-badge.g { background: rgba(13,125,77,0.25); color:#4ade80; }
        .lp-mock-badge.a { background: rgba(146,83,10,0.25); color:#fbbf24; }
        .lp-mock-badge.r { background: rgba(185,28,28,0.2);  color:#f87171; }

        /* ══════════════════════════════════════
           STATS STRIP
        ══════════════════════════════════════ */
        .lp-stats {
          background: var(--dark2);
          border-top: 1px solid rgba(255,255,255,0.06);
          border-bottom: 1px solid rgba(255,255,255,0.06);
          padding: 48px 40px;
        }
        .lp-stats-inner {
          max-width: 900px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1px;
        }
        @media(max-width:640px){ .lp-stats-inner { grid-template-columns: repeat(2,1fr); } }
        .lp-stat-item {
          padding: 8px 24px;
          border-right: 1px solid rgba(255,255,255,0.07);
          text-align: center;
        }
        .lp-stat-item:last-child { border-right: none; }
        .lp-stat-val {
          font-family: var(--serif);
          font-size: 44px;
          color: #fff;
          line-height: 1;
          margin-bottom: 6px;
        }
        .lp-stat-label {
          font-size: 13px;
          color: rgba(255,255,255,0.45);
        }

        /* ══════════════════════════════════════
           SECTION COMMON
        ══════════════════════════════════════ */
        .lp-section {
          padding: 100px 40px;
        }
        .lp-section-inner {
          max-width: 1100px;
          margin: 0 auto;
        }

        .lp-section-eyebrow {
          font-size: 12px;
          font-weight: 600;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: var(--accent2);
          margin-bottom: 12px;
        }

        .lp-section-h2 {
          font-family: var(--serif);
          font-size: clamp(32px, 4.5vw, 52px);
          font-weight: 400;
          line-height: 1.15;
          color: var(--ink);
          margin-bottom: 16px;
        }
        .lp-section-h2.light { color: #fff; }

        .lp-section-desc {
          font-size: 16px;
          color: var(--ink-m);
          line-height: 1.75;
          max-width: 540px;
        }
        .lp-section-desc.light { color: rgba(255,255,255,0.5); }

        /* ══════════════════════════════════════
           FEATURES
        ══════════════════════════════════════ */
        .lp-features-grid {
          margin-top: 60px;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        @media(max-width:900px){ .lp-features-grid { grid-template-columns: repeat(2,1fr); } }
        @media(max-width:560px){ .lp-features-grid { grid-template-columns: 1fr; } }

        .lp-feature-card {
          background: #fff;
          border: 1px solid var(--border);
          border-radius: var(--rl);
          padding: 28px;
          transition: border-color 200ms ease, box-shadow 200ms ease, transform 200ms ease;
        }
        .lp-feature-card:hover {
          border-color: #c7d8f8;
          box-shadow: 0 8px 32px rgba(26,86,219,0.08);
          transform: translateY(-3px);
        }
        .lp-feature-icon {
          font-size: 28px;
          margin-bottom: 16px;
          display: inline-block;
        }
        .lp-feature-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--ink);
          margin-bottom: 8px;
        }
        .lp-feature-desc {
          font-size: 14px;
          color: var(--ink-m);
          line-height: 1.7;
        }

        /* ══════════════════════════════════════
           HOW IT WORKS
        ══════════════════════════════════════ */
        .lp-how {
          background: var(--dark);
        }
        .lp-steps {
          margin-top: 64px;
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 0;
          position: relative;
        }
        @media(max-width:900px) { .lp-steps { grid-template-columns: repeat(2,1fr); gap: 32px; } }
        @media(max-width:520px) { .lp-steps { grid-template-columns: 1fr; } }

        /* connector line */
        .lp-steps::before {
          content: '';
          position: absolute;
          top: 28px;
          left: 10%;
          right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12) 20%, rgba(255,255,255,0.12) 80%, transparent);
          pointer-events: none;
        }
        @media(max-width:900px) { .lp-steps::before { display: none; } }

        .lp-step {
          padding: 0 20px;
          text-align: center;
          position: relative;
        }

        .lp-step-num-wrap {
          width: 56px; height: 56px;
          margin: 0 auto 20px;
          position: relative;
          z-index: 2;
        }
        .lp-step-num-bg {
          width: 56px; height: 56px;
          border-radius: 50%;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.12);
          display: flex; align-items: center; justify-content: center;
          font-size: 20px;
          transition: background 200ms ease, border-color 200ms ease;
        }
        .lp-step:hover .lp-step-num-bg {
          background: rgba(26,86,219,0.2);
          border-color: rgba(59,130,246,0.4);
        }

        .lp-step-label {
          font-family: var(--mono);
          font-size: 11px;
          color: rgba(255,255,255,0.25);
          letter-spacing: 0.1em;
          margin-bottom: 10px;
        }
        .lp-step-title {
          font-family: var(--serif);
          font-size: 18px;
          color: #fff;
          margin-bottom: 10px;
          line-height: 1.3;
        }
        .lp-step-desc {
          font-size: 13.5px;
          color: rgba(255,255,255,0.42);
          line-height: 1.7;
        }

        /* ══════════════════════════════════════
           WHAT WE PROVIDE (light section)
        ══════════════════════════════════════ */
        .lp-provide-grid {
          margin-top: 60px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 48px;
          align-items: center;
        }
        @media(max-width:768px) { .lp-provide-grid { grid-template-columns: 1fr; } }

        .lp-provide-list { display: flex; flex-direction: column; gap: 24px; }

        .lp-provide-item {
          display: flex;
          gap: 16px;
          padding: 20px 22px;
          background: var(--surf2);
          border-radius: var(--r);
          border: 1px solid var(--border);
          transition: border-color 180ms, box-shadow 180ms, transform 180ms;
        }
        .lp-provide-item:hover {
          border-color: #c7d8f8;
          box-shadow: 0 4px 20px rgba(26,86,219,0.07);
          transform: translateX(4px);
        }
        .lp-provide-icon {
          font-size: 22px;
          flex-shrink: 0;
          margin-top: 2px;
        }
        .lp-provide-item-title {
          font-size: 15px;
          font-weight: 600;
          color: var(--ink);
          margin-bottom: 4px;
        }
        .lp-provide-item-desc {
          font-size: 13.5px;
          color: var(--ink-m);
          line-height: 1.65;
        }

        .lp-provide-visual {
          background: var(--dark);
          border-radius: var(--rl);
          overflow: hidden;
          border: 1px solid rgba(255,255,255,0.07);
          box-shadow: 0 24px 60px rgba(0,0,0,0.2);
        }
        .lp-pv-header {
          padding: 16px 20px;
          border-bottom: 1px solid rgba(255,255,255,0.07);
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: rgba(255,255,255,0.5);
          font-family: var(--mono);
        }
        .lp-pv-body { padding: 20px; display: flex; flex-direction: column; gap: 12px; }

        .lp-skill-row {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
        }
        .lp-skill-name {
          color: rgba(255,255,255,0.7);
          min-width: 100px;
          font-family: var(--mono);
          font-size: 12px;
        }
        .lp-skill-track {
          flex: 1;
          height: 6px;
          background: rgba(255,255,255,0.08);
          border-radius: 3px;
          overflow: hidden;
        }
        .lp-skill-fill {
          height: 100%;
          border-radius: 3px;
          background: linear-gradient(90deg, #1a56db, #3b82f6);
        }
        .lp-skill-pct {
          color: rgba(255,255,255,0.4);
          font-size: 12px;
          min-width: 34px;
          text-align: right;
        }

        /* ══════════════════════════════════════
           TESTIMONIAL / TRUST
        ══════════════════════════════════════ */
        .lp-trust {
          background: var(--surf2);
          border-top: 1px solid var(--border);
          border-bottom: 1px solid var(--border);
          padding: 64px 40px;
          text-align: center;
        }
        .lp-trust-label {
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-f);
          margin-bottom: 32px;
        }
        .lp-trust-pills {
          display: flex;
          align-items: center;
          justify-content: center;
          flex-wrap: wrap;
          gap: 12px;
        }
        .lp-trust-pill {
          background: #fff;
          border: 1px solid var(--border);
          border-radius: 100px;
          padding: 9px 20px;
          font-size: 13.5px;
          font-weight: 500;
          color: var(--ink-m);
          display: flex;
          align-items: center;
          gap: 8px;
        }

        /* ══════════════════════════════════════
           CTA
        ══════════════════════════════════════ */
        .lp-cta {
          background: var(--dark);
          padding: 120px 40px;
          text-align: center;
          position: relative;
          overflow: hidden;
        }
        .lp-cta-bg {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 60% 70% at 50% 100%, rgba(26,86,219,0.22) 0%, transparent 70%);
          pointer-events: none;
        }
        .lp-cta-inner { position: relative; z-index: 2; max-width: 640px; margin: 0 auto; }
        .lp-cta-h2 {
          font-family: var(--serif);
          font-size: clamp(34px, 5vw, 58px);
          color: #fff;
          font-weight: 400;
          line-height: 1.15;
          margin-bottom: 18px;
        }
        .lp-cta-h2 em { font-style: italic; color: #93c5fd; }
        .lp-cta-sub {
          font-size: 16px;
          color: rgba(255,255,255,0.48);
          margin-bottom: 40px;
          line-height: 1.7;
        }
        .lp-cta-btn {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          background: #fff;
          color: var(--dark);
          font-size: 15px;
          font-weight: 600;
          padding: 15px 36px;
          border-radius: var(--r);
          transition: transform 160ms ease, box-shadow 160ms ease;
        }
        .lp-cta-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 40px rgba(0,0,0,0.4);
        }

        /* ══════════════════════════════════════
           FOOTER
        ══════════════════════════════════════ */
        .lp-footer {
          background: #080c14;
          padding: 40px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 16px;
          border-top: 1px solid rgba(255,255,255,0.05);
        }
        .lp-footer-logo {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: var(--serif);
          font-size: 16px;
          color: rgba(255,255,255,0.6);
        }
        .lp-footer-logo-dot {
          width: 20px; height: 20px;
          background: rgba(255,255,255,0.3);
          border-radius: 5px;
        }
        .lp-footer-copy {
          font-size: 13px;
          color: rgba(255,255,255,0.25);
        }
        .lp-footer-links {
          display: flex;
          gap: 20px;
        }
        .lp-footer-links a {
          font-size: 13px;
          color: rgba(255,255,255,0.35);
          transition: color 140ms ease;
        }
        .lp-footer-links a:hover { color: rgba(255,255,255,0.7); }

        /* ══════════════════════════════════════
           MOBILE MENU
        ══════════════════════════════════════ */
        .lp-hamburger {
          display: none;
          background: none;
          border: none;
          color: #fff;
          font-size: 22px;
          padding: 4px 8px;
          cursor: pointer;
        }
        @media(max-width:768px){ .lp-hamburger { display: block; } }

        .lp-mobile-menu {
          position: fixed;
          top: 64px; left: 0; right: 0;
          background: rgba(11,15,26,0.97);
          backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(255,255,255,0.08);
          z-index: 199;
          padding: 20px 24px 28px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          animation: slideDown 250ms ease both;
        }
        @keyframes slideDown {
          from { opacity:0; transform:translateY(-12px); }
          to   { opacity:1; transform:translateY(0); }
        }
        .lp-mobile-menu a {
          font-size: 15px;
          color: rgba(255,255,255,0.7);
          padding: 8px 0;
          border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .lp-mobile-menu a:last-child { border-bottom: none; }
      `}</style>

      {/* ── Nav ── */}
      <nav className={`lp-nav${scrolled ? ' scrolled' : ''}`}>
        <div className="lp-nav-logo">
          <div className="lp-nav-logo-dot" />
          Resume AI
        </div>

        <ul className="lp-nav-links">
          <li><a href="#features">Features</a></li>
          <li><a href="#how-it-works">How it works</a></li>
          <li><a href="#what-we-provide">What we provide</a></li>
        </ul>

        <div className="lp-nav-cta">
          <Link to="/login" className="lp-btn-ghost">Sign in</Link>
          <Link to="/signup" className="lp-btn-primary">Get started free</Link>
          <button className="lp-hamburger" onClick={() => setMenuOpen(v => !v)} aria-label="Menu">
            {menuOpen ? '✕' : '☰'}
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="lp-mobile-menu" onClick={() => setMenuOpen(false)}>
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          <a href="#what-we-provide">What we provide</a>
          <Link to="/login">Sign in</Link>
          <Link to="/signup">Get started free →</Link>
        </div>
      )}

      {/* ── Hero ── */}
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
              {[
                { rank:1, name:'Priya Sharma', score:88, bar:'88%', bar_c:'#3b82f6', badge:'Strong Fit', bc:'g' },
                { rank:2, name:'James O\'Brien', score:74, bar:'74%', bar_c:'#60a5fa', badge:'Strong Fit', bc:'g' },
                { rank:3, name:'Ananya Gupta', score:51, bar:'51%', bar_c:'#fbbf24', badge:'Moderate', bc:'a' },
              ].map((r) => (
                <div key={r.rank} className="lp-mock-row row">
                  <div className={`lp-rank-pill lp-rank-${r.rank}`}>{r.rank}</div>
                  <span style={{color:'rgba(255,255,255,0.8)',fontSize:13}}>{r.name}</span>
                  <div className="lp-mock-bar-wrap">
                    <div className="lp-mock-bar" style={{width:r.bar,background:r.bar_c}} />
                  </div>
                  <span style={{color:'rgba(255,255,255,0.55)',fontSize:12,fontFamily:'var(--mono)'}}>{r.score}</span>
                  <span className={`lp-mock-badge ${r.bc}`}>{r.badge}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <div className="lp-stats">
        <div className="lp-stats-inner">
          {STATS.map((s, i) => (
            <div key={i} className="lp-stat-item">
              <div className="lp-stat-val">
                <Counter target={s.value} suffix={s.suffix} />
              </div>
              <div className="lp-stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
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

      {/* ── Trust pills ── */}
      <div className="lp-trust">
        <div className="lp-trust-label">Works with any job type or industry</div>
        <div className="lp-trust-pills">
          {['🧑‍💻 Software Engineering','📊 Data Science','🎨 Design','💼 Product Management','📈 Marketing','🏥 Healthcare','⚖️ Legal','🏗️ Engineering'].map(p => (
            <div key={p} className="lp-trust-pill">{p}</div>
          ))}
        </div>
      </div>

      {/* ── How it works ── */}
      <section className="lp-section lp-how" id="how-it-works">
        <div className="lp-section-inner">
          <RevealBlock>
            <div className="lp-section-eyebrow" style={{color:'#93c5fd'}}>How it works</div>
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

      {/* ── What we provide ── */}
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
                {[
                  { icon:'🏆', title:'Overall Score (0–100)', desc:'A single weighted score combining skill match, semantic similarity, and real-world project experience — calibrated to mirror how a senior recruiter thinks.' },
                  { icon:'✅', title:'Matched Skills Breakdown', desc:'Every JD skill we found in the resume is listed explicitly. Hover a candidate row to see exactly what ticked — no black box.' },
                  { icon:'🚫', title:'Skill Gap Analysis', desc:'Every required skill that\'s missing from a resume is flagged clearly, so you know what to ask in the interview before you book it.' },
                  { icon:'📝', title:'Strong / Moderate / Not a Fit Label', desc:'A plain-English hiring recommendation is generated for each candidate based on configurable score thresholds — no jargon.' },
                ].map((item, i) => (
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
                  {[
                    { skill:'Python',      pct:98 },
                    { skill:'FastAPI',     pct:95 },
                    { skill:'PostgreSQL',  pct:88 },
                    { skill:'Docker',      pct:82 },
                    { skill:'AWS',         pct:76 },
                    { skill:'Kubernetes',  pct:60 },
                    { skill:'Redis',       pct:45 },
                    { skill:'Kafka',       pct:12 },
                  ].map(({ skill, pct }) => (
                    <div key={skill} className="lp-skill-row">
                      <div className="lp-skill-name">{skill}</div>
                      <div className="lp-skill-track">
                        <div className="lp-skill-fill" style={{width:`${pct}%`, opacity: pct < 30 ? 0.35 : 1, background: pct < 30 ? 'linear-gradient(90deg,#b91c1c,#ef4444)' : undefined}} />
                      </div>
                      <div className="lp-skill-pct">{pct}%</div>
                    </div>
                  ))}
                  <div style={{marginTop:16,padding:'12px 14px',background:'rgba(13,125,77,0.12)',border:'1px solid rgba(74,222,128,0.2)',borderRadius:10,color:'#4ade80',fontSize:13}}>
                    ✓ &nbsp;<strong>Strong Fit</strong> — 88.4 / 100 &nbsp;·&nbsp; 6/8 skills matched
                  </div>
                </div>
              </div>
            </RevealBlock>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
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

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-logo">
          <div className="lp-footer-logo-dot" />
          Resume AI
        </div>
        <div className="lp-footer-copy">© {new Date().getFullYear()} Resume AI. All rights reserved.</div>
        <div className="lp-footer-links">
          <Link to="/login">Sign in</Link>
          <Link to="/signup">Sign up</Link>
        </div>
      </footer>
    </>
  )
}