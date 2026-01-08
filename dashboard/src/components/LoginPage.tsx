import React, { useState, useEffect } from 'react';
import { Loader2, Shield, Sparkles } from 'lucide-react';

// Social login icons
const GoogleIcon = () => (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
        <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            fill="#4285F4"
        />
        <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
        />
        <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
        />
        <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
        />
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

// Check if running on Azure Static Web Apps (production) or locally
const isAzureHosted = () => {
    return window.location.hostname.includes('azurestaticapps.net') || 
           window.location.hostname.includes('cardea');
};

const LoginPage: React.FC = () => {
    const [isLoading, setIsLoading] = useState<string | null>(null);
    const [checkingAuth, setCheckingAuth] = useState(true);

    // Check if user is already authenticated
    useEffect(() => {
        const checkAuth = async () => {
            if (isAzureHosted()) {
                try {
                    const response = await fetch(AUTH_ENDPOINTS.me);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.clientPrincipal) {
                            // Redirect to dashboard if already logged in
                            window.location.href = '/dashboard';
                            return;
                        }
                    }
                } catch (error) {
                    console.log('Not authenticated or running locally');
                }
            } else {
                // Check for dev auth
                const devAuth = localStorage.getItem('cardea_dev_auth');
                if (devAuth === 'true') {
                    window.location.href = '/dashboard';
                    return;
                }
            }
            setCheckingAuth(false);
        };
        
        checkAuth();
    }, []);

    const handleSocialLogin = (provider: 'microsoft' | 'google') => {
        setIsLoading(provider);
        
        if (isAzureHosted()) {
            // Use Azure Static Web Apps built-in auth
            const redirectUrl = encodeURIComponent(window.location.origin + '/dashboard');
            window.location.href = `${AUTH_ENDPOINTS[provider]}?post_login_redirect_uri=${redirectUrl}`;
        } else {
            // Dev mode: simulate login
            setTimeout(() => {
                localStorage.setItem('cardea_dev_auth', 'true');
                localStorage.setItem('cardea_dev_provider', provider);
                localStorage.setItem('cardea_dev_user', JSON.stringify({
                    name: 'Demo User',
                    email: `demo@${provider}.com`,
                    provider
                }));
                window.location.href = '/dashboard';
            }, 1000);
        }
    };

    if (checkingAuth) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
                    <p className="text-slate-400">Checking authentication...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen w-full flex bg-slate-950">
            {/* Left Section - Login Form */}
            <div className="w-full lg:w-1/2 flex flex-col justify-between p-8 lg:p-16 xl:p-24">
                <div>
                    {/* Logo */}
                    <div className="flex items-center mb-16">
                        <div className="h-10 w-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center mr-3 shadow-lg shadow-cyan-500/20">
                            <Shield className="h-5 w-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white tracking-tight">CARDEA</h1>
                            <p className="text-[10px] text-slate-500 uppercase tracking-widest">Security Oracle</p>
                        </div>
                    </div>

                    {/* Header */}
                    <div className="mb-10">
                        <h2 className="text-3xl lg:text-4xl font-bold text-white mb-3">
                            Welcome to Cardea
                        </h2>
                        <p className="text-slate-400 text-lg">
                            Sign in to access your AI-powered security dashboard.
                        </p>
                    </div>

                    {/* Social Login Buttons */}
                    <div className="space-y-4">
                        <button
                            onClick={() => handleSocialLogin('google')}
                            disabled={isLoading !== null}
                            className="w-full flex items-center justify-center gap-3 px-6 py-4 
                                     bg-white hover:bg-gray-50 text-gray-800 
                                     rounded-xl font-semibold text-base shadow-lg
                                     border border-gray-200
                                     focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 
                                     disabled:opacity-70 transition-all duration-200
                                     hover:scale-[1.02] active:scale-[0.98]"
                        >
                            {isLoading === 'google' ? (
                                <Loader2 className="animate-spin h-5 w-5" />
                            ) : (
                                <GoogleIcon />
                            )}
                            <span>Continue with Google</span>
                        </button>

                        <button
                            onClick={() => handleSocialLogin('microsoft')}
                            disabled={isLoading !== null}
                            className="w-full flex items-center justify-center gap-3 px-6 py-4 
                                     bg-slate-800 hover:bg-slate-700 text-white 
                                     rounded-xl font-semibold text-base shadow-lg
                                     border border-slate-700
                                     focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 
                                     disabled:opacity-70 transition-all duration-200
                                     hover:scale-[1.02] active:scale-[0.98]"
                        >
                            {isLoading === 'microsoft' ? (
                                <Loader2 className="animate-spin h-5 w-5" />
                            ) : (
                                <MicrosoftIcon />
                            )}
                            <span>Continue with Microsoft</span>
                        </button>
                    </div>

                    {/* Info Box */}
                    <div className="mt-8 p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                        <div className="flex items-start gap-3">
                            <Sparkles className="w-5 h-5 text-cyan-500 flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="text-sm text-slate-300 font-medium">Secure Authentication</p>
                                <p className="text-xs text-slate-500 mt-1">
                                    We use Microsoft Entra ID for enterprise-grade security. 
                                    Your credentials are never stored on our servers.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Dev Mode Notice */}
                    {!isAzureHosted() && (
                        <div className="mt-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                            <p className="text-xs text-yellow-500">
                                🔧 <strong>Development Mode:</strong> Running locally. 
                                Social login will simulate authentication.
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="mt-12 flex flex-col sm:flex-row items-center justify-between text-sm text-slate-500 gap-4">
                    <p>© 2026 Cardea Security • Imagine Cup</p>
                    <div className="flex gap-4">
                        <a href="/privacy" className="hover:text-slate-300 transition-colors">Privacy</a>
                        <a href="/terms" className="hover:text-slate-300 transition-colors">Terms</a>
                    </div>
                </div>
            </div>

            {/* Right Section - Hero */}
            <div className="hidden lg:flex w-1/2 bg-gradient-to-br from-cyan-600 via-blue-600 to-blue-800 p-16 xl:p-24 flex-col justify-center relative overflow-hidden">
                {/* Background Pattern */}
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/2" />
                    <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/2 -translate-x-1/2" />
                </div>

                {/* Content */}
                <div className="relative z-10 max-w-lg">
                    <div className="flex items-center gap-2 mb-6">
                        <div className="h-2 w-2 bg-cyan-300 rounded-full animate-pulse" />
                        <span className="text-cyan-200 text-sm font-medium uppercase tracking-wider">
                            AI-Powered Protection
                        </span>
                    </div>
                    
                    <h2 className="text-4xl xl:text-5xl font-bold text-white mb-6 leading-tight">
                        Stay one step ahead of every threat.
                    </h2>
                    
                    <p className="text-blue-100 text-lg mb-8 leading-relaxed">
                        Cardea combines edge-based intrusion detection with cloud AI analytics 
                        to protect your network in real-time. Simple enough for home use, 
                        powerful enough for enterprise.
                    </p>

                    {/* Feature List */}
                    <div className="space-y-4">
                        {[
                            'Real-time threat detection with Zeek & Suricata',
                            'AI-powered anomaly detection with KitNET',
                            'Natural language security insights with GPT-4o',
                            'One-click response actions'
                        ].map((feature, index) => (
                            <div key={index} className="flex items-center gap-3">
                                <div className="h-6 w-6 rounded-full bg-white/20 flex items-center justify-center">
                                    <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <span className="text-blue-100 text-sm">{feature}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;