import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { PublicClientApplication } from '@azure/msal-browser';
import type { AuthenticationResult } from '@azure/msal-browser';
import { msalConfig, loginRequest, isAzureAuthEnabled } from '../authConfig';

// Initialize MSAL instance
let msalInstance: PublicClientApplication | null = null;

// Initialize MSAL with error handling
const initializeMsal = async () => {
  if (isAzureAuthEnabled()) {
    try {
      msalInstance = new PublicClientApplication(msalConfig);
      await msalInstance.initialize();
      console.log('✅ MSAL initialized successfully');
      console.log('Authority:', msalConfig.auth.authority);
      console.log('Client ID:', msalConfig.auth.clientId);
    } catch (error) {
      console.error('❌ Failed to initialize MSAL:', error);
      msalInstance = null;
    }
  } else {
    console.warn('⚠️ Azure authentication is disabled');
  }
};

interface User {
  id: string;
  email: string;
  name: string;
  provider: 'azure' | 'google' | 'traditional';
  picture?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithMicrosoft: () => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  azureAuthEnabled: boolean;
  googleAuthEnabled: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [azureAuthEnabled, setAzureAuthEnabled] = useState(false);
  const [googleAuthEnabled] = useState(
    import.meta.env.VITE_ENABLE_GOOGLE_AUTH === 'true'
  );

  useEffect(() => {
    // Initialize MSAL and check session
    const init = async () => {
      await initializeMsal();
      setAzureAuthEnabled(isAzureAuthEnabled() && msalInstance !== null);
      await checkExistingSession();
    };
    init();
  }, []);

  const checkExistingSession = async () => {
    try {
      setIsLoading(true);
      
      // Check localStorage for session
      const storedUser = localStorage.getItem('user');
      const storedToken = localStorage.getItem('access_token');
      
      if (storedUser && storedToken) {
        setUser(JSON.parse(storedUser));
      } else if (msalInstance) {
        // Check MSAL cache for Microsoft session
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          const account = accounts[0];
          setUser({
            id: account.localAccountId,
            email: account.username,
            name: account.name || account.username,
            provider: 'azure',
          });
        }
      }
    } catch (error) {
      console.error('Error checking session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username: email, password }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      
      const userData: User = {
        id: data.user.id,
        email: data.user.email,
        name: data.user.full_name || data.user.email,
        provider: 'traditional',
      };

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('access_token', data.access_token);
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithMicrosoft = async () => {
    console.log('🔵 Microsoft login initiated');
    console.log('MSAL Instance:', msalInstance ? 'Available' : 'NULL');
    console.log('Azure Auth Enabled:', azureAuthEnabled);
    
    if (!msalInstance) {
      const errorMsg = 'Microsoft authentication is not configured. Check console for MSAL initialization errors.';
      console.error('❌', errorMsg);
      alert(errorMsg);
      throw new Error(errorMsg);
    }

    setIsLoading(true);
    try {
      console.log('🔵 Opening Microsoft login popup...');
      console.log('Login request scopes:', loginRequest.scopes);
      
      // Trigger Microsoft login popup
      const loginResponse: AuthenticationResult = await msalInstance.loginPopup(loginRequest);
      
      console.log('✅ Microsoft login successful:', loginResponse.account?.username);
      console.log('ID Token received:', loginResponse.idToken ? 'Yes' : 'No');

      // For External ID, use the ID token (not access token)
      // The idToken contains user claims and is what we validate on backend
      const token = loginResponse.idToken;

      // Send token to backend for validation
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth/azure/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ access_token: token }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Backend authentication failed:', errorData);
        throw new Error(errorData.detail || 'Backend authentication failed');
      }

      const data = await response.json();
      
      const userData: User = {
        id: loginResponse.account.localAccountId,
        email: loginResponse.account.username,
        name: loginResponse.account.name || loginResponse.account.username,
        provider: 'azure',
      };

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('access_token', data.access_token);
    } catch (error) {
      console.error('Microsoft login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async () => {
    setIsLoading(true);
    try {
      // Initialize Google Sign-In
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      
      if (!clientId) {
        throw new Error('Google Client ID not configured');
      }

      // This will be handled by the Google Sign-In button component
      // For now, throw an error to indicate it should be implemented in the component
      throw new Error('Please use the Google Sign-In button component');
    } catch (error) {
      console.error('Google login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      // Clear local storage
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');

      // Logout from MSAL if Microsoft user
      if (user?.provider === 'azure' && msalInstance) {
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          await msalInstance.logoutPopup({
            account: accounts[0],
          });
        }
      }

      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    loginWithMicrosoft,
    loginWithGoogle,
    logout,
    azureAuthEnabled,
    googleAuthEnabled,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
