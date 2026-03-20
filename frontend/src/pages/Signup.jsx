'use client'

import { useState } from 'react'
import { Eye, EyeOff, ArrowLeft } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../api/axios'

export default function SignupPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [apiErr, setApiErr] = useState('')
  const [errors, setErrors] = useState({})

  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirm: '',
    agreeToTerms: false,
  })

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    setErrors((prev) => ({ ...prev, [name]: '' }))
    setApiErr('')
  }

  const validate = () => {
    const e = {}
    if (!formData.firstName.trim()) e.firstName = 'First name is required'
    if (!formData.lastName.trim()) e.lastName = 'Last name is required'
    if (!formData.email) e.email = 'Email is required'
    if (formData.password.length < 8) e.password = 'Min 8 characters'
    if (!/[A-Z]/.test(formData.password)) e.password = 'Must contain an uppercase letter'
    if (!/[0-9]/.test(formData.password)) e.password = 'Must contain a digit'
    if (formData.password !== formData.confirm) e.confirm = 'Passwords do not match'
    if (!formData.agreeToTerms) e.agreeToTerms = 'You must agree to the terms'
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
    try {
      await api.post('/auth/signup', {
        email: formData.email,
        password: formData.password,
      })
      navigate('/verify-otp', { state: { email: formData.email } })
    } catch (err) {
      setApiErr(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

        .signup-shell {
          min-height: 100vh;
          background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e293b 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          font-family: 'DM Sans', system-ui, sans-serif;
        }

        .signup-card {
          display: flex;
          width: 100%;
          max-width: 980px;
          min-height: 640px;
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

        /* ── Left panel ── */
        .signup-left {
          flex: 1.1;
          position: relative;
          overflow: hidden;
          display: none;
        }
        @media (min-width: 768px) { .signup-left { display: block; } }

        .signup-left-img {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .signup-left-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            180deg,
            rgba(15,23,42,0.18) 0%,
            rgba(15,23,42,0.55) 100%
          );
        }

        .signup-left-back {
          position: absolute;
          top: 20px;
          left: 20px;
          z-index: 10;
          width: 38px;
          height: 38px;
          background: rgba(255,255,255,0.15);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(255,255,255,0.25);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: background 160ms ease, transform 160ms ease;
          color: #fff;
        }
        .signup-left-back:hover {
          background: rgba(255,255,255,0.25);
          transform: translateX(-2px);
        }

        .signup-left-badge {
          position: absolute;
          bottom: 28px;
          left: 28px;
          right: 28px;
          z-index: 10;
          background: rgba(255,255,255,0.12);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 14px;
          padding: 16px 20px;
          color: #fff;
        }
        .signup-left-badge-title {
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 17px;
          margin-bottom: 4px;
          line-height: 1.3;
        }
        .signup-left-badge-sub {
          font-size: 12px;
          opacity: 0.75;
          line-height: 1.5;
        }

        /* ── Right panel ── */
        .signup-right {
          flex: 1;
          padding: 40px 36px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          overflow-y: auto;
        }
        @media (max-width: 767px) {
          .signup-right { padding: 32px 24px; }
        }

        .signup-logo {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 18px;
          color: #0e0e0f;
          margin-bottom: 28px;
        }
        .signup-logo-dot {
          width: 26px;
          height: 26px;
          background: #0e0e0f;
          border-radius: 7px;
        }

        .signup-heading {
          font-family: 'DM Serif Display', Georgia, serif;
          font-size: 26px;
          font-weight: 400;
          color: #0e0e0f;
          margin-bottom: 5px;
          line-height: 1.25;
        }
        .signup-subheading {
          font-size: 13.5px;
          color: #6b6b78;
          margin-bottom: 26px;
        }
        .signup-subheading a {
          color: #1a56db;
          font-weight: 500;
          text-decoration: none;
        }
        .signup-subheading a:hover { text-decoration: underline; }

        /* ── Alert ── */
        .su-alert-error {
          background: #fef2f2;
          border: 1px solid #fca5a5;
          color: #b91c1c;
          border-radius: 10px;
          padding: 11px 14px;
          font-size: 13.5px;
          margin-bottom: 18px;
          line-height: 1.5;
        }

        /* ── Form ── */
        .signup-form { display: flex; flex-direction: column; gap: 16px; }

        .su-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        @media (max-width: 480px) { .su-row { grid-template-columns: 1fr; } }

        .su-field { display: flex; flex-direction: column; gap: 5px; }

        .su-label {
          font-size: 12.5px;
          font-weight: 500;
          color: #6b6b78;
          letter-spacing: 0.025em;
        }

        .su-input-wrap { position: relative; }

        .su-input {
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
        .su-input:focus {
          border-color: #1a56db;
          box-shadow: 0 0 0 3px rgba(26,86,219,0.1);
        }
        .su-input.has-error { border-color: #b91c1c; }
        .su-input.has-error:focus { box-shadow: 0 0 0 3px rgba(185,28,28,0.1); }
        .su-input::placeholder { color: #a8a8b3; }
        .su-input.with-icon { padding-right: 42px; }

        .su-eye-btn {
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
        .su-eye-btn:hover { color: #6b6b78; background: #f2f2ef; }

        .su-field-error {
          font-size: 12px;
          color: #b91c1c;
          margin-top: 1px;
        }

        /* ── Checkbox ── */
        .su-checkbox-row {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }
        .su-checkbox {
          width: 16px;
          height: 16px;
          margin-top: 2px;
          accent-color: #1a56db;
          cursor: pointer;
          flex-shrink: 0;
        }
        .su-checkbox-label {
          font-size: 13px;
          color: #6b6b78;
          line-height: 1.5;
          cursor: pointer;
        }
        .su-checkbox-label button {
          background: none;
          border: none;
          padding: 0;
          color: #0e0e0f;
          font-weight: 500;
          font-size: 13px;
          font-family: inherit;
          cursor: pointer;
          text-decoration: underline;
          text-decoration-color: transparent;
          transition: text-decoration-color 140ms ease;
        }
        .su-checkbox-label button:hover { text-decoration-color: currentColor; }

        /* ── Submit button ── */
        .su-submit {
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
        .su-submit:hover:not(:disabled) {
          background: #1a1a1f;
          transform: translateY(-1px);
          box-shadow: 0 6px 18px rgba(0,0,0,0.18);
        }
        .su-submit:active:not(:disabled) { transform: translateY(0); }
        .su-submit:disabled { opacity: 0.55; cursor: not-allowed; }

        .su-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 700ms linear infinite;
          flex-shrink: 0;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Footer ── */
        .su-footer {
          margin-top: 18px;
          text-align: center;
          font-size: 13px;
          color: #6b6b78;
        }
        .su-footer a {
          color: #1a56db;
          font-weight: 500;
          text-decoration: none;
        }
        .su-footer a:hover { text-decoration: underline; }

        /* ── Stagger animation ── */
        .stagger-1 { animation: fadeSlide 380ms 60ms both; }
        .stagger-2 { animation: fadeSlide 380ms 110ms both; }
        .stagger-3 { animation: fadeSlide 380ms 160ms both; }
        .stagger-4 { animation: fadeSlide 380ms 200ms both; }
        .stagger-5 { animation: fadeSlide 380ms 240ms both; }
        .stagger-6 { animation: fadeSlide 380ms 280ms both; }
        .stagger-7 { animation: fadeSlide 380ms 310ms both; }

        @keyframes fadeSlide {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div className="signup-shell">
        <div className="signup-card">

          {/* ── Left Panel ── */}
          <div className="signup-left">
            <img
              src="https://i.ibb.co/dJxBbFks/brandasset.png"
              alt="Brand visual"
              className="signup-left-img"
            />
            <div className="signup-left-overlay" />

            <button
              className="signup-left-back"
              onClick={() => navigate('/')}
              aria-label="Back to home"
            >
              <ArrowLeft size={17} />
            </button>

            <div className="signup-left-badge">
              <div className="signup-left-badge-title">
                AI-Powered Resume Screening
              </div>
              <div className="signup-left-badge-sub">
                Rank candidates instantly with LLM-powered analysis.
                No spreadsheets needed.
              </div>
            </div>
          </div>

          {/* ── Right Panel ── */}
          <div className="signup-right">

            <div className="signup-logo stagger-1">
              <div className="signup-logo-dot" />
              Resume AI
            </div>

            <h1 className="signup-heading stagger-2">Create your account</h1>
            <p className="signup-subheading stagger-3">
              Already have an account?{' '}
              <Link to="/login">Sign in</Link>
            </p>

            {apiErr && (
              <div className="su-alert-error">{apiErr}</div>
            )}

            <form className="signup-form" onSubmit={handleSubmit}>

              {/* Name row */}
              <div className="su-row stagger-3">
                <div className="su-field">
                  <label className="su-label" htmlFor="firstName">First name</label>
                  <input
                    id="firstName"
                    name="firstName"
                    type="text"
                    className={`su-input${errors.firstName ? ' has-error' : ''}`}
                    placeholder="John"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    autoComplete="given-name"
                    autoFocus
                  />
                  {errors.firstName && <span className="su-field-error">{errors.firstName}</span>}
                </div>
                <div className="su-field">
                  <label className="su-label" htmlFor="lastName">Last name</label>
                  <input
                    id="lastName"
                    name="lastName"
                    type="text"
                    className={`su-input${errors.lastName ? ' has-error' : ''}`}
                    placeholder="Doe"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    autoComplete="family-name"
                  />
                  {errors.lastName && <span className="su-field-error">{errors.lastName}</span>}
                </div>
              </div>

              {/* Email */}
              <div className="su-field stagger-4">
                <label className="su-label" htmlFor="email">Work email</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className={`su-input${errors.email ? ' has-error' : ''}`}
                  placeholder="you@company.com"
                  value={formData.email}
                  onChange={handleInputChange}
                  autoComplete="email"
                />
                {errors.email && <span className="su-field-error">{errors.email}</span>}
              </div>

              {/* Password */}
              <div className="su-field stagger-5">
                <label className="su-label" htmlFor="password">Password</label>
                <div className="su-input-wrap">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    className={`su-input with-icon${errors.password ? ' has-error' : ''}`}
                    placeholder="Min 8 chars, 1 uppercase, 1 digit"
                    value={formData.password}
                    onChange={handleInputChange}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="su-eye-btn"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && <span className="su-field-error">{errors.password}</span>}
              </div>

              {/* Confirm password */}
              <div className="su-field stagger-5">
                <label className="su-label" htmlFor="confirm">Confirm password</label>
                <div className="su-input-wrap">
                  <input
                    id="confirm"
                    name="confirm"
                    type={showConfirm ? 'text' : 'password'}
                    className={`su-input with-icon${errors.confirm ? ' has-error' : ''}`}
                    placeholder="Repeat password"
                    value={formData.confirm}
                    onChange={handleInputChange}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="su-eye-btn"
                    onClick={() => setShowConfirm((v) => !v)}
                    aria-label={showConfirm ? 'Hide password' : 'Show password'}
                  >
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.confirm && <span className="su-field-error">{errors.confirm}</span>}
              </div>

              {/* Terms */}
              <div className="stagger-6">
                <label className="su-checkbox-row">
                  <input
                    type="checkbox"
                    name="agreeToTerms"
                    className="su-checkbox"
                    checked={formData.agreeToTerms}
                    onChange={handleInputChange}
                  />
                  <span className="su-checkbox-label">
                    I agree to the{' '}
                    <button type="button">Terms & Conditions</button>
                    {' '}and{' '}
                    <button type="button">Privacy Policy</button>
                  </span>
                </label>
                {errors.agreeToTerms && (
                  <div className="su-field-error" style={{ marginTop: 4 }}>
                    {errors.agreeToTerms}
                  </div>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                className="su-submit stagger-7"
                disabled={loading}
              >
                {loading ? (
                  <><span className="su-spinner" /> Creating account…</>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>

            <div className="su-footer">
              Already have an account?{' '}
              <Link to="/login">Sign in</Link>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}