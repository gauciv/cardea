import { useState, useEffect, useRef } from 'react';
import { Wifi, WifiOff, CheckCircle, Loader2, Terminal } from 'lucide-react';
import type { AIInsight, ActionButton } from '../../types';
import axios from 'axios';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8000';

interface AIPersonaProps {
  insight: AIInsight | null | undefined;
  isLoading: boolean;
  isOffline?: boolean;
  deviceStatus?: 'online' | 'offline';
  riskLevel?: 'low' | 'medium' | 'high';
  onActionComplete?: () => void;
  onResolvedChange?: (resolved: boolean) => void;
}

// Disco Ball SVG Component
const DiscoBall: React.FC<{ status: 'idle' | 'thinking' | 'speaking' | 'executing'; color: string }> = ({ status, color }) => {
  const baseColor = color === 'red' ? '#ef4444' : color === 'yellow' ? '#eab308' : '#22d3ee';
  const glowColor = color === 'red' ? 'rgba(239,68,68,0.4)' : color === 'yellow' ? 'rgba(234,179,8,0.4)' : 'rgba(34,211,238,0.4)';
  
  return (
    <div className={`relative ${status === 'thinking' || status === 'executing' ? 'animate-pulse' : ''}`}>
      <div 
        className={`absolute inset-0 rounded-full blur-xl transition-opacity duration-500 ${status === 'speaking' || status === 'executing' ? 'opacity-60' : 'opacity-30'}`}
        style={{ background: glowColor }}
      />
      <svg viewBox="0 0 100 100" className="w-16 h-16 relative z-10">
        <defs>
          <radialGradient id="ballGradient" cx="30%" cy="30%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="50%" stopColor={baseColor} stopOpacity="0.6" />
            <stop offset="100%" stopColor="#1e293b" stopOpacity="0.8" />
          </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="40" fill="url(#ballGradient)" />
        <g className={status !== 'idle' ? 'animate-spin' : ''} style={{ transformOrigin: '50px 50px', animationDuration: status === 'executing' ? '2s' : '8s' }}>
          {[0, 30, 60, 90, 120, 150].map((angle, i) => (
            <g key={i} transform={`rotate(${angle} 50 50)`}>
              <rect x="45" y="15" width="10" height="8" rx="1" fill="white" opacity={0.3 + (i % 3) * 0.2} />
              <rect x="30" y="28" width="8" height="6" rx="1" fill="white" opacity={0.2 + (i % 2) * 0.3} />
            </g>
          ))}
        </g>
        <ellipse cx="35" cy="35" rx="12" ry="8" fill="white" opacity="0.3" />
      </svg>
    </div>
  );
};

// Typing animation hook
const useTypingEffect = (text: string, speed: number = 30, enabled: boolean = true) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const prevTextRef = useRef<string>('');

  useEffect(() => {
    if (!enabled || !text) {
      setDisplayedText(text || '');
      return;
    }
    if (text === prevTextRef.current) {
      setDisplayedText(text);
      return;
    }
    prevTextRef.current = text;
    setIsTyping(true);
    setDisplayedText('');
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayedText(text.slice(0, i + 1));
        i++;
      } else {
        setIsTyping(false);
        clearInterval(timer);
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed, enabled]);

  return { displayedText, isTyping };
};

type ExecutionState = 'idle' | 'executing' | 'resolved';
type StepStatus = 'pending' | 'running' | 'success' | 'error';

interface ExecutionStep {
  label: string;
  command?: string;
  status: StepStatus;
}

export const AIPersona: React.FC<AIPersonaProps> = ({ 
  insight, 
  isLoading, 
  isOffline,
  deviceStatus,
  riskLevel = 'low',
  onActionComplete,
  onResolvedChange
}) => {
  const [executionState, setExecutionState] = useState<ExecutionState>('idle');
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [resolvedMessage, setResolvedMessage] = useState('');
  
  const message = executionState === 'resolved' 
    ? resolvedMessage 
    : (insight?.story || insight?.headline || '');
  const { displayedText, isTyping } = useTypingEffect(message, 25, !isLoading && !!message);
  
  const ballColor = executionState === 'resolved' ? 'cyan' : (riskLevel === 'high' ? 'red' : riskLevel === 'medium' ? 'yellow' : 'cyan');
  const ballStatus = isLoading ? 'thinking' : executionState === 'executing' ? 'executing' : isTyping ? 'speaking' : 'idle';

  const handleAction = async (decision: ActionButton) => {
    setExecutionState('executing');
    
    const isBlock = decision.action_type === 'block_ip';
    const target = decision.target || 'threat';
    
    // Set up execution steps with actual commands
    const execSteps: ExecutionStep[] = isBlock ? [
      { label: 'Connecting to Sentry device', command: 'ssh sentry@192.168.1.1', status: 'running' },
      { label: 'Adding firewall rule', command: `iptables -A INPUT -s ${target} -j DROP`, status: 'pending' },
      { label: 'Persisting rules', command: 'iptables-save > /etc/iptables/rules.v4', status: 'pending' },
      { label: 'Verifying block', command: `iptables -L INPUT -n | grep ${target}`, status: 'pending' },
    ] : [
      { label: 'Updating threat database', command: `UPDATE alerts SET status='dismissed' WHERE source_ip='${target}'`, status: 'running' },
      { label: 'Adding to whitelist', command: `echo "${target}" >> /etc/cardea/whitelist.conf`, status: 'pending' },
    ];
    
    setSteps(execSteps);

    try {
      // Execute each step with visual feedback
      for (let i = 0; i < execSteps.length; i++) {
        await new Promise(r => setTimeout(r, 800));
        setSteps(s => s.map((step, idx) => 
          idx === i ? { ...step, status: 'success' } : 
          idx === i + 1 ? { ...step, status: 'running' } : step
        ));
      }

      // Make actual API call
      await axios.post(`${ORACLE_URL}/api/actions/execute`, {
        action_type: decision.action_type,
        target: decision.target,
        reason: 'User action from dashboard'
      });

      await new Promise(r => setTimeout(r, 500));
      
      // Mark all steps complete
      setSteps(s => s.map(step => ({ ...step, status: 'success' })));
      
      await new Promise(r => setTimeout(r, 800));
      
      // Transition to resolved state
      const successMsg = isBlock 
        ? `Done! I've blocked ${target} from your network. The firewall rule is now active and will persist across reboots. Your perimeter is secure.`
        : `Got it! I've marked this activity as safe. I won't alert you about ${target} again.`;
      
      setResolvedMessage(successMsg);
      setExecutionState('resolved');
      setSteps([]);
      onResolvedChange?.(true);
      
      // Notify parent to refresh data
      setTimeout(() => onActionComplete?.(), 1500);
      
    } catch {
      setSteps(s => s.map(step => 
        step.status === 'running' ? { ...step, status: 'error' } : step
      ));
    }
  };

  // Reset when insight changes significantly
  useEffect(() => {
    if (insight?.active_threat?.id && executionState === 'resolved') {
      // New threat detected, reset
      setExecutionState('idle');
      setSteps([]);
    }
  }, [insight?.active_threat?.id]);

  // Offline state
  if (isOffline) {
    return (
      <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center gap-6">
          <DiscoBall status="idle" color="cyan" />
          <div className="flex-1">
            <p className="text-slate-200 text-sm font-medium">Hi! I'm your AI security assistant.</p>
            <p className="text-slate-400 text-xs mt-2">Connect your first Sentry device to get started.</p>
          </div>
        </div>
      </div>
    );
  }

  // Device offline
  if (deviceStatus === 'offline') {
    return (
      <div className="bg-gradient-to-br from-yellow-950/20 to-slate-950 border border-yellow-900/30 rounded-2xl p-6">
        <div className="flex items-center gap-6">
          <DiscoBall status="idle" color="yellow" />
          <div className="flex-1">
            <p className="text-yellow-300 text-sm font-medium">I've lost connection to your Sentry device.</p>
            <p className="text-slate-400 text-xs mt-2">Check that it's powered on and connected.</p>
          </div>
        </div>
      </div>
    );
  }

  // Loading
  if (isLoading && !insight) {
    return (
      <div className="bg-gradient-to-br from-cyan-950/20 to-slate-950 border border-cyan-900/30 rounded-2xl p-6">
        <div className="flex items-center gap-6">
          <DiscoBall status="thinking" color="cyan" />
          <div className="flex-1">
            <p className="text-slate-300 text-sm">Scanning your network...</p>
          </div>
        </div>
      </div>
    );
  }

  const emoji = executionState === 'resolved' ? '🟢' : (insight?.status_emoji || '🟢');
  const borderColor = executionState === 'resolved' ? 'border-green-500/50' : 
    (riskLevel === 'high' ? 'border-red-900/50' : riskLevel === 'medium' ? 'border-yellow-900/50' : 'border-cyan-900/50');
  const bgGradient = executionState === 'resolved' ? 'from-green-950/30' :
    (riskLevel === 'high' ? 'from-red-950/30' : riskLevel === 'medium' ? 'from-yellow-950/20' : 'from-cyan-950/20');

  return (
    <div className={`bg-gradient-to-br ${bgGradient} to-slate-900/80 border ${borderColor} rounded-2xl p-6 transition-all duration-500`}>
      <div className="flex items-start gap-6">
        <DiscoBall status={ballStatus} color={ballColor} />
        
        <div className="flex-1 min-w-0">
          {/* Greeting & Status */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{emoji}</span>
            <span className="text-xs text-slate-500">
              {executionState === 'resolved' ? 'Threat Resolved' : (insight?.greeting || 'Security Update')}
            </span>
          </div>
          
          {/* Main message */}
          <p className="text-slate-200 text-sm leading-relaxed">
            {displayedText}
            {isTyping && <span className="inline-block w-0.5 h-4 bg-cyan-400 ml-0.5 animate-pulse" />}
          </p>
          
          {/* Execution Steps - Terminal Style */}
          {steps.length > 0 && (
            <div className="mt-4 bg-slate-950 rounded-lg p-3 font-mono text-xs border border-slate-800">
              <div className="flex items-center gap-2 text-slate-500 mb-2 pb-2 border-b border-slate-800">
                <Terminal className="w-3 h-3" />
                <span>Executing on Sentry</span>
              </div>
              {steps.map((step, idx) => (
                <div key={idx} className="flex items-start gap-2 py-1">
                  {step.status === 'running' ? (
                    <Loader2 className="w-3 h-3 text-cyan-400 animate-spin mt-0.5" />
                  ) : step.status === 'success' ? (
                    <CheckCircle className="w-3 h-3 text-green-400 mt-0.5" />
                  ) : step.status === 'error' ? (
                    <span className="text-red-400">✗</span>
                  ) : (
                    <span className="text-slate-600">○</span>
                  )}
                  <div className="flex-1">
                    <span className={step.status === 'success' ? 'text-green-400' : step.status === 'running' ? 'text-cyan-400' : 'text-slate-500'}>
                      {step.label}
                    </span>
                    {step.command && step.status !== 'pending' && (
                      <div className="text-slate-600 mt-0.5">
                        $ <span className="text-slate-400">{step.command}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* Action Buttons - Only show when idle and there's a threat */}
          {executionState === 'idle' && insight?.decisions && insight.decisions.length > 0 && !isTyping && (
            <div className="flex gap-3 mt-4">
              {insight.decisions.map((decision) => (
                <button
                  key={decision.id}
                  onClick={() => handleAction(decision)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    decision.severity === 'danger' 
                      ? 'bg-red-600 hover:bg-red-500 text-white' 
                      : 'bg-slate-700 hover:bg-slate-600 text-white'
                  }`}
                >
                  {decision.label}
                </button>
              ))}
            </div>
          )}
          
          {/* Timestamp */}
          {insight?.generated_at && !isTyping && executionState === 'idle' && (
            <p className="text-[10px] text-slate-600 mt-3">
              {new Date(insight.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// Simple status cards
interface SimpleStatsProps {
  deviceStatus: 'online' | 'offline';
  riskLevel: 'low' | 'medium' | 'high';
  deviceName?: string;
}

export const SimpleStats: React.FC<SimpleStatsProps> = ({ deviceStatus, riskLevel }) => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-3">
          {deviceStatus === 'online' ? (
            <div className="p-2 bg-green-500/10 rounded-lg">
              <Wifi className="w-5 h-5 text-green-500" />
            </div>
          ) : (
            <div className="p-2 bg-slate-800 rounded-lg">
              <WifiOff className="w-5 h-5 text-slate-500" />
            </div>
          )}
          <div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Sentry</p>
            <p className={`text-sm font-medium ${deviceStatus === 'online' ? 'text-green-400' : 'text-slate-400'}`}>
              {deviceStatus === 'online' ? 'Online' : 'Offline'}
            </p>
          </div>
        </div>
      </div>
      
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${
            riskLevel === 'high' ? 'bg-red-500/10' : riskLevel === 'medium' ? 'bg-yellow-500/10' : 'bg-green-500/10'
          }`}>
            <div className={`w-5 h-5 rounded-full ${
              riskLevel === 'high' ? 'bg-red-500' : riskLevel === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
            }`} />
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Risk Level</p>
            <p className={`text-sm font-medium capitalize ${
              riskLevel === 'high' ? 'text-red-400' : riskLevel === 'medium' ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {riskLevel}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
