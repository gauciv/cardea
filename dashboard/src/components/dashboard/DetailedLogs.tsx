import { useState } from 'react';
import { Terminal, ChevronDown, ChevronRight, Clock, AlertTriangle, Shield, Network } from 'lucide-react';
import type { Alert } from '../../types';

interface DetailedLogsProps {
  alerts: Alert[];
  isLoading?: boolean;
}

const severityColors = {
  critical: 'text-red-400 bg-red-500/10',
  high: 'text-orange-400 bg-orange-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  low: 'text-cyan-400 bg-cyan-500/10'
};

const sourceIcons: Record<string, React.ReactNode> = {
  suricata: <Shield className="w-3 h-3" />,
  zeek: <Network className="w-3 h-3" />,
  kitnet: <AlertTriangle className="w-3 h-3" />
};

export const DetailedLogs: React.FC<DetailedLogsProps> = ({ alerts, isLoading }) => {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high'>('all');

  const filtered = alerts.filter(a => 
    filter === 'all' || a.severity === filter || (filter === 'high' && a.severity === 'critical')
  );

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatRawData = (raw: Record<string, unknown> | undefined) => {
    if (!raw) return null;
    return JSON.stringify(raw, null, 2);
  };

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Detailed Logs</h3>
        </div>
        <div className="animate-pulse space-y-2">
          {[1,2,3].map(i => <div key={i} className="h-10 bg-slate-800/50 rounded" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Detailed Logs</h3>
          <span className="text-[10px] text-slate-500 ml-2">{filtered.length} entries</span>
        </div>
        <div className="flex gap-1">
          {(['all', 'high', 'critical'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                filter === f ? 'bg-cyan-900/50 text-cyan-400' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1 max-h-80 overflow-y-auto font-mono text-xs">
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No alerts to display</p>
          </div>
        ) : (
          filtered.map(alert => (
            <div key={alert.id} className="group">
              <button
                onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
                className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800/30 hover:bg-slate-800/50 rounded transition-colors text-left"
              >
                {expandedId === alert.id ? (
                  <ChevronDown className="w-3 h-3 text-slate-500 flex-shrink-0" />
                ) : (
                  <ChevronRight className="w-3 h-3 text-slate-500 flex-shrink-0" />
                )}
                
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${severityColors[alert.severity]}`}>
                  {alert.severity.toUpperCase()}
                </span>
                
                <span className="text-slate-500 flex items-center gap-1 flex-shrink-0">
                  {sourceIcons[alert.source] || <AlertTriangle className="w-3 h-3" />}
                  {alert.source}
                </span>
                
                <span className="text-slate-300 truncate flex-1">{alert.title}</span>
                
                <span className="text-slate-600 flex items-center gap-1 flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  {formatTime(alert.timestamp)}
                </span>
              </button>
              
              {expandedId === alert.id && (
                <div className="ml-5 mt-1 mb-2 p-3 bg-slate-900/80 rounded border border-slate-800/50 space-y-3">
                  <div>
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider">Description</span>
                    <p className="text-slate-300 mt-1">{alert.description}</p>
                  </div>
                  
                  {alert.threat_score !== undefined && (
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase tracking-wider">Threat Score</span>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              alert.threat_score >= 0.7 ? 'bg-red-500' : 
                              alert.threat_score >= 0.4 ? 'bg-orange-500' : 'bg-cyan-500'
                            }`}
                            style={{ width: `${alert.threat_score * 100}%` }}
                          />
                        </div>
                        <span className="text-slate-400">{(alert.threat_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                  
                  {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase tracking-wider">Raw Data</span>
                      <pre className="mt-1 p-2 bg-slate-950 rounded text-[10px] text-slate-400 overflow-x-auto max-h-40">
                        {formatRawData(alert.raw_data)}
                      </pre>
                    </div>
                  )}
                  
                  <div className="flex gap-4 text-[10px] text-slate-500 pt-2 border-t border-slate-800/50">
                    <span>ID: {alert.id}</span>
                    <span>Type: {alert.alert_type}</span>
                    <span>Full timestamp: {new Date(alert.timestamp).toISOString()}</span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
