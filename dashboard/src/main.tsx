import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import LoginPage from './components/LoginPage.tsx'
import LandingPage from './components/LandingPage.tsx'
import { DevicesPage } from './components/DevicesPage.tsx'
import { ProtectedRoute } from './components/ProtectedRoute.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        
        {/* Protected Routes - Require Authentication */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        } />
        <Route path="/devices" element={
          <ProtectedRoute>
            <DevicesPage />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
