import { PublicClientApplication, LogLevel } from '@azure/msal-browser';
import type { Configuration } from '@azure/msal-browser';

/**
 * MICROSOFT ENTRA (AZURE AD) CONFIGURATION
 */

// Read environment variables
const AZURE_CLIENT_ID = import.meta.env.VITE_AZURE_CLIENT_ID || '';
const AZURE_TENANT_ID = import.meta.env.VITE_AZURE_TENANT_ID || '';
const AZURE_TENANT_NAME = import.meta.env.VITE_AZURE_TENANT_NAME || '';
// For External ID, use the full authority with tenant ID
const AZURE_AUTHORITY = import.meta.env.VITE_AZURE_AUTHORITY 
  ? `${import.meta.env.VITE_AZURE_AUTHORITY}${AZURE_TENANT_ID}`
  : `https://login.microsoftonline.com/${AZURE_TENANT_ID}`;
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || window.location.origin;
const POST_LOGOUT_REDIRECT_URI = import.meta.env.VITE_POST_LOGOUT_REDIRECT_URI || window.location.origin;

// Check if Azure authentication is properly configured
export const isAzureAuthEnabled = (): boolean => {
  const isEnabled = import.meta.env.VITE_ENABLE_AZURE_AUTH === 'true';
  const hasClientId = AZURE_CLIENT_ID && AZURE_CLIENT_ID !== 'PASTE_YOUR_MICROSOFT_CLIENT_ID_HERE';
  const hasTenantId = AZURE_TENANT_ID && AZURE_TENANT_ID !== 'PASTE_YOUR_MICROSOFT_TENANT_ID_HERE';
  
  if (!isEnabled) {
    console.warn('Azure authentication is disabled in environment configuration');
    return false;
  }
  
  if (!hasClientId || !hasTenantId) {
    console.warn('Azure authentication credentials are not configured. Please update your .env file.');
    return false;
  }
  
  return true;
};

/**
 * MSAL Configuration for Microsoft Authentication
 * See: https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig: Configuration = {
  auth: {
    clientId: AZURE_CLIENT_ID,
    authority: AZURE_AUTHORITY,
    redirectUri: REDIRECT_URI,
    postLogoutRedirectUri: POST_LOGOUT_REDIRECT_URI,
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'localStorage', // Use localStorage for persistent sessions
    storeAuthStateInCookie: false, // Set to true if you have issues with IE11 or Edge
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            return;
          case LogLevel.Info:
            console.info(message);
            return;
          case LogLevel.Verbose:
            console.debug(message);
            return;
          case LogLevel.Warning:
            console.warn(message);
            return;
        }
      },
      logLevel: import.meta.env.VITE_DEBUG === 'true' ? LogLevel.Verbose : LogLevel.Warning,
    },
  },
};

/**
 * Scopes required for login
 * For External ID, use basic OIDC scopes
 */
export const loginRequest = {
  scopes: ['openid', 'profile', 'email'],
};

/**
 * Scopes required for accessing your backend API
 * This must match the scope you exposed in Azure Portal -> Expose an API
 */
export const apiRequest = {
  scopes: [
    import.meta.env.VITE_API_SCOPES || `api://${AZURE_CLIENT_ID}/access_as_user`,
  ],
};

/**
 * Scopes for silent token acquisition (background token refresh)
 */
export const tokenRequest = {
  scopes: [...loginRequest.scopes, ...apiRequest.scopes],
};

/**
 * Initialize MSAL instance
 * This is the main authentication client for Microsoft
 */
export const msalInstance = isAzureAuthEnabled() 
  ? new PublicClientApplication(msalConfig)
  : null;

/**
 * GOOGLE OAUTH 2.0 CONFIGURATION
 */

// Google OAuth Client ID from Google Cloud Console
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

// Check if Google authentication is properly configured
export const isGoogleAuthEnabled = (): boolean => {
  const isEnabled = import.meta.env.VITE_ENABLE_GOOGLE_AUTH === 'true';
  const hasClientId = GOOGLE_CLIENT_ID && GOOGLE_CLIENT_ID !== 'PASTE_YOUR_GOOGLE_CLIENT_ID_HERE';
  
  if (!isEnabled) {
    console.warn('Google authentication is disabled in environment configuration');
    return false;
  }
  
  if (!hasClientId) {
    console.warn('Google authentication credentials are not configured. Please update your .env file.');
    return false;
  }
  
  return true;
};

/**
 * Google OAuth Configuration
 */
export const googleConfig = {
  clientId: GOOGLE_CLIENT_ID,
  redirectUri: REDIRECT_URI,
  // Scopes determine what data your app can access
  scope: 'openid email profile',
  // Response type for OAuth 2.0 flow
  responseType: 'code', // Use authorization code flow for better security
};

/**
 * API Configuration
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Debug logging helper
 */
export const logAuthConfig = () => {
  if (import.meta.env.VITE_DEBUG === 'true') {
    console.group('🔐 Authentication Configuration');
    console.log('Azure Auth Enabled:', isAzureAuthEnabled());
    console.log('Google Auth Enabled:', isGoogleAuthEnabled());
    console.log('Microsoft Client ID:', AZURE_CLIENT_ID ? '✓ Configured' : '✗ Missing');
    console.log('Microsoft Tenant ID:', AZURE_TENANT_ID ? '✓ Configured' : '✗ Missing');
    console.log('Google Client ID:', GOOGLE_CLIENT_ID ? '✓ Configured' : '✗ Missing');
    console.log('API URL:', API_URL);
    console.log('Redirect URI:', REDIRECT_URI);
    console.groupEnd();
  }
};

// Log configuration on load (only in development)
if (import.meta.env.DEV) {
  logAuthConfig();
}

export default {
  msalInstance,
  msalConfig,
  loginRequest,
  apiRequest,
  tokenRequest,
  googleConfig,
  isAzureAuthEnabled,
  isGoogleAuthEnabled,
  API_URL,
};
