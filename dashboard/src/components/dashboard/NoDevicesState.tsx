import { Link } from 'react-router-dom';
import { Server, Plus, ChevronRight } from 'lucide-react';
import { OnboardingTooltip } from '../onboarding';

interface NoDevicesStateProps {
  showOnboarding: boolean;
  onboardingStep: number;
  onNextStep: () => void;
  onSkip: () => void;
  onboardingRef?: React.RefObject<HTMLDivElement | null>;
}

export const NoDevicesState: React.FC<NoDevicesStateProps> = ({ 
  showOnboarding, 
  onboardingStep, 
  onNextStep, 
  onSkip, 
  onboardingRef 
}) => (
  <div className="max-w-lg mx-auto text-center py-12" ref={onboardingRef}>
    <div className="relative inline-block mb-6">
      <div className="w-16 h-16 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center">
        <Server className="w-8 h-8 text-slate-600" />
      </div>
      <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-slate-800 rounded-full flex items-center justify-center border-2 border-slate-950">
        <Plus className="w-3 h-3 text-slate-500" />
      </div>
    </div>

    <h2 className="text-xl font-semibold text-white mb-2">No Sentry Devices</h2>
    <p className="text-sm text-slate-500 mb-6">Connect your first Sentry device to start monitoring your network.</p>
    
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
        <span>Quick Setup</span>
        <span className="text-slate-600">~2 min</span>
      </div>
      <div className="flex justify-between">
        {[{ n: 1, t: "Power on" }, { n: 2, t: "Get code" }, { n: 3, t: "Enter here" }].map((s, i) => (
          <div key={s.n} className="flex flex-col items-center gap-1">
            <div className="w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-xs font-bold text-cyan-400">
              {s.n}
            </div>
            <span className="text-[10px] text-slate-500">{s.t}</span>
            {i < 2 && (
              <ChevronRight 
                className="w-3 h-3 text-slate-700 absolute" 
                style={{ marginLeft: "80px", marginTop: "10px" }} 
              />
            )}
          </div>
        ))}
      </div>
    </div>

    <div className="relative inline-block">
      <Link 
        to="/devices" 
        className="inline-flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-2.5 rounded-lg font-medium text-sm transition-all hover:scale-105 active:scale-95"
      >
        <Plus className="w-4 h-4" /> Connect Device
      </Link>
      {showOnboarding && onboardingStep === 1 && (
        <OnboardingTooltip 
          step={1} 
          total={3} 
          title="Start Here" 
          desc="Click to add your first Sentry device and begin monitoring." 
          onNext={onNextStep} 
          onSkip={onSkip} 
        />
      )}
    </div>
  </div>
);
