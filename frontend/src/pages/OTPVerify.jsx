import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import api, { getErrorMessage } from '../api/axios'

const OTP_LENGTH = 6

export default function OTPVerify() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const email     = location.state?.email || ''

  const [digits,   setDigits]  = useState(Array(OTP_LENGTH).fill(''))
  const [error,    setError]   = useState('')
  const [success,  setSuccess] = useState('')
  const [loading,  setLoading] = useState(false)
  const [resending,setResend]  = useState(false)
  const [countdown,setCountdown] = useState(0)

  const inputRefs = useRef([])

  // Redirect if no email in state
  useEffect(() => {
    if (!email) navigate('/signup')
  }, [email, navigate])

  // Countdown timer for resend
  useEffect(() => {
    if (countdown <= 0) return
    const t = setInterval(() => setCountdown((c) => c - 1), 1000)
    return () => clearInterval(t)
  }, [countdown])

  const otp = digits.join('')

  // ── Digit input handlers ───────────────────────────────────────

  const handleDigitChange = (idx, value) => {
    const digit = value.replace(/\D/g, '').slice(-1)
    const next  = [...digits]
    next[idx]   = digit
    setDigits(next)
    setError('')
    if (digit && idx < OTP_LENGTH - 1) {
      inputRefs.current[idx + 1]?.focus()
    }
    // Auto-submit when all filled
    if (digit && idx === OTP_LENGTH - 1 && next.every(Boolean)) {
      submitOtp(next.join(''))
    }
  }

  const handleKeyDown = (idx, e) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputRefs.current[idx - 1]?.focus()
    }
    if (e.key === 'ArrowLeft' && idx > 0)  inputRefs.current[idx - 1]?.focus()
    if (e.key === 'ArrowRight' && idx < OTP_LENGTH - 1) inputRefs.current[idx + 1]?.focus()
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH)
    if (!pasted) return
    const next = [...digits]
    for (let i = 0; i < pasted.length; i++) next[i] = pasted[i]
    setDigits(next)
    const focusIdx = Math.min(pasted.length, OTP_LENGTH - 1)
    inputRefs.current[focusIdx]?.focus()
    if (pasted.length === OTP_LENGTH) submitOtp(pasted)
  }

  // ── Submit ─────────────────────────────────────────────────────

  const submitOtp = async (code) => {
    if (code.length !== OTP_LENGTH) return
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/verify-otp', { email, otp: code })
      setSuccess('Email verified! Redirecting to login…')
      setTimeout(() => navigate('/login', { state: { verified: true } }), 1800)
    } catch (err) {
      setError(getErrorMessage(err))
      setDigits(Array(OTP_LENGTH).fill(''))
      inputRefs.current[0]?.focus()
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    submitOtp(otp)
  }

  // ── Resend ─────────────────────────────────────────────────────

  const handleResend = async () => {
    setResend(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('email', email)
      await api.post('/auth/resend-otp', formData)
      setCountdown(60)
      setDigits(Array(OTP_LENGTH).fill(''))
      inputRefs.current[0]?.focus()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setResend(false)
    }
  }

  return (
    <div className="page-center">
      <div className="card auth-card animate-fadeUp" style={{ maxWidth: 460 }}>
        <div className="auth-logo"><span />Resume AI</div>

        <h1 className="auth-title">Check your email</h1>
        <p className="auth-subtitle" style={{ marginBottom: 8 }}>
          We sent a 6-digit verification code to
        </p>
        <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 24, color: 'var(--ink)' }}>
          {email}
        </p>

        {error   && <div className="alert alert-error"   style={{ marginBottom: 16 }}>{error}</div>}
        {success && <div className="alert alert-success" style={{ marginBottom: 16 }}>{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="otp-inputs" onPaste={handlePaste}>
            {digits.map((d, i) => (
              <input
                key={i}
                ref={(el) => (inputRefs.current[i] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                className={`otp-digit ${d ? 'filled' : ''}`}
                value={d}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                autoFocus={i === 0}
                disabled={loading || Boolean(success)}
              />
            ))}
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full btn-lg"
            disabled={otp.length < OTP_LENGTH || loading || Boolean(success)}
          >
            {loading ? <><span className="spinner" />Verifying…</> : 'Verify email'}
          </button>
        </form>

        <div className="auth-divider" style={{ margin: '20px 0' }} />

        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--ink-muted)' }}>
          Didn't receive the code?{' '}
          {countdown > 0 ? (
            <span>Resend in {countdown}s</span>
          ) : (
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleResend}
              disabled={resending}
              style={{ display: 'inline', padding: '2px 6px' }}
            >
              {resending ? 'Sending…' : 'Resend code'}
            </button>
          )}
        </div>

        <div className="auth-footer" style={{ marginTop: 12 }}>
          <Link to="/signup">← Back to sign up</Link>
        </div>
      </div>
    </div>
  )
}
