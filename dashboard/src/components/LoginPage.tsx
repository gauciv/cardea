import * as React from 'react';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Import useNavigate
import { Loader2, Shield, Sparkles, Mail, Lock, User, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react';

// API base URL
const API_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8000';

// Social login icons
const GoogleIcon = () => (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
);

const MicrosoftIcon = () => (
    <svg className="h-5 w-5" viewBox="0 0 23 23">
        <path fill="#f35325" d="M1 1h10v10H1z"/>
        <path fill="#81bc06" d="M12 1h10v10H12z"/>
        <path fill="#05a6f0" d="M1 12h10v10H1z"/>
        <path fill="#ffba08" d="M12 12h10v10H12z"/>
    </svg>
);

// Azure Static Web Apps auth endpoints
const AUTH_ENDPOINTS = {
    microsoft: '/.auth/login/aad',
    google: '/.auth/login/google',
    logout: '/.auth/logout',
    me: '/.auth/me'
};

// Check if running on Azure Static Web Apps
const isAzureHosted = () => {
    return window.location.hostname.includes('azurestaticapps.net') || 
           window.location.hostname.includes('cardea');
};

type AuthMode = 'login' | 'register' | 'forgot-password' | 'verify-email' | 'reset-password';

interface FormState {
    email: string;
    password: string;
    confirmPassword: string;
    fullName: string;
}

const LoginPage: React.FC = () => {
    const navigate = useNavigate(); // Hook for navigation
    const [mode, setMode] = useState<AuthMode>('login');
    const [isLoading, setIsLoading] = useState<string | null>(null);
    const [checkingAuth, setCheckingAuth] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    
    const [form, setForm] = useState<FormState>({
        email: '',
        password: '',
        confirmPassword: '',
        fullName: ''
    });
    
    // Get token from URL for email verification or password reset
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    // Check if user is already authenticated
    useEffect(() => {
        // Handle verification/reset tokens
        if (window.location.pathname.includes('verify-email') && token) {
            setMode('verify-email');
            handleVerifyEmail(token);
            return;
        }
        if (window.location.pathname.includes('reset-password') && token) {
            setMode('reset-password');
            setCheckingAuth(false);
            return;
        }
        
        const checkAuth = async () => {
            if (isAzureHosted()) {
                try {
                    const response = await fetch(AUTH_ENDPOINTS.me);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.clientPrincipal) {
                            navigate('/dashboard'); // Use navigate instead of window.location
                            return;
                        }
                    }
                } catch {
                    console.log('Not authenticated');
                }
            } else {
                const devAuth = localStorage.getItem('cardea_dev_auth');
                if (devAuth === 'true') {
                    navigate('/dashboard'); // Use navigate instead of window.location
                    return;
                }
            }
            setCheckingAuth(false);
        };
        
        checkAuth();
    }, [token, navigate]);

    const handleVerifyEmail = async (verifyToken: string) => {
        setIsLoading('verify');
        try {
            const response = await fetch(`${API_URL}/api/auth/verify-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: verifyToken })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('cardea_auth_token', data.access_token);
                localStorage.setItem('cardea_user', JSON.stringify(data.user));
                localStorage.setItem('cardea_dev_auth', 'true');
                setSuccess('Email verified! Redirecting to dashboard...');
                setTimeout(() => {
                    navigate('/dashboard');
                }, 2000);
            } else {
                setError(data.detail || 'Verification failed');
                setCheckingAuth(false);
            }
        } catch {
            setError('Network error. Please try again.');
            setCheckingAuth(false);
        } finally {
            setIsLoading(null);
        }
    };

    const handleEmailLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading('email');
        
        try {
            const response = await fetch(`${API_URL}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: form.email,
                    password: form.password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('cardea_auth_token', data.access_token);
                localStorage.setItem('cardea_user', JSON.stringify(data.user));
                localStorage.setItem('cardea_dev_auth', 'true');
                navigate('/dashboard');
            } else {
                setError(data.detail || 'Login failed');
            }
        } catch  {
            setError('Network error. Please check your connection.');
        } finally {
            setIsLoading(null);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        
        if (form.password !== form.confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        
        if (form.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        
        setIsLoading('register');
        
        try {
            const response = await fetch(`${API_URL}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: form.email,
                    password: form.password,
                    full_name: form.fullName || undefined
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                setSuccess(data.message || 'Check your email to verify your account!');
                setMode('login');
                setForm({ ...form, password: '', confirmPassword: '' });
            } else {
                setError(data.detail || 'Registration failed');
            }
        } catch  {
            setError('Network error. Please try again.');
        } finally {
            setIsLoading(null);
        }
    };

    const handleForgotPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading('forgot');
        
        try {
            const response = await fetch(`${API_URL}/api/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: form.email })
            });
            
            const data = await response.json();
            setSuccess(data.message || 'If an account exists, you will receive a reset email.');
            setMode('login');
        } catch  {
            setError('Network error. Please try again.');
        } finally {
            setIsLoading(null);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        
        if (form.password !== form.confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        
        if (form.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        
        setIsLoading('reset');
        
        try {
            const response = await fetch(`${API_URL}/api/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    new_password: form.password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                setSuccess('Password reset! You can now log in.');
                setMode('login');
                navigate('/login');
            } else {
                setError(data.detail || 'Reset failed');
            }
        } catch  {
            setError('Network error. Please try again.');
        } finally {
            setIsLoading(null);
        }
    };

    const handleSocialLogin = (provider: 'microsoft' | 'google') => {
        setIsLoading(provider);
        
        if (isAzureHosted()) {
            // Social Login MUST use window.location because it leaves the app
            const redirectUrl = encodeURIComponent(window.location.origin + '/dashboard');
            window.location.href = `${AUTH_ENDPOINTS[provider]}?post_login_redirect_uri=${redirectUrl}`;
        } else {
            setTimeout(() => {
                localStorage.setItem('cardea_dev_auth', 'true');
                localStorage.setItem('cardea_dev_provider', provider);
                localStorage.setItem('cardea_dev_user', JSON.stringify({
                    name: 'Demo User',
                    email: `demo@${provider}.com`,
                    provider
                }));
                navigate('/dashboard');
            }, 1000);
        }
    };

    const updateForm = (field: keyof FormState, value: string) => {
        setForm(prev => ({ ...prev, [field]: value }));
        setError(null);
    };

    if (checkingAuth) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
                    <p className="text-slate-400">
                        {mode === 'verify-email' ? 'Verifying your email...' : 'Checking authentication...'}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen w-full flex bg-slate-950">
            {/* Left Section - Login Form */}
            <div className="w-full lg:w-1/2 flex flex-col justify-between p-8 lg:p-16 xl:p-24">
                {/* Logo */}
                <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
                    <Shield className="h-8 w-8 text-cyan-500" />
                    <span className="text-2xl font-bold text-white tracking-tight">
                        CARDEA <span className="text-slate-500 font-normal">Security</span>
                    </span>
                </div>

                {/* Form Section */}
                <div className="max-w-md w-full mx-auto space-y-6">
                    {/* Header */}
                    <div className="space-y-2">
                        {mode !== 'login' && mode !== 'verify-email' && (
                            <button 
                                onClick={() => { setMode('login'); setError(null); setSuccess(null); }}
                                className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-sm mb-4"
                            >
                                <ArrowLeft className="w-4 h-4" /> Back to login
                            </button>
                        )}
                        <h1 className="text-3xl font-bold text-white">
                            {mode === 'login' && 'Welcome back'}
                            {mode === 'register' && 'Create an account'}
                            {mode === 'forgot-password' && 'Reset your password'}
                            {mode === 'reset-password' && 'Set new password'}
                            {mode === 'verify-email' && 'Email Verified!'}
                        </h1>
                        <p className="text-slate-400">
                            {mode === 'login' && 'Sign in to monitor your network security'}
                            {mode === 'register' && 'Start protecting your network with AI'}
                            {mode === 'forgot-password' && 'Enter your email to receive a reset link'}
                            {mode === 'reset-password' && 'Choose a strong password'}
                        </p>
                    </div>

                    {/* Success Message */}
                    {success && (
                        <div className="flex items-center gap-3 bg-green-950/50 border border-green-800 rounded-lg p-4 text-green-300">
                            <CheckCircle2 className="w-5 h-5 shrink-0" />
                            <p className="text-sm">{success}</p>
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="flex items-center gap-3 bg-red-950/50 border border-red-800 rounded-lg p-4 text-red-300">
                            <AlertCircle className="w-5 h-5 shrink-0" />
                            <p className="text-sm">{error}</p>
                        </div>
                    )}

                    {/* Login Form */}
                    {mode === 'login' && (
                        <>
                            <form onSubmit={handleEmailLogin} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                        <input
                                            type="email"
                                            value={form.email}
                                            onChange={(e) => updateForm('email', e.target.value)}
                                            className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                                            placeholder="you@company.com"
                                            required
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                        <input
                                            type="password"
                                            value={form.password}
                                            onChange={(e) => updateForm('password', e.target.value)}
                                            className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                                            placeholder="••••••••"
                                            required
                                        />
                                    </div>
                                </div>
                                <div className="flex justify-end">
                                    <button 
                                        type="button"
                                        onClick={() => setMode('forgot-password')}
                                        className="text-sm text-cyan-400 hover:text-cyan-300"
                                    >
                                        Forgot password?
                                    </button>
                                </div>
                                <button
                                    type="submit"
                                    disabled={isLoading === 'email'}
                                    className="w-full py-3 bg-linear-to-r from-cyan-600 to-cyan-500 text-white font-medium rounded-lg hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                                >
                                    {isLoading === 'email' ? (
                                        <><Loader2 className="w-5 h-5 animate-spin" /> Signing in...</>
                                    ) : (
                                        'Sign in with Email'
                                    )}
                                </button>
                            </form>

                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-slate-800"></div>
                                </div>
                                <div className="relative flex justify-center text-sm">
                                    <span className="px-4 bg-slate-950 text-slate-500">or continue with</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <button
                                    onClick={() => handleSocialLogin('google')}
                                    disabled={isLoading !== null}
                                    className="flex items-center justify-center gap-3 py-3 px-4 bg-slate-900 border border-slate-700 rounded-lg text-white hover:bg-slate-800 disabled:opacity-50 transition-all"
                                >
                                    {isLoading === 'google' ? <Loader2 className="h-5 w-5 animate-spin" /> : <GoogleIcon />}
                                    <span>Google</span>
                                </button>
                                <button
                                    onClick={() => handleSocialLogin('microsoft')}
                                    disabled={isLoading !== null}
                                    className="flex items-center justify-center gap-3 py-3 px-4 bg-slate-900 border border-slate-700 rounded-lg text-white hover:bg-slate-800 disabled:opacity-50 transition-all"
                                >
                                    {isLoading === 'microsoft' ? <Loader2 className="h-5 w-5 animate-spin" /> : <MicrosoftIcon />}
                                    <span>Microsoft</span>
                                </button>
                            </div>

                            <p className="text-center text-slate-400">
                                Don't have an account?{' '}
                                <button onClick={() => setMode('register')} className="text-cyan-400 hover:text-cyan-300">
                                    Sign up
                                </button>
                            </p>
                        </>
                    )}

                    {/* Register Form */}
                    {mode === 'register' && (
                        <form onSubmit={handleRegister} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Full Name (optional)</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="text"
                                        value={form.fullName}
                                        onChange={(e) => updateForm('fullName', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="Jane Smith"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="email"
                                        value={form.email}
                                        onChange={(e) => updateForm('email', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="you@company.com"
                                        required
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="password"
                                        value={form.password}
                                        onChange={(e) => updateForm('password', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="At least 8 characters"
                                        required
                                        minLength={8}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Confirm Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="password"
                                        value={form.confirmPassword}
                                        onChange={(e) => updateForm('confirmPassword', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>
                            </div>
                            <button
                                type="submit"
                                disabled={isLoading === 'register'}
                                className="w-full py-3 bg-linear-to-r from-cyan-600 to-cyan-500 text-white font-medium rounded-lg hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                            >
                                {isLoading === 'register' ? (
                                    <><Loader2 className="w-5 h-5 animate-spin" /> Creating account...</>
                                ) : (
                                    'Create account'
                                )}
                            </button>
                            <p className="text-center text-sm text-slate-500">
                                By signing up, you agree to our Terms of Service and Privacy Policy
                            </p>
                        </form>
                    )}

                    {/* Forgot Password Form */}
                    {mode === 'forgot-password' && (
                        <form onSubmit={handleForgotPassword} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="email"
                                        value={form.email}
                                        onChange={(e) => updateForm('email', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="you@company.com"
                                        required
                                    />
                                </div>
                            </div>
                            <button
                                type="submit"
                                disabled={isLoading === 'forgot'}
                                className="w-full py-3 bg-linear-to-r from-cyan-600 to-cyan-500 text-white font-medium rounded-lg hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                            >
                                {isLoading === 'forgot' ? (
                                    <><Loader2 className="w-5 h-5 animate-spin" /> Sending...</>
                                ) : (
                                    'Send reset link'
                                )}
                            </button>
                        </form>
                    )}

                    {/* Reset Password Form */}
                    {mode === 'reset-password' && (
                        <form onSubmit={handleResetPassword} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">New Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="password"
                                        value={form.password}
                                        onChange={(e) => updateForm('password', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="At least 8 characters"
                                        required
                                        minLength={8}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">Confirm Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-500" />
                                    <input
                                        type="password"
                                        value={form.confirmPassword}
                                        onChange={(e) => updateForm('confirmPassword', e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>
                            </div>
                            <button
                                type="submit"
                                disabled={isLoading === 'reset'}
                                className="w-full py-3 bg-linear-to-r from-cyan-600 to-cyan-500 text-white font-medium rounded-lg hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                            >
                                {isLoading === 'reset' ? (
                                    <><Loader2 className="w-5 h-5 animate-spin" /> Resetting...</>
                                ) : (
                                    'Reset password'
                                )}
                            </button>
                        </form>
                    )}
                    {/* Dev Mode Notice */}
                    {!isAzureHosted() && mode === 'login' && (
                        <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                            <p className="text-xs text-yellow-500">
                                🔧 <strong>Development Mode:</strong> Running locally. Email verification emails will be logged to console.
                            </p>
                        </div>
                    )}
                </div>
                {/* Footer */}
                <div className="text-center lg:text-left text-sm text-slate-500">
                    <p>© 2026 Cardea Security. Protected by AI.</p>
                </div>
            </div>
            {/* Right Section - Feature Showcase */}
            <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-linear-to-br from-slate-900 via-cyan-950/30 to-slate-900">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(34,211,238,0.1),transparent_50%)]" />
                <div className="relative z-10 flex flex-col justify-center p-16 xl:p-24 space-y-8">
                    <div className="flex items-center gap-2 text-cyan-400">
                        <Sparkles className="w-5 h-5" />
                        <span className="text-sm font-medium uppercase tracking-wider">AI-Powered Security</span>
                    </div>
                    
                    <h2 className="text-4xl xl:text-5xl font-bold text-white leading-tight">
                        Protect your network with intelligent threat detection
                    </h2>
                    
                    <p className="text-lg text-slate-400 max-w-md">
                        Cardea uses machine learning to detect anomalies, correlate threats, and take automated action to keep your network safe.
                    </p>

                    <div className="space-y-4">
                        {[
                            { title: 'Real-time Monitoring', desc: 'Continuous network analysis' },
                            { title: 'AI Threat Detection', desc: 'ML-powered anomaly detection' },
                            { title: 'Automated Response', desc: 'Instant threat mitigation' },
                            { title: 'Data Isolation', desc: 'Your data stays private' },
                        ].map((feature, i) => (
                            <div key={i} className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                                    <Shield className="w-5 h-5 text-cyan-400" />
                                </div>
                                <div>
                                    <p className="font-medium text-white">{feature.title}</p>
                                    <p className="text-sm text-slate-400">{feature.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;