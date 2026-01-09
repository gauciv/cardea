import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import LoginPage from './components/LoginPage.tsx'
import LandingPage from './components/LandingPage.tsx'
import { DevicesPage } from './components/DevicesPage.tsx' // Import the new page

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Landing Page */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Login Page */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Dashboard (Main App) */}
        <Route path="/dashboard" element={<App />} />

        {/* Devices Management Page */}
        <Route path="/devices" element={<DevicesPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)