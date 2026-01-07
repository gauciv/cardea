import React, { useState } from "react";
import { Eye, EyeOff, Loader2, ArrowLeft, CheckCircle, Mail, User, Lock } from "lucide-react";
import { useNavigate } from "react-router-dom";

/**
 * Registration Flow Steps
 */
type RegistrationStep = "info" | "otp" | "password" | "complete";

/**
 * Registration Page Component
 * 
 * Implements 3-step Native Authentication registration:
 * 1. Enter email, given name, family name → triggers OTP email
 * 2. Verify OTP code from email
 * 3. Set password → complete registration
 */
const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  
  // Registration step state
  const [step, setStep] = useState<RegistrationStep>("info");
  
  // Form data
  const [formData, setFormData] = useState({
    email: "",
    givenName: "",
    familyName: "",
    password: "",
    confirmPassword: "",
  });
  
  // OTP state
  const [otpCode, setOtpCode] = useState(["", "", "", "", "", ""]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  /**
   * Handle input changes
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  /**
   * Handle OTP input
   */
  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) {
      value = value[0];
    }
    
    if (!/^\d*$/.test(value)) return;
    
    const newOtp = [...otpCode];
    newOtp[index] = value;
    setOtpCode(newOtp);
    
    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      nextInput?.focus();
    }
    
    if (error) setError(null);
  };

  /**
   * Handle OTP paste
   */
  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").slice(0, 6);
    if (!/^\d+$/.test(pastedData)) return;
    
    const newOtp = [...otpCode];
    pastedData.split("").forEach((char, i) => {
      if (i < 6) newOtp[i] = char;
    });
    setOtpCode(newOtp);
  };

  /**
   * Handle OTP backspace
   */
  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otpCode[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      prevInput?.focus();
    }
  };

  /**
   * Step 1: Initiate Registration
   */
  const handleInitiateRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validate inputs
      if (!formData.email || !formData.givenName || !formData.familyName) {
        setError("Please fill in all fields.");
        setIsLoading(false);
        return;
      }

      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        setError("Please enter a valid email address.");
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          given_name: formData.givenName,
          family_name: formData.familyName,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      // Store session ID and move to OTP step
      setSessionId(data.session_id);
      setSuccess("Verification code sent to your email!");
      setStep("otp");
    } catch (err: any) {
      setError(err.message || "Failed to initiate registration. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Step 2: Verify OTP
   */
  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const code = otpCode.join("");
      if (code.length !== 6) {
        setError("Please enter the complete 6-digit code.");
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/verify-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          otp_code: code,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      setSuccess("Email verified! Now set your password.");
      setStep("password");
    } catch (err: any) {
      setError(err.message || "Invalid verification code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Step 3: Complete Registration
   */
  const handleCompleteRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validate password
      if (formData.password.length < 8) {
        setError("Password must be at least 8 characters long.");
        setIsLoading(false);
        return;
      }

      if (formData.password !== formData.confirmPassword) {
        setError("Passwords do not match.");
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/complete-registration`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          password: formData.password,
          given_name: formData.givenName,
          family_name: formData.familyName,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      // Store the access token
      if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
      }

      setStep("complete");
    } catch (err: any) {
      setError(err.message || "Failed to complete registration. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Resend OTP
   */
  const handleResendOTP = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/auth/resend-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to resend code");
      }

      // Update session ID if changed
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      
      setSuccess("New verification code sent!");
      setOtpCode(["", "", "", "", "", ""]);
    } catch (err: any) {
      setError(err.message || "Failed to resend code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Render Step Indicator
   */
  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {["info", "otp", "password"].map((s, index) => (
        <React.Fragment key={s}>
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
              step === s || (step === "complete" && s !== "complete")
                ? "bg-blue-600 text-white"
                : index < ["info", "otp", "password"].indexOf(step)
                ? "bg-green-500 text-white"
                : "bg-gray-200 text-gray-500"
            }`}
          >
            {index < ["info", "otp", "password"].indexOf(step) ? (
              <CheckCircle className="h-5 w-5" />
            ) : (
              index + 1
            )}
          </div>
          {index < 2 && (
            <div
              className={`w-16 h-1 mx-2 ${
                index < ["info", "otp", "password"].indexOf(step)
                  ? "bg-green-500"
                  : "bg-gray-200"
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  /**
   * Render Step 1: User Information
   */
  const renderInfoStep = () => (
    <form onSubmit={handleInitiateRegistration} className="space-y-6">
      <div className="space-y-2">
        <label htmlFor="email" className="block text-sm font-semibold text-gray-700">
          Email Address
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            id="email"
            name="email"
            type="email"
            required
            placeholder="you@example.com"
            value={formData.email}
            onChange={handleChange}
            className="block w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 
                     text-gray-900 placeholder-gray-400
                     focus:ring-2 focus:ring-blue-600 focus:border-transparent
                     transition-all duration-200 bg-gray-50"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label htmlFor="givenName" className="block text-sm font-semibold text-gray-700">
            First Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              id="givenName"
              name="givenName"
              type="text"
              required
              placeholder="John"
              value={formData.givenName}
              onChange={handleChange}
              className="block w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 
                       text-gray-900 placeholder-gray-400
                       focus:ring-2 focus:ring-blue-600 focus:border-transparent
                       transition-all duration-200 bg-gray-50"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="familyName" className="block text-sm font-semibold text-gray-700">
            Last Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              id="familyName"
              name="familyName"
              type="text"
              required
              placeholder="Doe"
              value={formData.familyName}
              onChange={handleChange}
              className="block w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 
                       text-gray-900 placeholder-gray-400
                       focus:ring-2 focus:ring-blue-600 focus:border-transparent
                       transition-all duration-200 bg-gray-50"
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white 
                 rounded-xl font-semibold text-lg shadow-sm
                 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 
                 disabled:opacity-70 transition-all duration-200"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <Loader2 className="animate-spin h-5 w-5 mr-2" />
            Sending Code...
          </span>
        ) : (
          "Continue"
        )}
      </button>
    </form>
  );

  /**
   * Render Step 2: OTP Verification
   */
  const renderOTPStep = () => (
    <form onSubmit={handleVerifyOTP} className="space-y-6">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Mail className="h-8 w-8 text-blue-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Check Your Email</h3>
        <p className="text-gray-600 text-sm">
          We've sent a 6-digit verification code to<br />
          <span className="font-semibold text-gray-900">{formData.email}</span>
        </p>
      </div>

      <div className="flex justify-center gap-2">
        {otpCode.map((digit, index) => (
          <input
            key={index}
            id={`otp-${index}`}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleOtpChange(index, e.target.value)}
            onKeyDown={(e) => handleOtpKeyDown(index, e)}
            onPaste={index === 0 ? handleOtpPaste : undefined}
            className="w-12 h-14 text-center text-xl font-bold rounded-xl border border-gray-200 
                     text-gray-900 focus:ring-2 focus:ring-blue-600 focus:border-transparent
                     transition-all duration-200 bg-gray-50"
          />
        ))}
      </div>

      <button
        type="submit"
        disabled={isLoading || otpCode.join("").length !== 6}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white 
                 rounded-xl font-semibold text-lg shadow-sm
                 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 
                 disabled:opacity-70 transition-all duration-200"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <Loader2 className="animate-spin h-5 w-5 mr-2" />
            Verifying...
          </span>
        ) : (
          "Verify Code"
        )}
      </button>

      <p className="text-center text-sm text-gray-600">
        Didn't receive the code?{" "}
        <button
          type="button"
          onClick={handleResendOTP}
          disabled={isLoading}
          className="text-blue-600 hover:text-blue-700 font-semibold"
        >
          Resend
        </button>
      </p>
    </form>
  );

  /**
   * Render Step 3: Password Setup
   */
  const renderPasswordStep = () => (
    <form onSubmit={handleCompleteRegistration} className="space-y-6">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Email Verified!</h3>
        <p className="text-gray-600 text-sm">
          Now create a secure password for your account
        </p>
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="block text-sm font-semibold text-gray-700">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            required
            placeholder="••••••••"
            value={formData.password}
            onChange={handleChange}
            className="block w-full pl-10 pr-12 py-3 rounded-xl border border-gray-200 
                     text-gray-900 placeholder-gray-400
                     focus:ring-2 focus:ring-blue-600 focus:border-transparent
                     transition-all duration-200 bg-gray-50"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600"
          >
            {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
          </button>
        </div>
        <p className="text-xs text-gray-500">Must be at least 8 characters</p>
      </div>

      <div className="space-y-2">
        <label htmlFor="confirmPassword" className="block text-sm font-semibold text-gray-700">
          Confirm Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            id="confirmPassword"
            name="confirmPassword"
            type={showConfirmPassword ? "text" : "password"}
            required
            placeholder="••••••••"
            value={formData.confirmPassword}
            onChange={handleChange}
            className="block w-full pl-10 pr-12 py-3 rounded-xl border border-gray-200 
                     text-gray-900 placeholder-gray-400
                     focus:ring-2 focus:ring-blue-600 focus:border-transparent
                     transition-all duration-200 bg-gray-50"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600"
          >
            {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white 
                 rounded-xl font-semibold text-lg shadow-sm
                 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 
                 disabled:opacity-70 transition-all duration-200"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <Loader2 className="animate-spin h-5 w-5 mr-2" />
            Creating Account...
          </span>
        ) : (
          "Create Account"
        )}
      </button>
    </form>
  );

  /**
   * Render Complete Step
   */
  const renderCompleteStep = () => (
    <div className="text-center">
      <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="h-10 w-10 text-green-600" />
      </div>
      <h3 className="text-2xl font-bold text-gray-900 mb-3">Welcome to Cardea!</h3>
      <p className="text-gray-600 mb-8">
        Your account has been created successfully.<br />
        You're now ready to explore the platform.
      </p>
      <button
        onClick={() => navigate("/dashboard")}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white 
                 rounded-xl font-semibold text-lg shadow-sm
                 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 
                 transition-all duration-200"
      >
        Go to Dashboard
      </button>
    </div>
  );

  return (
    <div className="min-h-screen w-full flex bg-white">
      {/* Left Section - Registration Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-8 lg:p-24">
        <div>
          {/* Logo & Back Button */}
          <div className="flex items-center justify-between mb-12">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center mr-2">
                <div className="h-4 w-4 border-2 border-white rounded-full"></div>
              </div>
              <h1 className="text-xl font-bold text-gray-900">Cardea</h1>
            </div>
            {step !== "complete" && (
              <button
                onClick={() => {
                  if (step === "info") {
                    navigate("/login");
                  } else if (step === "otp") {
                    setStep("info");
                  } else if (step === "password") {
                    setStep("otp");
                  }
                }}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="h-5 w-5 mr-1" />
                Back
              </button>
            )}
          </div>

          {/* Header */}
          {step !== "complete" && (
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                {step === "info" && "Create Your Account"}
                {step === "otp" && "Verify Your Email"}
                {step === "password" && "Set Your Password"}
              </h2>
              <p className="text-gray-600">
                {step === "info" && "Enter your details to get started with Cardea."}
                {step === "otp" && "We need to verify your email address."}
                {step === "password" && "Almost done! Create a secure password."}
              </p>
            </div>
          )}

          {/* Step Indicator */}
          {step !== "complete" && renderStepIndicator()}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200">
              <p className="text-red-600 text-sm font-medium">{error}</p>
            </div>
          )}

          {/* Success Message */}
          {success && step !== "complete" && (
            <div className="mb-6 p-4 rounded-xl bg-green-50 border border-green-200">
              <p className="text-green-600 text-sm font-medium">{success}</p>
            </div>
          )}

          {/* Step Content */}
          {step === "info" && renderInfoStep()}
          {step === "otp" && renderOTPStep()}
          {step === "password" && renderPasswordStep()}
          {step === "complete" && renderCompleteStep()}

          {/* Login Link */}
          {step === "info" && (
            <p className="mt-8 text-center text-sm text-gray-600">
              Already have an account?{" "}
              <button
                onClick={() => navigate("/login")}
                className="text-blue-600 hover:text-blue-700 font-semibold"
              >
                Log In
              </button>
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 flex items-center justify-between text-sm text-gray-500">
          <p>Copyright © 2025 Cardea</p>
          <button className="hover:text-gray-700">Privacy Policy</button>
        </div>
      </div>

      {/* Right Section - Promo */}
      <div className="hidden lg:flex w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 p-24 flex-col justify-center relative overflow-hidden">
        {/* Background Design Elements */}
        <div className="absolute top-0 right-0 -mt-20 -mr-20 text-blue-500 opacity-20">
          <svg width="400" height="400" viewBox="0 0 400 400" fill="none">
            <circle cx="200" cy="200" r="200" fill="currentColor" />
          </svg>
        </div>
        <div className="absolute bottom-0 left-0 -mb-20 -ml-20 text-blue-400 opacity-10">
          <svg width="300" height="300" viewBox="0 0 300 300" fill="none">
            <circle cx="150" cy="150" r="150" fill="currentColor" />
          </svg>
        </div>

        <div className="relative z-10">
          <h2 className="text-4xl font-bold text-white mb-6 leading-tight">
            Join the future of security monitoring
          </h2>
          <p className="text-blue-100 text-lg mb-8">
            Get real-time threat detection and instant alerts to keep your network safe.
          </p>
          <div className="space-y-4">
            <div className="flex items-center text-blue-100">
              <CheckCircle className="h-5 w-5 mr-3 text-green-400" />
              Real-time threat monitoring
            </div>
            <div className="flex items-center text-blue-100">
              <CheckCircle className="h-5 w-5 mr-3 text-green-400" />
              AI-powered analytics
            </div>
            <div className="flex items-center text-blue-100">
              <CheckCircle className="h-5 w-5 mr-3 text-green-400" />
              Enterprise-grade security
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
