import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import ErrorBoundary  from './components/ErrorBoundary'
import LandingPage    from './pages/Landingpage'
import Login          from './pages/Login'
import Signup         from './pages/Signup'
import OTPVerify      from './pages/OTPVerify'
import Projects       from './pages/Projects'
import ProjectDetail  from './pages/ProjectDetail'

/** Redirect logged-in users away from auth pages */
function GuestRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/projects" replace /> : children
}

/** Redirect unauthenticated users to login */
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public landing page */}
            <Route path="/"           element={<LandingPage />} />

            {/* Auth flow: signup → verify-otp → login → projects */}
            <Route path="/signup"     element={<GuestRoute><Signup /></GuestRoute>} />
            <Route path="/verify-otp" element={<OTPVerify />} />
            <Route path="/login"      element={<GuestRoute><Login /></GuestRoute>} />

            {/* Protected app pages */}
            <Route path="/projects"            element={<ProtectedRoute><Projects /></ProtectedRoute>} />
            <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}