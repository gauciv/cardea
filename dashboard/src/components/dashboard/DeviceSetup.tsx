import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Server, Plus, Shield, Wifi, ArrowRight, Copy, Check } from 'lucide-react';

export const DeviceSetup: React.FC = () => {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const installCmd = 'curl -fsSL https://get.cardea.io | sudo bash';

  const handleCopy = () => {
    navigator.clipboard.writeText(installCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="bg-gradient-to-br from-slate-900/90 to-slate-950 border border-slate-800 rounded-2xl p-8 shadow-xl">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 flex items-center justify-center mx-auto mb-6 border border-cyan-500/20">
          <Server className="w-8 h-8 text-cyan-500" />
        </div>

        {/* Title */}
        <h2 className="text-xl font-semibold text-white text-center mb-2">
          Set Up Your First Sentry
        </h2>
        <p className="text-sm text-slate-400 text-center mb-8">
          Deploy a Sentry device on your network to start monitoring for threats
        </p>

        {/* Features */}
        <div className="space-y-3 mb-8">
          {[
            { icon: Shield, text: 'Real-time threat detection with AI' },
            { icon: Wifi, text: 'Monitor all network traffic' },
            { icon: Server, text: 'Edge processing, cloud intelligence' },
          ].map(({ icon: Icon, text }, i) => (
            <div key={i} className="flex items-center gap-3 text-sm text-slate-300">
              <div className="w-8 h-8 rounded-lg bg-slate-800/80 flex items-center justify-center">
                <Icon className="w-4 h-4 text-cyan-500" />
              </div>
              {text}
            </div>
          ))}
        </div>

        {/* Install command */}
        <div className="mb-6">
          <label className="text-[10px] uppercase tracking-wider text-slate-500 mb-2 block">
            Quick Install
          </label>
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg p-3">
            <code className="flex-1 text-xs text-cyan-400 font-mono truncate">{installCmd}</code>
            <button
              onClick={handleCopy}
              className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/devices')}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Device
          </button>
          <button
            onClick={() => window.open('https://docs.cardea.io/setup', '_blank')}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors"
          >
            Docs
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
