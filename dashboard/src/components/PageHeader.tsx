import { useNavigate } from 'react-router-dom';
import { Eye, BarChart3 } from 'lucide-react';
import { NavBar } from './NavBar';
import { useAuth } from '../lib/useAuth';

interface PageHeaderProps {
  showViewToggle?: boolean;
  viewMode?: 'simple' | 'detailed';
  onViewModeChange?: () => void;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ 
  showViewToggle, 
  viewMode, 
  onViewModeChange 
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40 px-6 py-3">
      <div className="max-w-6xl mx-auto flex justify-between items-center">
        <button 
          onClick={() => navigate('/dashboard')} 
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
        >
          <img src="/cardea-logo.png" alt="Cardea" className="w-6 h-6" />
          <span className="font-bold text-sm tracking-tight text-white">CARDEA</span>
        </button>
        <div className="flex items-center gap-3">
          {showViewToggle && onViewModeChange && (
            <button 
              onClick={onViewModeChange}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all border ${
                viewMode === "detailed" 
                  ? "bg-cyan-900/30 border-cyan-700/50 text-cyan-400" 
                  : "bg-slate-800/50 border-slate-700/50 text-slate-500 hover:text-slate-300 hover:bg-slate-800"
              }`}
            >
              {viewMode === "detailed" ? <><BarChart3 className="w-3 h-3" />Detailed</> : <><Eye className="w-3 h-3" />Simple</>}
            </button>
          )}
          <NavBar user={user} />
        </div>
      </div>
    </header>
  );
};
