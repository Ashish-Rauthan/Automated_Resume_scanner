import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import ErrorBoundary from './components/ErrorBoundary'
import Login        from './pages/Login'
import Signup       from './pages/Signup'
import OTPVerify    from './pages/OTPVerify'
import Projects     from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function GuestRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/projects" replace /> : children
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"                    element={<Navigate to="/projects" replace />} />
            <Route path="/login"               element={<GuestRoute><Login /></GuestRoute>} />
            <Route path="/signup"              element={<GuestRoute><Signup /></GuestRoute>} />
            <Route path="/verify-otp"          element={<OTPVerify />} />
            <Route path="/projects"            element={<ProtectedRoute><Projects /></ProtectedRoute>} />
            <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
            <Route path="*"                    element={<Navigate to="/projects" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}