import { Shield, Activity, Zap } from 'lucide-react';
import type { AnalyticsResponse } from '../../types';

interface StatsGridProps {
  data: AnalyticsResponse | null;
  isConnected: boolean;
}

export const StatsGrid: React.FC<StatsGridProps> = ({ data, isConnected }) => {
  if (!isConnected || !data) return null;

  const risk = data.risk_score || 0;
  const critical = data.alerts_by_severity?.critical || 0;
  const high = data.alerts_by_severity?.high || 0;

  return (
    <div className="grid grid-cols-4 gap-3">
      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-2 h-2 rounded-full ${critical > 0 ? "bg-red-500 animate-pulse" : high > 0 ? "bg-orange-500" : "bg-green-500"}`} />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Status</span>
        </div>
        <p className={`text-sm font-semibold ${critical > 0 ? "text-red-400" : high > 0 ? "text-orange-400" : "text-green-400"}`}>
          {critical > 0 ? "Alert" : high > 0 ? "Warning" : "Clear"}
        </p>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="w-3 h-3 text-cyan-500" />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Risk</span>
        </div>
        <p className={`text-sm font-semibold ${risk >= 0.7 ? "text-red-400" : risk >= 0.4 ? "text-yellow-400" : "text-cyan-400"}`}>
          {risk >= 0.7 ? "High" : risk >= 0.4 ? "Medium" : "Low"}
        </p>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="w-3 h-3 text-purple-500" />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Events</span>
        </div>
        <p className="text-sm font-semibold text-slate-200">{data.total_alerts || 0}</p>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-3 h-3 text-green-500" />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Protection</span>
        </div>
        <p className="text-sm font-semibold text-green-400">Active</p>
      </div>
    </div>
  );
};
