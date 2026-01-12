import { useState } from 'react';
import { Shield, Ban, Eye, CheckCircle, Loader2, AlertTriangle, X } from 'lucide-react';
import type { Alert } from '../../types';

interface ActionableAlertProps {
  alert: Alert;
  onAction?: (alertId: number, action: string, target?: string) => Promise<boolean>;
}

// Extract IP from alert
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

export const ActionableAlert: React.FC<ActionableAlertProps> = ({ alert, onAction }) => {
  const [actionState, setActionState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [lastAction, setLastAction] = useState<string | null>(null);
  
  const ip = extractIP(alert);
  const isHighSeverity = alert.severity === 'critical' || alert.severity === 'high';

  const handleAction = async (action: string) => {
    if (!onAction || actionState === 'loading') return;
    
    setActionState('loading');
    setLastAction(action);
    
    try {
      const success = await onAction(alert.id, action, ip || undefined);
      setActionState(success ? 'success' : 'error');
      
      // Reset after 3 seconds
      setTimeout(() => {
        setActionState('idle');
        setLastAction(null);
      }, 3000);
    } catch {
      setActionState('error');
      setTimeout(() => setActionState('idle'), 3000);
    }
  };

  const severityColors = {
    critical: 'border-red-500/30 bg-red-500/5',
    high: 'border-orange-500/30 bg-orange-500/5',
    medium: 'border-yellow-500/30 bg-yellow-500/5',
    low: 'border-cyan-500/30 bg-cyan-500/5'
  };

  return (
    <div className={`border rounded-xl p-4 ${severityColors[alert.severity]} transition-all`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {isHighSeverity && <AlertTriangle className="w-4 h-4 text-red-500" />}
            <span className={`text-xs font-medium uppercase ${
              alert.severity === 'critical' ? 'text-red-400' :
              alert.severity === 'high' ? 'text-orange-400' :
              alert.severity === 'medium' ? 'text-yellow-400' : 'text-cyan-400'
            }`}>
              {alert.severity}
            </span>
          </div>
          <h4 className="text-sm font-medium text-white">{alert.title}</h4>
          <p className="text-xs text-slate-500 mt-1 line-clamp-2">{alert.description}</p>
        </div>
        
        {ip && (
          <div className="text-right flex-shrink-0">
            <p className="text-[10px] text-slate-500 uppercase">Source IP</p>
            <p className="text-xs font-mono text-slate-300">{ip}</p>
          </div>
        )}
      </div>
      
      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-700/50">
        {/* Block IP button */}
        {ip && (
          <button
            onClick={() => handleAction('block_ip')}
            disabled={actionState === 'loading'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              actionState === 'success' && lastAction === 'block_ip'
                ? 'bg-green-500/20 text-green-400'
                : actionState === 'loading' && lastAction === 'block_ip'
                ? 'bg-slate-700 text-slate-400'
                : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
            }`}
          >
            {actionState === 'loading' && lastAction === 'block_ip' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : actionState === 'success' && lastAction === 'block_ip' ? (
              <CheckCircle className="w-3 h-3" />
            ) : (
              <Ban className="w-3 h-3" />
            )}
            {actionState === 'success' && lastAction === 'block_ip' ? 'Blocked' : 'Block IP'}
          </button>
        )}
        
        {/* Monitor button */}
        <button
          onClick={() => handleAction('monitor')}
          disabled={actionState === 'loading'}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            actionState === 'success' && lastAction === 'monitor'
              ? 'bg-green-500/20 text-green-400'
              : actionState === 'loading' && lastAction === 'monitor'
              ? 'bg-slate-700 text-slate-400'
              : 'bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20'
          }`}
        >
          {actionState === 'loading' && lastAction === 'monitor' ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : actionState === 'success' && lastAction === 'monitor' ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <Eye className="w-3 h-3" />
          )}
          {actionState === 'success' && lastAction === 'monitor' ? 'Monitoring' : 'Monitor'}
        </button>
        
        {/* Dismiss button */}
        <button
          onClick={() => handleAction('dismiss')}
          disabled={actionState === 'loading'}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            actionState === 'success' && lastAction === 'dismiss'
              ? 'bg-green-500/20 text-green-400'
              : actionState === 'loading' && lastAction === 'dismiss'
              ? 'bg-slate-700 text-slate-400'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
          }`}
        >
          {actionState === 'loading' && lastAction === 'dismiss' ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : actionState === 'success' && lastAction === 'dismiss' ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <X className="w-3 h-3" />
          )}
          {actionState === 'success' && lastAction === 'dismiss' ? 'Dismissed' : 'Dismiss'}
        </button>
        
        {/* Spacer */}
        <div className="flex-1" />
        
        {/* Timestamp */}
        <span className="text-[10px] text-slate-600">
          {new Date(alert.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};

// Panel showing actionable alerts
interface ActionableAlertsPanelProps {
  alerts: Alert[];
  isLoading?: boolean;
}

export const ActionableAlertsPanel: React.FC<ActionableAlertsPanelProps> = ({ alerts, isLoading }) => {
  const [actionLog, setActionLog] = useState<Array<{ time: string; action: string; target?: string }>>([]);
  
  // Filter to high-severity alerts only
  const actionableAlerts = alerts.filter(a => a.severity === 'critical' || a.severity === 'high');

  const handleAction = async (alertId: number, action: string, target?: string): Promise<boolean> => {
    // Simulate API call
    await new Promise(r => setTimeout(r, 1000));
    
    // Log the action
    setActionLog(prev => [{
      time: new Date().toLocaleTimeString(),
      action,
      target
    }, ...prev.slice(0, 4)]);
    
    // In production, this would call the Oracle API
    console.log(`Action: ${action} on alert ${alertId}${target ? ` targeting ${target}` : ''}`);
    
    return true;
  };

  // Empty state
  if (!isLoading && actionableAlerts.length === 0) {
    return (
      <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-500" />
            <h3 className="text-sm font-medium text-white">Action Center</h3>
          </div>
          <span className="text-[10px] text-green-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            No Action Needed
          </span>
        </div>
        
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mb-3">
            <CheckCircle className="w-6 h-6 text-green-500" />
          </div>
          <p className="text-sm text-slate-300 font-medium">All Clear</p>
          <p className="text-xs text-slate-500 mt-1">No critical threats requiring your attention</p>
          <p className="text-[10px] text-slate-600 mt-3">High-priority alerts will appear here for quick action</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Action Center</h3>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400">
          {actionableAlerts.length} requiring action
        </span>
      </div>
      
      {/* Actionable alerts */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {actionableAlerts.slice(0, 5).map(alert => (
          <ActionableAlert 
            key={alert.id} 
            alert={alert} 
            onAction={handleAction}
          />
        ))}
      </div>
      
      {/* Action log */}
      {actionLog.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-800">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Recent Actions</p>
          <div className="space-y-1">
            {actionLog.map((log, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <CheckCircle className="w-3 h-3 text-green-500" />
                <span className="text-slate-400">
                  {log.action === 'block_ip' ? 'Blocked' : log.action === 'monitor' ? 'Monitoring' : 'Dismissed'}
                  {log.target && <span className="font-mono text-slate-300"> {log.target}</span>}
                </span>
                <span className="text-slate-600 ml-auto">{log.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
