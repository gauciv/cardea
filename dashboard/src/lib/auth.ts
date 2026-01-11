/**
 * Authentication utilities for Cardea Dashboard
 * Supports Hybrid Auth: Azure SWA (Social) + Custom JWT (Email/Pass)
 */

export interface UserInfo {
  userId: string;
  userDetails: string;
  userRoles: string[];
  identityProvider: 'aad' | 'google' | 'github' | 'twitter' | 'dev' | 'local';
  claims?: Record<string, string>;
}

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  error: string | null;
}

export const AUTH_ENDPOINTS = {
  microsoft: '/.auth/login/aad',
  google: '/.auth/login/google',
  github: '/.auth/login/github',
  logout: '/.auth/logout',
  me: '/.auth/me',
  purge: '/.auth/purge/aad'
} as const;

export const isAzureHosted = (): boolean => {
  if (typeof window === 'undefined') return false;
  const hostname = window.location.hostname;
  return (
    hostname.includes('azurestaticapps.net') ||
    hostname.includes('cardea') ||
    hostname.endsWith('.azurewebsites.net')
  );
};

/**
 * Get the current authenticated user (Hybrid Strategy)
 */
export async function getCurrentUser(): Promise<UserInfo | null> {
  // STRATEGY 1: Check Azure Static Web Apps (Social Login)
  if (isAzureHosted()) {
    try {
      const response = await fetch(AUTH_ENDPOINTS.me);
      if (response.ok) {
        const data = await response.json();
        if (data.clientPrincipal) {
          return {
            userId: data.clientPrincipal.userId,
            userDetails: data.clientPrincipal.userDetails,
            userRoles: data.clientPrincipal.userRoles || ['authenticated'],
            identityProvider: data.clientPrincipal.identityProvider,
            claims: data.clientPrincipal.claims?.reduce(
              (acc: Record<string, string>, claim: { typ: string; val: string }) => {
                acc[claim.typ] = claim.val;
                return acc;
              },
              {}
            )
          };
        }
      }
    } catch (error) {
      console.error('Failed to check Azure auth:', error);
    }
  }

  // STRATEGY 2: Check Local Storage (Email/Password Login)
  // This runs if Azure returns null OR if we are in dev mode
  const localToken = localStorage.getItem('cardea_auth_token');
  const localUserStr = localStorage.getItem('cardea_user');

  if (localToken && localUserStr) {
    try {
      const localUser = JSON.parse(localUserStr);
      return {
        userId: localUser.id || 'local-user',
        userDetails: localUser.email,
        userRoles: ['authenticated'], // Custom auth users are always authenticated
        identityProvider: 'local',
        claims: { name: localUser.full_name || localUser.email }
      };
    } catch (e) {
      console.error('Failed to parse local user:', e);
      localStorage.removeItem('cardea_auth_token');
      localStorage.removeItem('cardea_user');
    }
  }
  
  // STRATEGY 3: Local Dev Auth
  if (!isAzureHosted()) {
    const devAuth = localStorage.getItem('cardea_dev_auth');
    if (devAuth === 'true') {
      const devUser = localStorage.getItem('cardea_dev_user');
      if (devUser) {
        const parsed = JSON.parse(devUser);
        return {
          userId: 'dev-user-001',
          userDetails: parsed.email || 'dev@cardea.local',
          userRoles: ['authenticated', 'admin'],
          identityProvider: 'dev',
          claims: { name: parsed.name || 'Local User' }
        };
      }
    }
  }

  return null;
}

export function login(provider: 'microsoft' | 'google' | 'github', redirectPath: string = '/dashboard'): void {
  if (isAzureHosted()) {
    const redirectUrl = encodeURIComponent(window.location.origin + redirectPath);
    window.location.href = `${AUTH_ENDPOINTS[provider]}?post_login_redirect_uri=${redirectUrl}`;
  } else {
    localStorage.setItem('cardea_dev_auth', 'true');
    localStorage.setItem('cardea_dev_provider', provider);
    localStorage.setItem('cardea_dev_user', JSON.stringify({
      name: 'Local User',
      email: `user@${provider}.local`,
      provider
    }));
    window.location.href = redirectPath;
  }
}

export function logout(redirectPath: string = '/login'): void {
  // Clear Local Storage (Custom Auth)
  localStorage.removeItem('cardea_auth_token');
  localStorage.removeItem('cardea_user');
  localStorage.removeItem('cardea_dev_auth');
  localStorage.removeItem('cardea_dev_provider');
  localStorage.removeItem('cardea_dev_user');

  // Clear Azure Auth (Social)
  if (isAzureHosted()) {
    const redirectUrl = encodeURIComponent(window.location.origin + redirectPath);
    window.location.href = `${AUTH_ENDPOINTS.logout}?post_logout_redirect_uri=${redirectUrl}`;
  } else {
    window.location.href = redirectPath;
  }
}

export function hasRole(user: UserInfo | null, role: string): boolean {
  if (!user) return false;
  return user.userRoles.includes(role);
}

export function getDisplayName(user: UserInfo | null): string {
  if (!user) return 'Guest';
  if (user.claims?.name) return user.claims.name;
  if (user.claims?.['preferred_username']) return user.claims['preferred_username'];
  if (user.userDetails) {
    const emailName = user.userDetails.split('@')[0];
    return emailName.charAt(0).toUpperCase() + emailName.slice(1);
  }
  return 'User';
}

export function getProviderName(provider: string): string {
  switch (provider) {
    case 'aad': return 'Microsoft';
    case 'google': return 'Google';
    case 'github': return 'GitHub';
    case 'twitter': return 'Twitter';
    case 'dev': return 'Development';
    case 'local': return 'Email';
    default: return provider;
  }
}