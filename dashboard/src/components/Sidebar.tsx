import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, User, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { logout, getDisplayName, type UserInfo } from '../lib/auth';

interface SidebarProps {
  user: UserInfo | null;
}

const navItems = [
  { id: 'dashboard', path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'devices', path: '/devices', icon: Server, label: 'Devices' },
  { id: 'settings', path: '/settings', icon: Settings, label: 'Settings' },
  { id: 'profile', path: '/profile', icon: User, label: 'Profile' },
];

export const Sidebar: React.FC<SidebarProps> = ({ user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname;

  const displayName = user ? getDisplayName(user) : '';
  const initials = displayName ? displayName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??';

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/40 z-40 lg:hidden transition-opacity duration-200"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 h-full bg-slate-900/95 backdrop-blur-sm border-r border-slate-800 z-50 flex flex-col transition-all duration-200 ease-out ${
        isOpen ? 'w-48' : 'w-14'
      }`}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-slate-800/50">
          <img src="/cardea-logo.png" alt="Cardea" className="w-6 h-6 flex-shrink-0" />
          <span className={`ml-2 font-bold text-sm text-white whitespace-nowrap transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
            CARDEA
          </span>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => {
            const isActive = currentPath === item.path;
            const Icon = item.icon;
            
            return (
              <button
                key={item.id}
                onClick={() => { navigate(item.path); if (window.innerWidth < 1024) setIsOpen(false); }}
                className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs font-medium transition-all duration-150 group relative ${
                  isActive 
                    ? 'bg-cyan-500/10 text-cyan-400' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 transition-transform duration-150 ${!isActive && 'group-hover:scale-110'}`} />
                <span className={`whitespace-nowrap transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
                  {item.label}
                </span>
                {/* Active indicator */}
                {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-cyan-400 rounded-r" />}
                {/* Tooltip when collapsed */}
                {!isOpen && (
                  <span className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity">
                    {item.label}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User & Logout */}
        <div className="border-t border-slate-800/50 p-2 space-y-1">
          {user && (
            <div className={`flex items-center gap-2 px-2.5 py-2 ${isOpen ? '' : 'justify-center'}`}>
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0">
                {initials}
              </div>
              <div className={`transition-opacity duration-200 overflow-hidden ${isOpen ? 'opacity-100' : 'opacity-0 w-0'}`}>
                <p className="text-[11px] font-medium text-white truncate max-w-24">{displayName}</p>
                <p className="text-[9px] text-slate-500 truncate max-w-24">{user.userDetails}</p>
              </div>
            </div>
          )}
          <button
            onClick={() => logout('/')}
            className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors ${!isOpen && 'justify-center'}`}
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            <span className={`transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'}`}>
              Sign Out
            </span>
          </button>
        </div>

        {/* Toggle Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="absolute -right-3 top-20 w-6 h-6 bg-slate-800 border border-slate-700 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors z-50"
        >
          {isOpen ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>
      </aside>
    </>
  );
};
