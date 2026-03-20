import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../api/axios'

export default function Signup() {
  const navigate = useNavigate()
  const [form,    setForm]    = useState({ email: '', password: '', confirm: '' })
  const [errors,  setErrors]  = useState({})
  const [apiErr,  setApiErr]  = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
    setErrors((er) => ({ ...er, [e.target.name]: '' }))
  }

  const validate = () => {
    const e = {}
    if (!form.email) e.email = 'Email is required'
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters'
    if (!/[A-Z]/.test(form.password)) e.password = 'Password must contain an uppercase letter'
    if (!/[0-9]/.test(form.password)) e.password = 'Password must contain a digit'
    if (form.password !== form.confirm) e.confirm = 'Passwords do not match'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setApiErr('')
    const fieldErrors = validate()
    if (Object.keys(fieldErrors).length) { setErrors(fieldErrors); return }

    setLoading(true)
    try {
      await api.post('/auth/signup', { email: form.email, password: form.password })
      navigate('/verify-otp', { state: { email: form.email } })
    } catch (err) {
      setApiErr(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-center">
      <div className="card auth-card animate-fadeUp">
        <div className="auth-logo">
          <span />
          Resume AI
        </div>

        <h1 className="auth-title">Create account</h1>
        <p className="auth-subtitle">Start screening resumes with AI in minutes</p>

        {apiErr && <div className="alert alert-error" style={{ marginBottom: 16 }}>{apiErr}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="field">
            <label className="label" htmlFor="email">Work email</label>
            <input
              id="email" name="email" type="email"
              className={`input ${errors.email ? 'error' : ''}`}
              placeholder="you@company.com"
              value={form.email}
              onChange={handleChange}
              required autoFocus
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>

          <div className="field">
            <label className="label" htmlFor="password">Password</label>
            <input
              id="password" name="password" type="password"
              className={`input ${errors.password ? 'error' : ''}`}
              placeholder="Min 8 chars, 1 uppercase, 1 digit"
              value={form.password}
              onChange={handleChange}
              required
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </div>

          <div className="field">
            <label className="label" htmlFor="confirm">Confirm password</label>
            <input
              id="confirm" name="confirm" type="password"
              className={`input ${errors.confirm ? 'error' : ''}`}
              placeholder="Repeat password"
              value={form.confirm}
              onChange={handleChange}
              required
            />
            {errors.confirm && <span className="field-error">{errors.confirm}</span>}
          </div>

          <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
            {loading ? <><span className="spinner" />Creating account…</> : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}