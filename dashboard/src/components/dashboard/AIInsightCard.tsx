import { useState } from 'react';
import { Sparkles, CheckCircle2, Info } from 'lucide-react';
import type { AIInsight } from '../../types';

interface AIInsightCardProps {
  insight: AIInsight | null | undefined;
  isLoading: boolean;
  isOffline?: boolean;
}

export const AIInsightCard: React.FC<AIInsightCardProps> = ({ insight, isLoading, isOffline }) => {
  const [showTech, setShowTech] = useState(false);

  if (isOffline) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-slate-800 rounded-lg">
            <Sparkles className="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-slate-500">AI Analysis</h2>
            <span className="text-[10px] text-slate-600">Offline</span>
          </div>
        </div>
        <p className="text-sm text-slate-500">Connect a Sentry device to enable AI-powered threat analysis.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-900/30 rounded-lg">
            <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="h-4 w-32 bg-slate-800 rounded" />
            <div className="h-3 w-20 bg-slate-800 rounded" />
          </div>
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-slate-800 rounded w-full" />
          <div className="h-3 bg-slate-800 rounded w-4/5" />
        </div>
      </div>
    );
  }

  if (!insight) return null;

  const emoji = insight.status_emoji || "🟢";
  const gradient = emoji === "🔴" || emoji === "🚨" 
    ? "from-red-950/40 border-red-900/40" 
    : emoji === "🟠" 
    ? "from-orange-950/40 border-orange-900/40" 
    : emoji === "🟡" 
    ? "from-yellow-950/30 border-yellow-900/30" 
    : "from-green-950/30 border-green-900/30";

  return (
    <div className={`bg-gradient-to-br ${gradient} to-slate-900/80 border rounded-xl p-6`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{emoji}</span>
          <div>
            <p className="text-sm text-slate-400">{insight.greeting}</p>
            <h2 className="text-lg font-semibold text-white">{insight.headline || insight.summary}</h2>
          </div>
        </div>
        <span className="text-[10px] text-slate-600 font-mono">
          {insight.generated_at ? new Date(insight.generated_at).toLocaleTimeString([], { hour12: false }) : ""}
        </span>
      </div>

      {insight.story && (
        <p className="text-sm text-slate-300 mb-4 leading-relaxed">{insight.story}</p>
      )}

      {insight.actions_taken && insight.actions_taken.length > 0 && (
        <div className="bg-slate-900/50 rounded-lg p-3 mb-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Actions taken</p>
          <ul className="space-y-1">
            {insight.actions_taken.map((a, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-center gap-2">
                <CheckCircle2 className="w-3 h-3 text-green-500" />{a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {insight.technical_summary && (
        <button 
          onClick={() => setShowTech(!showTech)} 
          className="text-[10px] text-slate-500 hover:text-slate-400 flex items-center gap-1"
        >
          <Info className="w-3 h-3" />{showTech ? "Hide" : "Show"} technical details
        </button>
      )}

      {showTech && insight.technical_summary && (
        <p className="mt-2 text-[10px] text-slate-500 font-mono bg-slate-900/50 rounded p-2">
          {insight.technical_summary}
        </p>
      )}

      <div className="mt-4 pt-3 border-t border-slate-800/50 flex items-center justify-between">
        <span className="text-[10px] text-cyan-500 flex items-center gap-1">
          <Sparkles className="w-3 h-3" />AI Analysis
        </span>
        <span className="text-[10px] text-slate-600">
          {((insight.confidence || 0) * 100).toFixed(0)}% confidence
        </span>
      </div>
    </div>
  );
};
