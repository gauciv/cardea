import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom"; // Import these
import "./index.css";
import App from "./App.tsx";
import LoginPage from "./components/LoginPage.tsx"; // Import your Login Page
import RegisterPage from "./components/RegisterPage.tsx"; // Import Register Page
import { AuthProvider } from "./contexts/AuthContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Login Page - Default route */}
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Registration Page - Native Authentication */}
          <Route path="/register" element={<RegisterPage />} />

          {/* Dashboard - Main App */}
          <Route path="/dashboard" element={<App />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>
);
