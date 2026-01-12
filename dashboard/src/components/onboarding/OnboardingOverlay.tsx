import { Sparkles, CheckCircle2 } from 'lucide-react';

interface OnboardingOverlayProps {
  step: number;
  onNext: () => void;
  onSkip: () => void;
}

export const OnboardingOverlay: React.FC<OnboardingOverlayProps> = ({ step, onNext, onSkip }) => {
  if (step === 2) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-sm text-center animate-in zoom-in-95">
          <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-6 h-6 text-cyan-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">AI-Powered Protection</h3>
          <p className="text-sm text-slate-400 mb-4">
            Once connected, Cardea's AI will analyze your network traffic in real-time and provide actionable insights.
          </p>
          <button 
            onClick={onNext} 
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-2 rounded-lg text-sm font-medium"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (step === 3) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-sm text-center animate-in zoom-in-95">
          <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-6 h-6 text-green-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">You're All Set!</h3>
          <p className="text-sm text-slate-400 mb-4">
            Click "Connect Device" to add your Sentry and start protecting your network.
          </p>
          <button 
            onClick={onSkip} 
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-2 rounded-lg text-sm font-medium"
          >
            Get Started
          </button>
        </div>
      </div>
    );
  }

  return null;
};
