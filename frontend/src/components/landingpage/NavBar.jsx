import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function NavBar({ scrolled }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <>
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
          <button
            className="lp-hamburger"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Menu"
          >
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
    </>
  )
}