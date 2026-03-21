import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="lp-footer">
      <div className="lp-footer-logo">
        <div className="lp-footer-logo-dot" />
        Resume AI
      </div>
      <div className="lp-footer-copy">
        © {new Date().getFullYear()} Resume AI. All rights reserved.
      </div>
      <div className="lp-footer-links">
        <Link to="/login">Sign in</Link>
        <Link to="/signup">Sign up</Link>
      </div>
    </footer>
  )
}