import { Shield, WifiOff } from 'lucide-react';
import type { Alert } from '../../types';
import { severityConfig } from '../../config';

interface AlertTableProps {
  alerts: Alert[];
  isConnected: boolean;
}

export const AlertTable: React.FC<AlertTableProps> = ({ alerts, isConnected }) => {
  if (!isConnected) {
    return (
      <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-8 text-center">
        <WifiOff className="w-8 h-8 text-slate-700 mx-auto mb-3" />
        <p className="text-sm text-slate-500">Waiting for connection...</p>
      </div>
    );
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-8 text-center">
        <Shield className="w-8 h-8 text-slate-700 mx-auto mb-3" />
        <p className="text-sm text-slate-500">No alerts detected</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/30 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">Recent Events</span>
        <span className="text-[10px] text-slate-600">Auto-refresh 5s</span>
      </div>
      <div className="divide-y divide-slate-800/50">
        {alerts.slice(0, 10).map((alert) => {
          const cfg = severityConfig[alert.severity as keyof typeof severityConfig] || severityConfig.low;
          return (
            <div key={alert.id} className="px-4 py-3 hover:bg-slate-800/30 transition-colors flex items-center gap-4">
              <span className="text-[10px] text-slate-600 font-mono w-16">
                {new Date(alert.timestamp).toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit" })}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-300 truncate">
                  {(alert.alert_type || "Unknown").replaceAll("_", " ")}
                </p>
                <p className="text-[10px] text-slate-500 truncate">{alert.description}</p>
              </div>
              <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${cfg.bg} ${cfg.color}`}>
                {alert.severity.toUpperCase()}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
