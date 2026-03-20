/**
 * api/axios.js
 * Configured Axios instance with:
 *  - Base URL from env
 *  - JWT token injection on every request
 *  - 401 auto-logout
 *  - Consistent error message extraction
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s — LLM calls can be slow for large batches
})

// ── Request interceptor: attach JWT ───────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: handle 401 ─────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      // Redirect to login only if not already there
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

/**
 * Extract a human-readable error message from an Axios error.
 * Handles FastAPI's { detail: string } and { detail: [{msg}] } formats.
 */
export function getErrorMessage(error) {
  const detail = error?.response?.data?.detail
  if (!detail) return error?.message || 'An unexpected error occurred.'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => e.msg || JSON.stringify(e)).join('. ')
  }
  return JSON.stringify(detail)
}

export default api
