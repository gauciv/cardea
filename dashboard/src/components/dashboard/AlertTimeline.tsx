import { useState, useEffect, useRef } from 'react';
import { Clock, AlertTriangle, Shield, ChevronDown, ChevronUp, Zap } from 'lucide-react';
import type { Alert } from '../../types';

interface AlertTimelineProps {
  alerts: Alert[];
  isLoading?: boolean;
}

interface TimelineAlert extends Alert {
  isNew?: boolean;
}

// Format relative time
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const alertTime = new Date(timestamp);
  const diffMs = now.getTime() - alertTime.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return alertTime.toLocaleDateString();
}

// Get severity color
function getSeverityColor(severity: string): { bg: string; text: string; border: string; dot: string } {
  switch (severity) {
    case 'critical':
      return { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' };
    case 'high':
      return { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30', dot: 'bg-orange-500' };
    case 'medium':
      return { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', dot: 'bg-yellow-500' };
    default:
      return { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30', dot: 'bg-cyan-500' };
  }
}

// Get alert type icon description
function getAlertTypeLabel(alertType: string): string {
  const types: Record<string, string> = {
    'network_anomaly': 'Network Anomaly',
    'intrusion_detection': 'Intrusion Detected',
    'malware_detection': 'Malware Alert',
    'suspicious_behavior': 'Suspicious Activity',
    'data_exfiltration': 'Data Exfiltration',
    'unauthorized_access': 'Unauthorized Access'
  };
  return types[alertType] || alertType.replace(/_/g, ' ');
}

export const AlertTimeline: React.FC<AlertTimelineProps> = ({ alerts, isLoading }) => {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [timelineAlerts, setTimelineAlerts] = useState<TimelineAlert[]>([]);
  const [newAlertIds, setNewAlertIds] = useState<Set<number>>(new Set());
  const prevAlertsRef = useRef<Alert[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  // Detect new alerts and animate them
  useEffect(() => {
    const prevIds = new Set(prevAlertsRef.current.map(a => a.id));
    
    // Find truly new alerts
    const newIds = new Set<number>();
    alerts.forEach(alert => {
      if (!prevIds.has(alert.id)) {
        newIds.add(alert.id);
      }
    });

    if (newIds.size > 0) {
      setNewAlertIds(prev => new Set([...prev, ...newIds]));
      
      // Clear "new" status after animation
      setTimeout(() => {
        setNewAlertIds(prev => {
          const updated = new Set(prev);
          newIds.forEach(id => updated.delete(id));
          return updated;
        });
      }, 3000);
    }

    setTimelineAlerts(alerts.map(a => ({ ...a, isNew: newIds.has(a.id) })));
    prevAlertsRef.current = alerts;
  }, [alerts]);

  // Empty state
  if (!isLoading && alerts.length === 0) {
    return (
      <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-500" />
            <h3 className="text-sm font-medium text-white">Alert Timeline</h3>
          </div>
          <span className="text-[10px] text-slate-500">Last 24 hours</span>
        </div>
        
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mb-3">
            <Shield className="w-6 h-6 text-green-500" />
          </div>
          <p className="text-sm text-slate-300 font-medium">All Quiet</p>
          <p className="text-xs text-slate-500 mt-1">No security events to report</p>
          <p className="text-[10px] text-slate-600 mt-3">New alerts will appear here in real-time</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Alert Timeline</h3>
        </div>
        <span className="text-[10px] text-slate-500">
          {alerts.length} {alerts.length === 1 ? 'event' : 'events'}
        </span>
      </div>
      
      {/* Timeline container */}
      <div className="relative max-h-96 overflow-y-auto pr-2" ref={containerRef}>
        {/* Timeline line */}
        <div className="absolute left-[7px] top-0 bottom-0 w-0.5 bg-slate-800" />
        
        {/* Alert items */}
        <div className="space-y-3">
          {timelineAlerts.map((alert, index) => {
            const colors = getSeverityColor(alert.severity);
            const isExpanded = expandedId === alert.id;
            const isNew = newAlertIds.has(alert.id);
            
            return (
              <div
                key={alert.id}
                className={`relative pl-6 transition-all duration-500 ${
                  isNew ? 'animate-slide-in' : ''
                }`}
                style={{
                  animationDelay: `${index * 50}ms`
                }}
              >
                {/* Timeline dot */}
                <div className={`absolute left-0 top-2 w-4 h-4 rounded-full border-2 border-slate-900 ${colors.dot} ${
                  isNew ? 'animate-pulse' : ''
                }`}>
                  {isNew && (
                    <div className={`absolute inset-0 rounded-full ${colors.dot} animate-ping`} />
                  )}
                </div>
                
                {/* Alert card */}
                <div 
                  className={`${colors.bg} border ${colors.border} rounded-lg p-3 cursor-pointer transition-all hover:scale-[1.01] ${
                    isNew ? 'ring-2 ring-offset-2 ring-offset-slate-950 ring-cyan-500/50' : ''
                  }`}
                  onClick={() => setExpandedId(isExpanded ? null : alert.id)}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {(alert.severity === 'critical' || alert.severity === 'high') && (
                          <AlertTriangle className={`w-3 h-3 ${colors.text} flex-shrink-0`} />
                        )}
                        <span className={`text-[10px] font-medium uppercase tracking-wider ${colors.text}`}>
                          {alert.severity}
                        </span>
                        <span className="text-[10px] text-slate-600">•</span>
                        <span className="text-[10px] text-slate-500">
                          {getAlertTypeLabel(alert.alert_type)}
                        </span>
                      </div>
                      <p className="text-sm text-white font-medium truncate">{alert.title}</p>
                    </div>
                    
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[10px] text-slate-500">{formatRelativeTime(alert.timestamp)}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-500" />
                      )}
                    </div>
                  </div>
                  
                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2 animate-fade-in">
                      <p className="text-xs text-slate-400">{alert.description}</p>
                      
                      {alert.threat_score !== undefined && (
                        <div className="flex items-center gap-2">
                          <Zap className="w-3 h-3 text-yellow-500" />
                          <span className="text-[10px] text-slate-500">
                            Threat Score: <span className="text-white font-mono">{(alert.threat_score * 100).toFixed(0)}%</span>
                          </span>
                        </div>
                      )}
                      
                      <div className="flex items-center gap-2 text-[10px] text-slate-600">
                        <span>Source: {alert.source}</span>
                        <span>•</span>
                        <span>{new Date(alert.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* CSS for animations */}
      <style>{`
        @keyframes slide-in {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        .animate-slide-in {
          animation: slide-in 0.5s ease-out forwards;
        }
        
        .animate-fade-in {
          animation: fade-in 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
};
