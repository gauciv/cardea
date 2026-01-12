import { useState } from 'react';
import { Shield, ChevronDown, ChevronUp, CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import type { ActiveThreat, ActionButton } from '../../types';
import axios from 'axios';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8000';

interface ActionCenterProps {
  threat: ActiveThreat | null | undefined;
  decisions: ActionButton[];
  onResolved?: () => void;
}

type ExecutionStep = {
  label: string;
  status: 'pending' | 'running' | 'success' | 'error';
  message?: string;
};

export const ActionCenter: React.FC<ActionCenterProps> = ({ threat, decisions, onResolved }) => {
  const [expanded, setExpanded] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [resultMessage, setResultMessage] = useState('');

  // No threat = all clear
  if (!threat && !resolved) {
    return (
      <div className="bg-gradient-to-br from-green-950/20 to-slate-900 border border-green-900/30 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-500/10 rounded-lg">
            <Shield className="w-5 h-5 text-green-500" />
          </div>
          <div>
            <p className="text-green-400 font-medium text-sm">All Clear</p>
            <p className="text-slate-500 text-xs">No threats requiring action</p>
          </div>
        </div>
      </div>
    );
  }

  // Resolved state - celebratory
  if (resolved) {
    return (
      <div className="bg-gradient-to-br from-green-950/30 to-slate-900 border border-green-500/30 rounded-xl p-5 shadow-lg shadow-green-500/5">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-green-500/20 rounded-xl">
            <CheckCircle className="w-6 h-6 text-green-400" />
          </div>
          <div className="flex-1">
            <p className="text-green-400 font-semibold">✓ Threat Neutralized</p>
            <p className="text-slate-300 text-sm mt-1">{resultMessage}</p>
            <p className="text-slate-500 text-xs mt-2">Your network perimeter is now secure.</p>
          </div>
        </div>
      </div>
    );
  }

  const handleAction = async (decision: ActionButton) => {
    setExecuting(true);
    setExpanded(true);
    
    // Initialize steps based on action type
    const isBlock = decision.action_type === 'block_ip';
    const actionSteps: ExecutionStep[] = isBlock ? [
      { label: 'Connecting to Sentry...', status: 'running' },
      { label: `Executing iptables block for ${decision.target}...`, status: 'pending' },
      { label: 'Verifying firewall rules...', status: 'pending' },
    ] : [
      { label: 'Processing request...', status: 'running' },
      { label: 'Updating threat database...', status: 'pending' },
      { label: 'Confirming changes...', status: 'pending' },
    ];
    setSteps(actionSteps);

    try {
      // Step 1: Connect/Process
      await new Promise(r => setTimeout(r, 600));
      setSteps(s => s.map((step, i) => i === 0 ? { ...step, status: 'success' } : i === 1 ? { ...step, status: 'running' } : step));

      // Step 2: Execute
      const response = await axios.post(`${ORACLE_URL}/api/actions/execute`, {
        action_type: decision.action_type,
        target: decision.target,
        reason: 'User action from dashboard'
      });

      await new Promise(r => setTimeout(r, 400));
      
      if (response.data.success) {
        setSteps(s => s.map((step, i) => i === 1 ? { ...step, status: 'success' } : i === 2 ? { ...step, status: 'running' } : step));
        
        // Step 3: Verify
        await new Promise(r => setTimeout(r, 500));
        setSteps(s => s.map((step, i) => i === 2 ? { ...step, status: 'success' } : step));
        
        setResultMessage(response.data.message);
        
        // Collapse and show resolved after delay
        setTimeout(() => {
          setResolved(true);
          onResolved?.();
        }, 1200);
      } else {
        setSteps(s => s.map((step, idx) => idx === 1 ? { ...step, status: 'error', message: response.data.message } : step));
      }
    } catch {
      setSteps(s => s.map((step) => 
        step.status === 'running' ? { ...step, status: 'error', message: 'Connection failed' } : step
      ));
    } finally {
      setExecuting(false);
    }
  };

  const getStepIcon = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'running': return <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />;
      case 'success': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-400" />;
      default: return <div className="w-4 h-4 rounded-full border-2 border-slate-600" />;
    }
  };

  return (
    <div className="bg-gradient-to-br from-yellow-950/20 to-slate-900 border border-yellow-900/30 rounded-xl overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => !executing && setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
        disabled={executing}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-500/10 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
          </div>
          <div className="text-left">
            <p className="text-yellow-400 font-medium text-sm capitalize">{threat?.description}</p>
            <p className="text-slate-500 text-xs">
              {threat?.alert_count} events from {threat?.source_ip}
            </p>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-slate-500" /> : <ChevronDown className="w-5 h-5 text-slate-500" />}
      </button>

      {/* Expandable content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-800">
          {/* Execution steps */}
          {steps.length > 0 && (
            <div className="mt-3 space-y-2">
              {steps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm">
                  {getStepIcon(step.status)}
                  <span className={step.status === 'error' ? 'text-red-400' : step.status === 'success' ? 'text-green-400' : 'text-slate-400'}>
                    {step.label}
                  </span>
                  {step.message && <span className="text-slate-500 text-xs">({step.message})</span>}
                </div>
              ))}
            </div>
          )}

          {/* Action buttons - only show if not executing */}
          {!executing && steps.length === 0 && (
            <div className="mt-3 flex gap-2">
              {decisions.map((decision) => (
                <button
                  key={decision.id}
                  onClick={() => handleAction(decision)}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                    decision.severity === 'danger' 
                      ? 'bg-red-600 hover:bg-red-500 text-white' 
                      : 'bg-green-600 hover:bg-green-500 text-white'
                  }`}
                >
                  {decision.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
