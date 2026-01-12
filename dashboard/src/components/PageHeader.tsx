import { Eye, BarChart3 } from 'lucide-react';

interface PageHeaderProps {
  title?: string;
  subtitle?: string;
  showViewToggle?: boolean;
  viewMode?: 'simple' | 'detailed';
  onViewModeChange?: () => void;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ 
  title,
  subtitle,
  showViewToggle, 
  viewMode, 
  onViewModeChange,
  actions
}) => {
  return (
    <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-30 px-6 py-3">
      <div className="flex justify-between items-center">
        <div>
          {title && <h1 className="text-lg font-semibold text-white">{title}</h1>}
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
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
          {actions}
        </div>
      </div>
    </header>
  );
};
