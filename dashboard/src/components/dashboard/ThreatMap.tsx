import { useEffect, useState } from 'react';
import { Globe, Shield } from 'lucide-react';
import type { Alert } from '../../types';

interface ThreatMapProps {
  alerts: Alert[];
  isLoading?: boolean;
}

function extractIP(alert: Alert): string | null {
  const raw = alert.raw_data as Record<string, unknown> | undefined;
  if (!raw) return null;
  const network = raw.network as Record<string, unknown> | undefined;
  if (network?.src_ip && typeof network.src_ip === 'string') return network.src_ip;
  if (raw.src_ip && typeof raw.src_ip === 'string') return raw.src_ip;
  if (raw.dest_ip && typeof raw.dest_ip === 'string') return raw.dest_ip;
  const ipMatch = alert.title.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/);
  return ipMatch ? ipMatch[1] : null;
}

const severityColor = (s: string) => 
  s === 'critical' ? '#ef4444' : s === 'high' ? '#f97316' : s === 'medium' ? '#eab308' : '#22d3ee';

export const ThreatMap: React.FC<ThreatMapProps> = ({ alerts, isLoading }) => {
  const [nodes, setNodes] = useState<{ip: string; severity: string; count: number; angle: number}[]>([]);
  
  useEffect(() => {
    const ipMap = new Map<string, {severity: string; count: number}>();
    alerts.forEach(alert => {
      const ip = extractIP(alert);
      if (ip) {
        const existing = ipMap.get(ip);
        if (existing) {
          existing.count++;
          if (['critical','high'].includes(alert.severity)) existing.severity = alert.severity;
        } else {
          ipMap.set(ip, { severity: alert.severity, count: 1 });
        }
      }
    });
    const arr = Array.from(ipMap.entries()).slice(0, 8);
    setNodes(arr.map(([ip, data], i) => ({ 
      ip, 
      ...data, 
      angle: (i / arr.length) * 2 * Math.PI - Math.PI/2 
    })));
  }, [alerts]);

  const hasAlerts = alerts.length > 0;
  const highCount = alerts.filter(a => ['critical', 'high'].includes(a.severity)).length;

  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Network Activity Map</h3>
        </div>
        <span className={`text-[10px] flex items-center gap-1 ${hasAlerts ? (highCount > 0 ? 'text-orange-400' : 'text-yellow-400') : 'text-green-400'}`}>
          <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${hasAlerts ? (highCount > 0 ? 'bg-orange-500' : 'bg-yellow-500') : 'bg-green-500'}`} />
          {hasAlerts ? `${alerts.length} events from ${nodes.length} sources` : 'All Clear'}
        </span>
      </div>
      
      <div className="relative aspect-[2/1] bg-slate-950/50 rounded-lg overflow-hidden border border-slate-800/50 flex items-center justify-center">
        {/* Network topology visualization */}
        <svg viewBox="0 0 400 200" className="w-full h-full">
          {/* Grid background */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#334155" strokeWidth="0.3" opacity="0.3"/>
            </pattern>
          </defs>
          <rect width="400" height="200" fill="url(#grid)" />
          
          {/* Center hub (your network) */}
          <circle cx="200" cy="100" r="25" fill="#0f172a" stroke="#22d3ee" strokeWidth="2" />
          <circle cx="200" cy="100" r="20" fill="#164e63" opacity="0.5">
            <animate attributeName="r" values="18;22;18" dur="2s" repeatCount="indefinite" />
          </circle>
          <text x="200" y="104" textAnchor="middle" fill="#22d3ee" fontSize="10" fontFamily="monospace">SENTRY</text>
          
          {/* Connection lines and nodes */}
          {nodes.map((node, i) => {
            const radius = 70;
            const x = 200 + Math.cos(node.angle) * radius;
            const y = 100 + Math.sin(node.angle) * radius;
            const color = severityColor(node.severity);
            
            return (
              <g key={node.ip}>
                {/* Connection line */}
                <line x1="200" y1="100" x2={x} y2={y} stroke={color} strokeWidth="1.5" opacity="0.6" strokeDasharray="4,2">
                  <animate attributeName="stroke-dashoffset" from="6" to="0" dur="1s" repeatCount="indefinite" />
                </line>
                
                {/* Node */}
                <circle cx={x} cy={y} r="8" fill="#0f172a" stroke={color} strokeWidth="2">
                  <animate attributeName="r" values="7;9;7" dur="2s" repeatCount="indefinite" begin={`${i * 0.2}s`} />
                </circle>
                
                {/* Alert count badge */}
                {node.count > 1 && (
                  <g>
                    <circle cx={x + 8} cy={y - 8} r="6" fill={color} />
                    <text x={x + 8} y={y - 5} textAnchor="middle" fill="white" fontSize="7" fontWeight="bold">{node.count}</text>
                  </g>
                )}
                
                {/* IP label */}
                <text x={x} y={y + 18} textAnchor="middle" fill="#94a3b8" fontSize="7" fontFamily="monospace">{node.ip}</text>
              </g>
            );
          })}
          
          {/* Empty state */}
          {!hasAlerts && (
            <g>
              <circle cx="200" cy="100" r="50" fill="none" stroke="#22c55e" strokeWidth="1" opacity="0.3" strokeDasharray="4,4">
                <animate attributeName="r" values="45;55;45" dur="3s" repeatCount="indefinite" />
              </circle>
            </g>
          )}
        </svg>
        
        {/* Empty state overlay */}
        {!hasAlerts && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/40 backdrop-blur-[1px]">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-3">
                <Shield className="w-6 h-6 text-green-500" />
              </div>
              <p className="text-sm text-slate-300 font-medium">Network Quiet</p>
              <p className="text-xs text-slate-500 mt-1">No anomalies detected</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Legend */}
      {hasAlerts && (
        <div className="mt-3 flex items-center justify-between">
          <div className="flex gap-3 text-[9px] text-slate-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Your Network</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Critical</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> High</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Medium</span>
          </div>
          <span className="text-[9px] text-slate-600">Live network topology</span>
        </div>
      )}
    </div>
  );
};
