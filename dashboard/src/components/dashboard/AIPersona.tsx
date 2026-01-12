import { useState, useEffect, useRef } from 'react';
import { Wifi, WifiOff, Shield, AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react';
import type { AIInsight, ActionButton } from '../../types';
import axios from 'axios';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8000';

interface AIPersonaProps {
  insight: AIInsight | null | undefined;
  isLoading: boolean;
  isOffline?: boolean;
  deviceStatus?: 'online' | 'offline';
  riskLevel?: 'low' | 'medium' | 'high';
}

// Disco Ball SVG Component
const DiscoBall: React.FC<{ status: 'idle' | 'thinking' | 'speaking'; color: string }> = ({ status, color }) => {
  const baseColor = color === 'red' ? '#ef4444' : color === 'yellow' ? '#eab308' : '#22d3ee';
  const glowColor = color === 'red' ? 'rgba(239,68,68,0.4)' : color === 'yellow' ? 'rgba(234,179,8,0.4)' : 'rgba(34,211,238,0.4)';
  
  return (
    <div className={`relative ${status === 'thinking' ? 'animate-pulse' : ''}`}>
      {/* Glow effect */}
      <div 
        className={`absolute inset-0 rounded-full blur-xl transition-opacity duration-500 ${status === 'speaking' ? 'opacity-60' : 'opacity-30'}`}
        style={{ background: glowColor }}
      />
      
      {/* Main disco ball */}
      <svg viewBox="0 0 100 100" className="w-16 h-16 relative z-10">
        <defs>
          <radialGradient id="ballGradient" cx="30%" cy="30%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="50%" stopColor={baseColor} stopOpacity="0.6" />
            <stop offset="100%" stopColor="#1e293b" stopOpacity="0.8" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        
        {/* Ball base */}
        <circle cx="50" cy="50" r="40" fill="url(#ballGradient)" filter="url(#glow)" />
        
        {/* Facets - animated rotation */}
        <g className={status !== 'idle' ? 'animate-spin' : ''} style={{ transformOrigin: '50px 50px', animationDuration: '8s' }}>
          {[0, 30, 60, 90, 120, 150].map((angle, i) => (
            <g key={i} transform={`rotate(${angle} 50 50)`}>
              <rect x="45" y="15" width="10" height="8" rx="1" fill="white" opacity={0.3 + (i % 3) * 0.2} />
              <rect x="30" y="28" width="8" height="6" rx="1" fill="white" opacity={0.2 + (i % 2) * 0.3} />
              <rect x="62" y="28" width="8" height="6" rx="1" fill="white" opacity={0.4} />
              <rect x="20" y="45" width="6" height="10" rx="1" fill="white" opacity={0.25} />
              <rect x="74" y="45" width="6" height="10" rx="1" fill="white" opacity={0.35} />
            </g>
          ))}
        </g>
        
        {/* Highlight */}
        <ellipse cx="35" cy="35" rx="12" ry="8" fill="white" opacity="0.3" />
      </svg>
      
      {/* Sparkle effects when speaking */}
      {status === 'speaking' && (
        <div className="absolute inset-0 pointer-events-none">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 bg-white rounded-full animate-ping"
              style={{
                left: `${20 + Math.random() * 60}%`,
                top: `${20 + Math.random() * 60}%`,
                animationDelay: `${i * 0.2}s`,
                animationDuration: '1.5s'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Typing animation hook - only animates when text actually changes
const useTypingEffect = (text: string, speed: number = 30, enabled: boolean = true) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const prevTextRef = useRef<string>('');
  const hasAnimatedRef = useRef<boolean>(false);

  useEffect(() => {
    if (!enabled || !text) {
      setDisplayedText(text || '');
      return;
    }

    // Skip animation if text hasn't changed
    if (text === prevTextRef.current && hasAnimatedRef.current) {
      setDisplayedText(text);
      return;
    }

    prevTextRef.current = text;
    hasAnimatedRef.current = true;
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

export const AIPersona: React.FC<AIPersonaProps> = ({ 
  insight, 
  isLoading, 
  isOffline,
  deviceStatus,
  riskLevel = 'low'
}) => {
  const message = insight?.story || insight?.headline || insight?.summary || '';
  const { displayedText, isTyping } = useTypingEffect(message, 20, !isLoading && !!insight);
  
  const ballColor = riskLevel === 'high' ? 'red' : riskLevel === 'medium' ? 'yellow' : 'cyan';
  const ballStatus = isLoading ? 'thinking' : isTyping ? 'speaking' : 'idle';

  // No devices at all - prompt to connect first device
  if (isOffline) {
    return (
      <div className="bg-gradient-to-br from-slate-900/80 to-slate-950 border border-slate-800 rounded-2xl p-6 shadow-lg">
        <div className="flex items-center gap-6">
          <DiscoBall status="idle" color="cyan" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">👋</span>
              <span className="text-xs text-slate-500">Welcome to Cardea</span>
            </div>
            <p className="text-slate-200 text-sm font-medium">Hi there! I'm your AI security assistant.</p>
            <p className="text-slate-400 text-xs mt-2 leading-relaxed">
              I'll help you monitor your network for threats and keep your business safe. 
              Let's start by connecting your first Sentry device.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Device exists but is offline
  if (deviceStatus === 'offline') {
    return (
      <div className="bg-gradient-to-br from-yellow-950/20 to-slate-950 border border-yellow-900/30 rounded-2xl p-6 shadow-lg">
        <div className="flex items-center gap-6">
          <DiscoBall status="idle" color="yellow" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">📡</span>
              <span className="text-xs text-yellow-500/70">Connection Issue</span>
            </div>
            <p className="text-yellow-300 text-sm font-medium">I've lost connection to your Sentry device.</p>
            <p className="text-slate-400 text-xs mt-2 leading-relaxed">
              This could be a network issue or the device may need attention. 
              Check that it's powered on and connected to your network. I'll automatically reconnect when it's back online.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-cyan-950/20 to-slate-950 border border-cyan-900/30 rounded-2xl p-6 shadow-lg">
        <div className="flex items-center gap-6">
          <DiscoBall status="thinking" color="cyan" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🔍</span>
              <span className="text-xs text-cyan-500/70">Analyzing</span>
            </div>
            <p className="text-slate-300 text-sm">Scanning your network for threats...</p>
            <div className="flex gap-1.5 mt-3">
              <span className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const emoji = insight?.status_emoji || '🟢';
  const borderColor = riskLevel === 'high' ? 'border-red-900/50' : riskLevel === 'medium' ? 'border-yellow-900/50' : 'border-cyan-900/50';
  const bgGradient = riskLevel === 'high' ? 'from-red-950/30' : riskLevel === 'medium' ? 'from-yellow-950/20' : 'from-cyan-950/20';
  
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleAction = async (decision: ActionButton) => {
    setActionLoading(decision.id);
    setActionResult(null);
    
    try {
      const response = await axios.post(`${ORACLE_URL}/api/actions/execute`, {
        action_type: decision.action_type,
        target: decision.target,
        reason: 'User decision from dashboard'
      });
      
      setActionResult({
        success: response.data.success,
        message: response.data.message
      });
    } catch (error) {
      setActionResult({
        success: false,
        message: 'Could not complete action. Please try again.'
      });
    } finally {
      setActionLoading(null);
    }
  };

  const getButtonStyle = (severity: string) => {
    switch (severity) {
      case 'danger': return 'bg-red-600 hover:bg-red-500 text-white';
      case 'warning': return 'bg-yellow-600 hover:bg-yellow-500 text-white';
      case 'success': return 'bg-green-600 hover:bg-green-500 text-white';
      default: return 'bg-slate-600 hover:bg-slate-500 text-white';
    }
  };

  const getButtonIcon = (actionType: string) => {
    switch (actionType) {
      case 'block_ip': return <XCircle className="w-4 h-4" />;
      case 'dismiss': return <CheckCircle className="w-4 h-4" />;
      case 'monitor': return <Eye className="w-4 h-4" />;
      default: return <Shield className="w-4 h-4" />;
    }
  };

  return (
    <div className={`bg-gradient-to-br ${bgGradient} to-slate-900/80 border ${borderColor} rounded-2xl p-6`}>
      <div className="flex items-start gap-6">
        <DiscoBall status={ballStatus} color={ballColor} />
        
        <div className="flex-1 min-w-0">
          {/* Greeting */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{emoji}</span>
            <span className="text-xs text-slate-500">{insight?.greeting || 'Security Update'}</span>
          </div>
          
          {/* Main message with typing effect */}
          <p className="text-slate-200 text-sm leading-relaxed">
            {displayedText}
            {isTyping && <span className="inline-block w-0.5 h-4 bg-cyan-400 ml-0.5 animate-pulse" />}
          </p>
          
          {/* Question for user */}
          {insight?.question && !isTyping && (
            <p className="text-slate-300 text-sm mt-3 font-medium">
              {insight.question}
            </p>
          )}
          
          {/* Action Result */}
          {actionResult && (
            <div className={`mt-3 p-3 rounded-lg text-sm ${actionResult.success ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
              {actionResult.success ? <CheckCircle className="w-4 h-4 inline mr-2" /> : <AlertTriangle className="w-4 h-4 inline mr-2" />}
              {actionResult.message}
            </div>
          )}
          
          {/* Decision Buttons */}
          {insight?.decisions && insight.decisions.length > 0 && !actionResult && !isTyping && (
            <div className="flex flex-wrap gap-2 mt-4">
              {insight.decisions.map((decision) => (
                <button
                  key={decision.id}
                  onClick={() => handleAction(decision)}
                  disabled={actionLoading !== null}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${getButtonStyle(decision.severity)} ${actionLoading === decision.id ? 'opacity-50' : ''}`}
                  title={decision.description}
                >
                  {actionLoading === decision.id ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    getButtonIcon(decision.action_type)
                  )}
                  {decision.label}
                </button>
              ))}
            </div>
          )}
          
          {/* Timestamp */}
          {insight?.generated_at && !isTyping && (
            <p className="text-[10px] text-slate-600 mt-3">
              {new Date(insight.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// Simple status cards for Simple Mode
interface SimpleStatsProps {
  deviceStatus: 'online' | 'offline';
  riskLevel: 'low' | 'medium' | 'high';
  deviceName?: string;
}

export const SimpleStats: React.FC<SimpleStatsProps> = ({ deviceStatus, riskLevel, deviceName }) => {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Device Status */}
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
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Sentry Status</p>
            <p className={`text-sm font-medium ${deviceStatus === 'online' ? 'text-green-400' : 'text-slate-400'}`}>
              {deviceStatus === 'online' ? 'Connected' : 'Offline'}
            </p>
            {deviceName && <p className="text-[10px] text-slate-600">{deviceName}</p>}
          </div>
        </div>
      </div>

      {/* Risk Level */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${
            riskLevel === 'high' ? 'bg-red-500/10' : 
            riskLevel === 'medium' ? 'bg-yellow-500/10' : 'bg-cyan-500/10'
          }`}>
            <div className={`w-5 h-5 rounded-full ${
              riskLevel === 'high' ? 'bg-red-500 animate-pulse' : 
              riskLevel === 'medium' ? 'bg-yellow-500' : 'bg-cyan-500'
            }`} />
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Risk Level</p>
            <p className={`text-sm font-medium ${
              riskLevel === 'high' ? 'text-red-400' : 
              riskLevel === 'medium' ? 'text-yellow-400' : 'text-cyan-400'
            }`}>
              {riskLevel === 'high' ? 'High Risk' : riskLevel === 'medium' ? 'Medium' : 'All Clear'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
