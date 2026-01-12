import { ChevronRight } from 'lucide-react';

interface OnboardingTooltipProps {
  step: number;
  total: number;
  title: string;
  desc: string;
  onNext: () => void;
  onSkip: () => void;
  position?: 'top' | 'bottom';
}

export const OnboardingTooltip: React.FC<OnboardingTooltipProps> = ({ 
  step, 
  total, 
  title, 
  desc, 
  onNext, 
  onSkip, 
  position = "bottom" 
}) => (
  <div 
    className={`absolute z-50 w-72 bg-slate-900 border border-cyan-500/50 rounded-xl p-4 shadow-2xl shadow-cyan-500/10 animate-in fade-in slide-in-from-${position === "top" ? "bottom" : "top"}-2 duration-300`}
    style={{ 
      [position === "top" ? "bottom" : "top"]: "100%", 
      left: "50%", 
      transform: "translateX(-50%)", 
      marginTop: position === "top" ? 0 : 8, 
      marginBottom: position === "top" ? 8 : 0 
    }}
  >
    <div className={`absolute ${position === "top" ? "bottom-0 translate-y-1/2" : "top-0 -translate-y-1/2"} left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-${position === "top" ? "b border-r" : "t border-l"} border-cyan-500/50 rotate-45`} />
    
    <div className="flex items-center justify-between mb-2">
      <span className="text-[10px] text-cyan-400 font-medium">Step {step}/{total}</span>
      <button onClick={onSkip} className="text-[10px] text-slate-500 hover:text-slate-300">
        Skip tour
      </button>
    </div>
    
    <h4 className="text-sm font-semibold text-white mb-1">{title}</h4>
    <p className="text-xs text-slate-400 mb-3">{desc}</p>
    
    <button 
      onClick={onNext} 
      className="w-full bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium py-2 rounded-lg flex items-center justify-center gap-1 transition-colors"
    >
      {step === total ? "Got it!" : "Next"} <ChevronRight className="w-3 h-3" />
    </button>
  </div>
);
