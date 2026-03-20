/**
 * components/ErrorBoundary.jsx
 * Catches unhandled React render errors — prevents white screen of death.
 * Must be a class component (React requirement for componentDidCatch).
 */

import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('React ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', padding: 24, background: 'var(--surface)',
      }}>
        <div style={{ maxWidth: 480, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>⚠</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 24,
            fontWeight: 400, marginBottom: 10,
          }}>
            Something went wrong
          </h2>
          <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 24 }}>
            An unexpected error occurred. Please refresh the page.
            If this keeps happening, contact support.
          </p>
          {this.state.error && (
            <pre style={{
              background: 'var(--surface-2)', padding: 16,
              borderRadius: 'var(--radius)', fontSize: 12,
              textAlign: 'left', overflow: 'auto',
              color: 'var(--red)', marginBottom: 24,
              fontFamily: 'var(--font-mono)',
            }}>
              {this.state.error.message}
            </pre>
          )}
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      </div>
    )
  }
}