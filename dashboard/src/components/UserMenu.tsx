/**
 * User Menu Component for authenticated users
 * Shows user avatar, name, and logout option
 */

import { useState, useRef, useEffect } from 'react';
import { LogOut, ChevronDown, Shield, Settings } from 'lucide-react';
import { getDisplayName, logout, type UserInfo } from '../lib/auth';

interface UserMenuProps {
  user: UserInfo;
}

export const UserMenu: React.FC<UserMenuProps> = ({ user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayName = getDisplayName(user);
  const email = user.userDetails || '';
  
  // Get provider icon/color
  const getProviderBadge = () => {
    const provider = user.identityProvider?.toLowerCase() || '';
    if (provider.includes('google')) {
      return { color: 'bg-red-500', label: 'Google' };
    }
    if (provider.includes('aad') || provider.includes('microsoft') || provider.includes('azure')) {
      return { color: 'bg-blue-500', label: 'Microsoft' };
    }
    if (provider.includes('github')) {
      return { color: 'bg-slate-700', label: 'GitHub' };
    }
    return { color: 'bg-cyan-500', label: 'Local' };
  };

  const providerBadge = getProviderBadge();

  // Generate avatar initials
  const getInitials = () => {
    const parts = displayName.split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return displayName.slice(0, 2).toUpperCase();
  };

  const handleLogout = () => {
    // UPDATED: Redirect to Home Page ('/') instead of Login
    logout('/');
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* User Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 hover:border-slate-600 transition-all"
      >
        {/* Avatar */}
        <div className="w-6 h-6 rounded-full bg-linear-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-[10px] font-bold text-white">
          {getInitials()}
        </div>
        
        {/* Name (hidden on small screens) */}
        <span className="hidden sm:block text-xs font-medium text-slate-300 max-w-25 truncate">
          {displayName}
        </span>
        
        {/* Provider Badge */}
        <span className={`w-1.5 h-1.5 rounded-full ${providerBadge.color}`} title={`Signed in with ${providerBadge.label}`} />
        
        <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-slate-900 border border-slate-800 rounded-lg shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200 z-50">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-linear-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-sm font-bold text-white">
                {getInitials()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{displayName}</p>
                <p className="text-xs text-slate-500 truncate">{email}</p>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${providerBadge.color}`} />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                Signed in via {providerBadge.label}
              </span>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            {/* Role Badge */}
            <div className="px-4 py-2 flex items-center gap-3 text-slate-400">
              <Shield className="w-4 h-4" />
              <span className="text-xs">
                {user.userRoles?.includes('admin') ? 'Administrator' : 'Security Analyst'}
              </span>
            </div>

            {/* Divider */}
            <div className="my-1 border-t border-slate-800" />

            {/* Settings (placeholder) */}
            <button
              className="w-full px-4 py-2 flex items-center gap-3 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors text-left"
              onClick={() => setIsOpen(false)}
              disabled
            >
              <Settings className="w-4 h-4" />
              <span className="text-xs">Settings</span>
              <span className="ml-auto text-[10px] text-slate-600">Coming soon</span>
            </button>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 flex items-center gap-3 text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-colors text-left"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-xs font-medium">Sign Out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserMenu;