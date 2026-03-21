import { useState } from 'react'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const verified = location.state?.verified

  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)
  const [apiErr, setApiErr] = useState('')
  const [errors, setErrors] = useState({})

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    setErrors((prev) => ({ ...prev, [name]: '' }))
    setApiErr('')
  }

  const validate = () => {
    const e = {}
    if (!formData.email) e.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(formData.email)) e.email = 'Enter a valid email'
    if (!formData.password) e.password = 'Password is required'
    else if (formData.password.length < 8) e.password = 'Min 8 characters'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setApiErr('')
    const fieldErrors = validate()
    if (Object.keys(fieldErrors).length) {
      setErrors(fieldErrors)
      return
    }
    setLoading(true)
    const result = await login(formData.email, formData.password)
    setLoading(false)
    if (result.success) {
      navigate('/projects')
    } else {
      setApiErr(result.error)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

        .login-shell {
          min-height: 100vh;
          background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e293b 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          font-family: 'DM Sans', system-ui, sans-serif;
        }

        .login-card {
          display: flex;
          width: 100%;
          max-width: 980px;
          min-height: 580px;
          background: #fff;
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 32px 80px rgba(0,0,0,0.35), 0 8px 24px rgba(0,0,0,0.2);
          animation: cardReveal 500ms cubic-bezier(0.22,1,0.36,1) both;
        }

        @keyframes cardReveal {
          from { opacity: 0; transform: translateY(28px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* ── Right panel: Image ── */
        .login-left {
          flex: 1.1;
          position: relative;
          overflow: hidden;
          display: none;
          order: 2;
        }
        @media (min-width: 768px) { .login-left { display: block; } }

        .login-left-img {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .login-left-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            180deg,
            rgba(15,23,42,0.12) 0%,
            rgba(15,23,42,0.6) 100%
          );
        }

        .login-left-badge {
          position: absolute;
          bottom: 28px;
          left: 28px;
          right: 28px;
          z-index: 10;
          background: rgba(255,255,255,0.11);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 14px;
          padding: 16px 20px;
          color: #fff;
        }
        .login-left-badge-title {
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 17px;
          margin-bottom: 4px;
          line-height: 1.3;
        }
        .login-left-badge-sub {
          font-size: 12px;
          opacity: 0.72;
          line-height: 1.5;
        }

        /* ── Left panel: Form ── */
        .login-right {
          flex: 1;
          order: 1;
          padding: 48px 40px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          overflow-y: auto;
        }
        @media (max-width: 767px) {
          .login-right { padding: 36px 24px; }
        }

        .login-logo {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 18px;
          color: #0e0e0f;
          margin-bottom: 32px;
        }
        .login-logo-dot {
          width: 26px;
          height: 26px;
          background: #0e0e0f;
          border-radius: 7px;
        }

        .login-heading {
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 28px;
          font-weight: 400;
          color: #0e0e0f;
          margin-bottom: 5px;
          line-height: 1.2;
        }
        .login-subheading {
          font-size: 13.5px;
          color: #6b6b78;
          margin-bottom: 30px;
        }

        /* ── Success banner ── */
        .lo-alert-success {
          background: #e8f5ee;
          border: 1px solid #6ee7b7;
          color: #0d7d4d;
          border-radius: 10px;
          padding: 11px 14px;
          font-size: 13.5px;
          margin-bottom: 20px;
          line-height: 1.5;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        /* ── Error banner ── */
        .lo-alert-error {
          background: #fef2f2;
          border: 1px solid #fca5a5;
          color: #b91c1c;
          border-radius: 10px;
          padding: 11px 14px;
          font-size: 13.5px;
          margin-bottom: 20px;
          line-height: 1.5;
        }

        /* ── Form ── */
        .login-form { display: flex; flex-direction: column; gap: 18px; }

        .lo-field { display: flex; flex-direction: column; gap: 5px; }

        .lo-label {
          font-size: 12.5px;
          font-weight: 500;
          color: #6b6b78;
          letter-spacing: 0.025em;
        }

        .lo-input-wrap { position: relative; }

        .lo-input {
          width: 100%;
          padding: 10px 14px;
          border: 1.5px solid #e0e0da;
          border-radius: 10px;
          font-size: 14.5px;
          font-family: 'DM Sans', system-ui, sans-serif;
          color: #0e0e0f;
          background: #fff;
          outline: none;
          transition: border-color 160ms ease, box-shadow 160ms ease;
          -webkit-appearance: none;
        }
        .lo-input:focus {
          border-color: #1a56db;
          box-shadow: 0 0 0 3px rgba(26,86,219,0.1);
        }
        .lo-input.has-error { border-color: #b91c1c; }
        .lo-input.has-error:focus { box-shadow: 0 0 0 3px rgba(185,28,28,0.1); }
        .lo-input::placeholder { color: #a8a8b3; }
        .lo-input.with-icon { padding-right: 42px; }

        .lo-eye-btn {
          position: absolute;
          right: 10px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          padding: 4px;
          color: #a8a8b3;
          cursor: pointer;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 140ms ease, background 140ms ease;
        }
        .lo-eye-btn:hover { color: #6b6b78; background: #f2f2ef; }

        .lo-field-error {
          font-size: 12px;
          color: #b91c1c;
          margin-top: 1px;
        }

        /* ── Remember me + forgot row ── */
        .lo-meta-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .lo-remember {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }
        .lo-checkbox {
          width: 15px;
          height: 15px;
          accent-color: #1a56db;
          cursor: pointer;
          flex-shrink: 0;
        }
        .lo-remember-label {
          font-size: 13px;
          color: #6b6b78;
          cursor: pointer;
          user-select: none;
        }

        .lo-forgot {
          font-size: 13px;
          font-weight: 500;
          color: #1a56db;
          text-decoration: none;
          white-space: nowrap;
          transition: opacity 140ms ease;
        }
        .lo-forgot:hover { opacity: 0.75; text-decoration: underline; }

        /* ── Submit ── */
        .lo-submit {
          width: 100%;
          padding: 11px 20px;
          background: #0e0e0f;
          color: #fff;
          border: none;
          border-radius: 10px;
          font-size: 14.5px;
          font-weight: 500;
          font-family: 'DM Sans', system-ui, sans-serif;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          transition: background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
          margin-top: 2px;
        }
        .lo-submit:hover:not(:disabled) {
          background: #1a1a1f;
          transform: translateY(-1px);
          box-shadow: 0 6px 18px rgba(0,0,0,0.18);
        }
        .lo-submit:active:not(:disabled) { transform: translateY(0); }
        .lo-submit:disabled { opacity: 0.55; cursor: not-allowed; }

        .lo-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 700ms linear infinite;
          flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Divider ── */
        .lo-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          color: #d0d0c8;
          font-size: 12px;
          margin: 2px 0;
        }
        .lo-divider::before,
        .lo-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: #e8e8e3;
        }

        /* ── Footer ── */
        .lo-footer {
          margin-top: 20px;
          text-align: center;
          font-size: 13px;
          color: #6b6b78;
        }
        .lo-footer a {
          color: #1a56db;
          font-weight: 500;
          text-decoration: none;
        }
        .lo-footer a:hover { text-decoration: underline; }

        /* ── Stagger animations ── */
        .s1 { animation: fadeSlide 380ms 50ms both; }
        .s2 { animation: fadeSlide 380ms 100ms both; }
        .s3 { animation: fadeSlide 380ms 150ms both; }
        .s4 { animation: fadeSlide 380ms 190ms both; }
        .s5 { animation: fadeSlide 380ms 230ms both; }
        .s6 { animation: fadeSlide 380ms 270ms both; }
        .s7 { animation: fadeSlide 380ms 300ms both; }

        @keyframes fadeSlide {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div className="login-shell">
        <div className="login-card">

          {/* ── Left Panel: Image ── */}
          <div className="login-left">
            <img
              src="https://images.unsplash.com/photo-1714715350295-5f00e902f0d7?ixlib=rb-4.1.0&auto=format&fit=crop&q=80&w=1200"
              alt="Abstract background"
              className="login-left-img"
            />
            <div className="login-left-overlay" />
            <div className="login-left-badge">
              <div className="login-left-badge-title">
                AI-Powered Resume Screening
              </div>
              <div className="login-left-badge-sub">
                Rank candidates instantly with LLM-powered analysis.
                No spreadsheets needed.
              </div>
            </div>
          </div>

          {/* ── Right Panel: Form ── */}
          <div className="login-right">

            <div className="login-logo s1">
              <div className="login-logo-dot" />
              Resume AI
            </div>

            <h1 className="login-heading s2">Welcome back</h1>
            <p className="login-subheading s3">
              Sign in by entering the information below
            </p>

            {verified && (
              <div className="lo-alert-success s3">
                ✓ Email verified successfully. You can now sign in.
              </div>
            )}

            {apiErr && (
              <div className="lo-alert-error s3">{apiErr}</div>
            )}

            <form className="login-form" onSubmit={handleSubmit}>

              {/* Email */}
              <div className="lo-field s3">
                <label className="lo-label" htmlFor="email">Email Address</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className={`lo-input${errors.email ? ' has-error' : ''}`}
                  placeholder="email@example.com"
                  value={formData.email}
                  onChange={handleInputChange}
                  autoComplete="email"
                  autoFocus
                />
                {errors.email && <span className="lo-field-error">{errors.email}</span>}
              </div>

              {/* Password */}
              <div className="lo-field s4">
                <label className="lo-label" htmlFor="password">Password</label>
                <div className="lo-input-wrap">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    className={`lo-input with-icon${errors.password ? ' has-error' : ''}`}
                    placeholder="••••••••••••"
                    value={formData.password}
                    onChange={handleInputChange}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="lo-eye-btn"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && <span className="lo-field-error">{errors.password}</span>}
              </div>

              {/* Remember me + Forgot */}
              <div className="lo-meta-row s5">
                <label className="lo-remember">
                  <input
                    type="checkbox"
                    className="lo-checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span className="lo-remember-label">Remember me</span>
                </label>
                <a href="#" className="lo-forgot">Forgotten Password?</a>
              </div>

              {/* Submit */}
              <button
                type="submit"
                className="lo-submit s6"
                disabled={loading}
              >
                {loading ? (
                  <><span className="lo-spinner" /> Signing in…</>
                ) : (
                  'Continue'
                )}
              </button>
            </form>

            <div className="lo-footer s7">
              Don't have an account?{' '}
              <Link to="/signup">Create one here</Link>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}