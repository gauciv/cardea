import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, RefreshCw, Eye, BarChart3 } from 'lucide-react';
import { UserMenu } from '../UserMenu';
import type { UserInfo } from '../../lib/auth';

interface HeaderProps {
  user: UserInfo | null;
  hasDevices: boolean | null;
  isConnected: boolean;
  viewMode: 'simple' | 'detailed';
  onViewModeChange: () => void;
  criticalCount: number;
  highCount: number;
}

export const Header: React.FC<HeaderProps> = ({ 
  user, 
  hasDevices, 
  isConnected, 
  viewMode, 
  onViewModeChange,
  criticalCount,
  highCount
}) => (
  <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40 px-6 py-3">
    <div className="max-w-6xl mx-auto flex justify-between items-center">
      <Link to="/dashboard" className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-cyan-500" />
        <span className="font-bold text-sm tracking-tight">CARDEA</span>
      </Link>

      <div className="flex items-center gap-4">
        {hasDevices && (
          <button 
            onClick={onViewModeChange}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-medium transition-all ${
              viewMode === "detailed" 
                ? "bg-cyan-900/40 text-cyan-400" 
                : "bg-slate-800/50 text-slate-500 hover:text-slate-300"
            }`}
          >
            {viewMode === "detailed" 
              ? <><BarChart3 className="w-3 h-3" />Technical</> 
              : <><Eye className="w-3 h-3" />Simple</>
            }
          </button>
        )}

        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          {hasDevices && (criticalCount > 0 || highCount > 0) && (
            <span className="text-red-500 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />{criticalCount + highCount}
            </span>
          )}
          {hasDevices && (
            <span className="flex items-center gap-1">
              {isConnected 
                ? <><div className="w-1.5 h-1.5 rounded-full bg-green-500" />Online</> 
                : <><RefreshCw className="w-3 h-3 animate-spin" />Connecting</>
              }
            </span>
          )}
        </div>

        {user && <UserMenu user={user} />}
      </div>
    </div>
  </header>
);
