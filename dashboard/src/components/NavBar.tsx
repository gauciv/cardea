import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, User, LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { logout, getDisplayName, type UserInfo } from '../lib/auth';

interface NavBarProps {
  user: UserInfo | null;
}

const navItems = [
  { id: 'dashboard', path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'devices', path: '/devices', icon: Server, label: 'Sentry Devices' },
  { id: 'settings', path: '/settings', icon: Settings, label: 'Settings' },
  { id: 'profile', path: '/profile', icon: User, label: 'Profile' },
];

export const NavBar: React.FC<NavBarProps> = ({ user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);

  const currentPath = location.pathname;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNav = (path: string) => {
    navigate(path);
    setIsOpen(false);
  };

  const displayName = user ? getDisplayName(user) : '';
  const initials = displayName ? displayName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??';

  return (
    <div className="relative" ref={menuRef}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border transition-all duration-200 ${
          isOpen 
            ? 'bg-cyan-900/30 border-cyan-700/50 text-cyan-400' 
            : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
        }`}
      >
        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-[8px] font-bold text-white">
          {initials}
        </div>
        <div className={`transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}>
          {isOpen ? <X className="w-3.5 h-3.5" /> : <Menu className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Dropdown */}
      <div className={`absolute right-0 mt-2 w-48 bg-slate-900/95 backdrop-blur-sm border border-slate-800 rounded-lg shadow-2xl overflow-hidden z-50 transition-all duration-200 origin-top-right ${
        isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
      }`}>
        {/* User header */}
        {user && (
          <div className="px-3 py-2.5 border-b border-slate-800/80 bg-slate-900/50">
            <p className="text-xs font-medium text-slate-200 truncate">{displayName}</p>
            <p className="text-[10px] text-slate-500 truncate">{user.userDetails}</p>
          </div>
        )}

        {/* Nav items */}
        <div className="py-1">
          {navItems.map((item) => {
            const isActive = currentPath === item.path;
            const Icon = item.icon;
            
            return (
              <button
                key={item.id}
                onClick={() => handleNav(item.path)}
                className={`w-full px-3 py-2 flex items-center gap-2.5 text-xs transition-all duration-150 group ${
                  isActive 
                    ? 'bg-cyan-900/30 text-cyan-400' 
                    : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-200'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 transition-transform duration-150 ${isActive ? '' : 'group-hover:scale-110'}`} />
                <span className="flex-1 text-left font-medium">{item.label}</span>
                <ChevronRight className={`w-3 h-3 transition-all duration-150 ${
                  isActive ? 'opacity-100 text-cyan-500' : 'opacity-0 group-hover:opacity-50 -translate-x-1 group-hover:translate-x-0'
                }`} />
              </button>
            );
          })}
        </div>

        {/* Logout */}
        <div className="border-t border-slate-800/80 py-1">
          <button
            onClick={() => logout('/')}
            className="w-full px-3 py-2 flex items-center gap-2.5 text-xs text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
};
