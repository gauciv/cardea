import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom' // Import these
import './index.css'
import App from './App.tsx'
import LoginPage from './components/LoginPage.tsx' // Import your Login Page
import LandingPage from './components/LandingPage.tsx' // Import Landing Page

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* This tells React: When path is "/", show LandingPage */}
        <Route path="/" element={<LandingPage />} />
        
        {/* When path is "/login", show LoginPage */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* When path is "/dashboard", show the App (Dashboard) */}
        <Route path="/dashboard" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)