import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom'; // Added this
import { 
  Shield, Activity, Zap, Server, AlertCircle, AlertTriangle, Info, XCircle,
  Sparkles, CheckCircle2, WifiOff, RefreshCw, Eye, BarChart3
} from 'lucide-react';
import type { AnalyticsResponse, Alert, AIInsight } from './types'; 
import { ThreatOverview } from './components/ThreatOverview';
// REMOVED: import LoginPage from './components/LoginPage'; 
import { UserMenu } from './components/UserMenu';
import { useAuth } from './lib/useAuth';

// Use environment variable or default to localhost for development
const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || "http://localhost:8000";

// Severity color/icon mapping
const severityConfig = {
  critical: { color: 'text-red-500', bg: 'bg-red-950/20 border-red-900/50', icon: XCircle },
  high: { color: 'text-orange-500', bg: 'bg-orange-950/20 border-orange-900/50', icon: AlertTriangle },
  medium: { color: 'text-yellow-500', bg: 'bg-yellow-950/20 border-yellow-900/50', icon: AlertCircle },
  low: { color: 'text-cyan-500', bg: 'bg-cyan-950/20 border-cyan-900/50', icon: Info },
};

// Toast notification component
const Toast: React.FC<{ message: string; type: 'error' | 'warning' | 'info' | 'success'; onDismiss: () => void }> = ({ message, type, onDismiss }) => {
  const config = {
    error: { bg: 'bg-red-950/90 border-red-800', icon: XCircle, iconColor: 'text-red-400' },
    warning: { bg: 'bg-yellow-950/90 border-yellow-800', icon: AlertTriangle, iconColor: 'text-yellow-400' },
    info: { bg: 'bg-cyan-950/90 border-cyan-800', icon: Info, iconColor: 'text-cyan-400' },
    success: { bg: 'bg-green-950/90 border-green-800', icon: CheckCircle2, iconColor: 'text-green-400' },
  }[type];
  const Icon = config.icon;

  // Auto-dismiss success toasts after 4 seconds
  useEffect(() => {
    if (type === 'success') {
      const timer = setTimeout(onDismiss, 4000);
      return () => clearTimeout(timer);
    }
  }, [type, onDismiss]);

  return (
    <div className={`fixed bottom-6 right-6 z-50 ${config.bg} border rounded-lg shadow-2xl p-4 max-w-md animate-in slide-in-from-bottom-4 fade-in duration-300`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 ${config.iconColor} shrink-0 mt-0.5`} />
        <div className="flex-1">
          <p className="text-sm text-slate-200 font-medium">{message}</p>
          {type === 'error' && <p className="text-xs text-slate-400 mt-1">Automatic retry in progress...</p>}
        </div>
        <button onClick={onDismiss} className="text-slate-500 hover:text-slate-300 transition-colors">
          <XCircle className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

// AI Insight Card Component
const AIInsightCard: React.FC<{ 
  insight: AIInsight | null | undefined; 
  isLoading: boolean;
  isExecutingAction?: boolean;
  onAction?: (action: { id: string; action_type: string; target?: string }) => void;
}> = ({ insight, isLoading, isExecutingAction, onAction }) => {
  const [showTechnical, setShowTechnical] = useState(false);
  const [activeButton, setActiveButton] = useState<string | null>(null);
  
  const handleAction = async (decision: { id: string; action_type: string; target?: string; label?: string }) => {
    setActiveButton(decision.id);
    try {
      await onAction?.(decision);
    } finally {
      setActiveButton(null);
    }
  };
  
  const getButtonStyle = (severity: string) => {
    switch (severity) {
      case 'danger': return 'bg-red-600 hover:bg-red-500 text-white border-red-500';
      case 'warning': return 'bg-orange-600 hover:bg-orange-500 text-white border-orange-500';
      case 'success': return 'bg-green-600 hover:bg-green-500 text-white border-green-500';
      default: return 'bg-slate-700 hover:bg-slate-600 text-slate-200 border-slate-600';
    }
  };

  const getStatusGradient = (emoji: string) => {
    if (emoji === '🔴' || emoji === '🚨') return 'from-red-950/40 via-slate-900/60 to-slate-900/80 border-red-900/50';
    if (emoji === '🟠') return 'from-orange-950/40 via-slate-900/60 to-slate-900/80 border-orange-900/50';
    if (emoji === '🟡') return 'from-yellow-950/30 via-slate-900/60 to-slate-900/80 border-yellow-900/40';
    return 'from-green-950/30 via-slate-900/60 to-cyan-950/20 border-green-900/40';
  };

  const TypingIndicator = () => (
    <div className="flex items-center gap-1">
      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  );

  if (isLoading) {
    return (
      <div className="bg-linear-to-br from-slate-900/80 via-slate-900/60 to-cyan-950/30 border border-slate-800 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 bg-cyan-900/30 rounded-xl">
            <Sparkles className="w-6 h-6 text-cyan-400 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-200">Analyzing your network...</h2>
            <div className="flex items-center gap-2 mt-1">
              <TypingIndicator />
              <span className="text-xs text-slate-500">AI is thinking</span>
            </div>
          </div>
        </div>
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-slate-800/50 rounded w-full" />
          <div className="h-4 bg-slate-800/50 rounded w-5/6" />
          <div className="h-4 bg-slate-800/50 rounded w-4/6" />
        </div>
      </div>
    );
  }

  if (!insight) {
    return (
      <div className="bg-linear-to-br from-slate-900/80 via-slate-900/60 to-slate-800/30 border border-slate-800 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-slate-800/50 rounded-xl">
            <Shield className="w-6 h-6 text-slate-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-400">Cardea Security</h2>
            <p className="text-xs text-slate-600">Connecting to your security brain...</p>
          </div>
        </div>
        <p className="text-slate-500 text-sm leading-relaxed">
          Waiting for connection to analyze your network security.
        </p>
      </div>
    );
  }

  const greeting = insight.greeting || '';
  const statusEmoji = insight.status_emoji || '🟢';
  const headline = insight.headline || insight.summary || 'Security status';
  const story = insight.story || insight.what_happened || '';
  const actionsTaken = insight.actions_taken || [];
  const decisions = insight.decisions || [];
  const technicalSummary = insight.technical_summary;

  return (
    <div className={`bg-linear-to-br ${getStatusGradient(statusEmoji)} border rounded-2xl p-8 relative overflow-hidden`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{statusEmoji}</span>
          <span className="text-lg text-slate-300 font-medium">{greeting}</span>
        </div>
        <span className="text-[10px] text-slate-600 font-mono">
          {insight.generated_at ? new Date(insight.generated_at).toLocaleTimeString([], { hour12: false }) : 'Just now'}
        </span>
      </div>

      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-100 leading-relaxed">{headline}</h2>
      </div>

      {story && (
        <div className="mb-6">
          <p className="text-base text-slate-300 leading-relaxed">{story}</p>
        </div>
      )}

      {actionsTaken.length > 0 && (
        <div className="mb-6 bg-slate-900/40 rounded-xl p-4 border border-slate-800/50">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            <h3 className="text-sm font-medium text-slate-400">What I've already done for you:</h3>
          </div>
          <ul className="space-y-1.5">
            {actionsTaken.map((action, index) => (
              <li key={index} className="flex items-center gap-2 text-sm text-slate-300">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full shrink-0" />
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {decisions.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-medium text-slate-400">What would you like me to do?</h3>
          </div>
          <div className="flex flex-wrap gap-3">
            {decisions.map((decision) => {
              const isExecuting = activeButton === decision.id || isExecutingAction;
              return (
                <button
                  key={decision.id}
                  onClick={() => handleAction(decision)}
                  disabled={isExecuting}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 border ${getButtonStyle(decision.severity)} ${isExecuting ? 'opacity-60 cursor-not-allowed' : 'hover:scale-105 active:scale-95'} shadow-lg flex items-center gap-2`}
                  title={decision.description}
                >
                  {activeButton === decision.id && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {decision.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {technicalSummary && (
        <div className="mt-4 pt-4 border-t border-slate-800/50">
          <button 
            onClick={() => setShowTechnical(!showTechnical)}
            className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-400 transition-colors"
          >
            <Info className="w-3 h-3" />
            {showTechnical ? 'Hide technical details' : 'Show technical details'}
          </button>
          {showTechnical && (
            <p className="mt-2 text-xs text-slate-500 font-mono bg-slate-900/50 rounded p-2">
              {technicalSummary}
            </p>
          )}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-slate-800/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {insight.ai_powered ? (
            <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-medium">
              <Sparkles className="w-3 h-3" /> AI-Powered Analysis
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-slate-500 font-medium">
              <Shield className="w-3 h-3" /> Automated Protection
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-600">
          Confidence: {(insight.confidence * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
};

// Empty State Component
const EmptyState: React.FC<{ title: string; description: string; icon?: React.ElementType }> = ({ 
  title, description, icon: Icon = AlertCircle 
}) => (
  <div className="flex flex-col items-center justify-center py-16 px-8">
    <div className="p-4 bg-slate-900/50 rounded-2xl mb-4">
      <Icon className="w-12 h-12 text-slate-600" />
    </div>
    <h3 className="text-lg font-medium text-slate-400 mb-2">{title}</h3>
    <p className="text-sm text-slate-600 text-center max-w-md">{description}</p>
  </div>
);

// Connection Status Component
const ConnectionStatus: React.FC<{ isConnected: boolean; isRetrying: boolean }> = ({ isConnected, isRetrying }) => (
  <span className="flex items-center gap-1.5">
    {isConnected ? (
      <>
        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
        <span className="text-green-500/70">Oracle: Connected</span>
      </>
    ) : (
      <>
        {isRetrying ? (
          <RefreshCw className="w-3 h-3 text-yellow-500 animate-spin" />
        ) : (
          <WifiOff className="w-3 h-3 text-red-500" />
        )}
        <span className={isRetrying ? "text-yellow-500/70" : "text-red-500/70"}>
          {isRetrying ? "Reconnecting..." : "Oracle: Offline"}
        </span>
      </>
    )}
  </span>
);

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate(); // Hook for redirection

  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showToast, setShowToast] = useState<boolean>(false);
  const [retryCount, setRetryCount] = useState<number>(0);
  const [actionToast, setActionToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [viewMode, setViewMode] = useState<'simple' | 'detailed'>('simple');

  // REDIRECT LOGIC: If done loading and not authenticated, go to login
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [authLoading, isAuthenticated, navigate]);

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const res = await axios.get<AnalyticsResponse>(`${ORACLE_URL}/api/analytics?time_range=today`, {
        timeout: 10000, 
      });
      setData(res.data);
      setError(null);
      setIsConnected(true);
      setLastUpdate(new Date());
      setShowToast(false);
      setRetryCount(0);
    } catch (err) {
      console.error("Oracle API Error:", err);
      setIsConnected(false);
      setRetryCount(prev => prev + 1);
      if (retryCount < 3) {
        setError("Unable to connect to Cardea Oracle backend");
        setShowToast(true);
      }
    } finally {
      setIsLoading(false);
    }
  }, [retryCount, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [fetchData, isAuthenticated]);

  const handleSecurityAction = useCallback(async (action: { id: string; action_type: string; target?: string }) => {
    if (action.action_type === 'expand') return;
    try {
      const res = await axios.post(`${ORACLE_URL}/api/actions/execute`, {
        action_id: action.id,
        action_type: action.action_type,
        target: action.target,
        duration_minutes: 60
      }, { timeout: 10000 });
      
      if (res.data.success) {
        setActionToast({ message: res.data.message, type: 'success' });
        await fetchData();
      } else {
        setActionToast({ message: `Action failed: ${res.data.message}`, type: 'error' });
      }
    } catch (err) {
      console.error('Action execution failed:', err);
      let errorMessage = 'Unknown error';
      if (axios.isAxiosError(err)) {
        errorMessage = err.response?.data?.detail || err.message;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setActionToast({ message: `Failed to execute action: ${errorMessage}`, type: 'error' });
    }
  }, [fetchData]);

  const severityStats = data?.alerts_by_severity || {};
  const criticalCount = severityStats['critical'] || 0;
  const highCount = severityStats['high'] || 0;

  // Render loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Shield className="w-12 h-12 text-cyan-500 animate-pulse" />
          <p className="text-slate-400 text-sm">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, we return null because the useEffect above handles the redirect
  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30">
      {showToast && error && <Toast message={error} type="error" onDismiss={() => setShowToast(false)} />}
      {actionToast && <Toast message={actionToast.message} type={actionToast.type} onDismiss={() => setActionToast(null)} />}

      <header className="border-b border-slate-900 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-500" />
            <span className="font-bold tracking-tight text-lg">
              CARDEA <span className="text-slate-500 font-light">ORACLE</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setViewMode(viewMode === 'simple' ? 'detailed' : 'simple')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                viewMode === 'detailed' ? 'bg-cyan-900/40 text-cyan-400 border border-cyan-800/50' : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-800'
              }`}
              title={viewMode === 'simple' ? 'Show technical details' : 'Hide technical details'}
            >
              {viewMode === 'detailed' ? <><BarChart3 className="w-3.5 h-3.5" /> Technical View</> : <><Eye className="w-3.5 h-3.5" /> Simple View</>}
            </button>
            
            <div className="flex items-center gap-6 text-[10px] font-bold text-slate-500 tracking-widest uppercase">
            {isConnected && (criticalCount > 0 || highCount > 0) && (
              <span className="flex items-center gap-1.5 text-red-500">
                <AlertTriangle className="w-3 h-3" />
                {criticalCount + highCount} Critical/High Alerts
              </span>
            )}
            <ConnectionStatus isConnected={isConnected} isRetrying={!isConnected && retryCount > 0} />
            {lastUpdate && isConnected && (
              <span className="text-slate-600">Updated: {lastUpdate.toLocaleTimeString([], { hour12: false })}</span>
            )}
            </div>
            
            {user && <UserMenu user={user} />}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10 space-y-6">
        <AIInsightCard insight={data?.ai_insight} isLoading={isLoading && !data} onAction={handleSecurityAction} />

        {viewMode === 'simple' && isConnected && data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${criticalCount > 0 ? 'bg-red-500 animate-pulse' : highCount > 0 ? 'bg-orange-500' : 'bg-green-500'}`} />
                <span className="text-xs font-medium text-slate-400">Network Status</span>
              </div>
              <p className={`text-lg font-semibold ${criticalCount > 0 ? 'text-red-400' : highCount > 0 ? 'text-orange-400' : 'text-green-400'}`}>
                {criticalCount > 0 ? 'Needs Attention' : highCount > 0 ? 'Monitoring' : 'All Clear'}
              </p>
            </div>

            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-3 h-3 text-cyan-500" />
                <span className="text-xs font-medium text-slate-400">Risk Level</span>
              </div>
              <p className={`text-lg font-semibold ${(data?.risk_score || 0) >= 0.7 ? 'text-red-400' : (data?.risk_score || 0) >= 0.4 ? 'text-yellow-400' : 'text-cyan-400'}`}>
                {(data?.risk_score || 0) >= 0.7 ? 'High' : (data?.risk_score || 0) >= 0.4 ? 'Medium' : 'Low'}
              </p>
            </div>

            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-3 h-3 text-purple-500" />
                <span className="text-xs font-medium text-slate-400">Events Today</span>
              </div>
              <p className="text-lg font-semibold text-slate-200">{data.total_alerts || 0}</p>
            </div>

            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-3 h-3 text-green-500" />
                <span className="text-xs font-medium text-slate-400">Protection</span>
              </div>
              <p className="text-lg font-semibold text-green-400">Active</p>
            </div>
          </div>
        )}

        {viewMode === 'detailed' && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ThreatOverview alerts={data?.alerts || []} severityStats={severityStats} isConnected={isConnected} />
              </div>
              
              <div className="flex flex-col gap-6">
                <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-xl flex-1 flex flex-col justify-center relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-2 opacity-10">
                    <Zap className="w-20 h-20 text-cyan-400" />
                  </div>
                  <div className="flex items-center gap-2 text-slate-500 mb-2 relative z-10">
                    <Zap className="w-3 h-3 text-cyan-500" />
                    <p className="text-[10px] font-bold uppercase tracking-wider">Risk Index</p>
                  </div>
                  {isConnected && data ? (
                    <>
                      <p className={`text-5xl font-extralight relative z-10 ${(data?.risk_score || 0) >= 0.7 ? 'text-red-400' : (data?.risk_score || 0) >= 0.4 ? 'text-yellow-400' : 'text-cyan-400'}`}>
                        {((data?.risk_score || 0) * 100).toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-slate-600 mt-4 leading-relaxed font-medium uppercase tracking-tighter">AI-Powered Threat Analysis</p>
                    </>
                  ) : (
                    <p className="text-5xl font-extralight text-slate-700 relative z-10">—</p>
                  )}
                </div>
                
                <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-xl flex-1 flex flex-col justify-center">
                  <div className="flex items-center gap-2 text-slate-500 mb-2">
                    <Activity className="w-3 h-3 text-purple-500" />
                    <p className="text-[10px] font-bold uppercase tracking-wider">Events Today</p>
                  </div>
                  {isConnected && data ? (
                    <>
                      <p className="text-5xl font-extralight">{data.total_alerts || 0}</p>
                      {Object.keys(severityStats).length > 0 && (
                        <div className="flex gap-3 mt-4">
                          {Object.entries(severityStats).map(([severity, count]) => {
                            const config = severityConfig[severity as keyof typeof severityConfig] || severityConfig.low;
                            return (
                              <div key={severity} className={`flex items-center gap-1 text-[9px] ${config.color}`}>
                                <span className="font-bold">{count as number}</span>
                                <span className="uppercase opacity-70">{severity}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-5xl font-extralight text-slate-700">—</p>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-slate-900/20 border border-slate-900 rounded-xl overflow-hidden shadow-2xl">
              <div className="px-6 py-4 border-b border-slate-900 bg-slate-900/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-slate-500" />
                    <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">Today's Security Events</h2>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">Showing latest 50 alerts</div>
                  <div className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">Updates: Auto (5s)</div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="text-slate-600 text-[10px] uppercase tracking-widest border-b border-slate-900/50">
                      <th className="px-6 py-4 font-bold">Timestamp</th>
                      <th className="px-6 py-4 font-bold">Alert Signature</th>
                      <th className="px-6 py-4 font-bold">Source</th>
                      <th className="px-6 py-4 font-bold text-center">Threat</th>
                      <th className="px-6 py-4 font-bold text-right">Severity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/50">
                    {!isConnected ? (
                      <tr>
                        <td colSpan={5} className="p-16 text-center">
                          <EmptyState icon={WifiOff} title="Oracle Backend Offline" description="Unable to connect to the Cardea Oracle backend. The system will automatically retry the connection. Check that the Oracle service is running." />
                        </td>
                      </tr>
                    ) : data?.alerts && data.alerts.length > 0 ? (
                      data.alerts.map((alert: Alert) => {
                        const config = severityConfig[alert.severity] || severityConfig.low;
                        const SeverityIcon = config.icon;
                        return (
                        <tr key={alert.id} className="hover:bg-slate-900/40 transition-colors group">
                          <td className="px-6 py-5 text-xs text-slate-500 font-mono tabular-nums">
                            {new Date(alert.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </td>
                          <td className="px-6 py-5">
                            <p className="text-sm font-semibold text-slate-300 group-hover:text-cyan-400 transition-colors">
                              {(alert.alert_type || 'Unknown').replaceAll('_', ' ').toUpperCase()}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-1 italic max-w-md">"{alert.description}"</p>
                          </td>
                          <td className="px-6 py-5 text-xs font-mono text-slate-400">{alert.source}</td>
                          <td className="px-6 py-5 text-center">
                            {alert.threat_score !== undefined && alert.threat_score !== null ? (
                              <span className={`text-[10px] font-bold tabular-nums ${alert.threat_score >= 0.7 ? 'text-red-500' : alert.threat_score >= 0.4 ? 'text-yellow-500' : 'text-green-500'}`}>
                                {(alert.threat_score * 100).toFixed(0)}%
                              </span>
                            ) : (<span className="text-[10px] text-slate-600">—</span>)}
                          </td>
                          <td className="px-6 py-5 text-right">
                            <span className={`inline-flex items-center gap-1.5 text-[9px] font-black px-2.5 py-1 rounded border tracking-tighter ${config.bg} ${config.color}`}>
                              <SeverityIcon className="w-3 h-3" />
                              {alert.severity.toUpperCase()}
                            </span>
                          </td>
                        </tr>
                      )})
                    ) : (
                      <tr>
                        <td colSpan={5} className="p-16 text-center">
                          <EmptyState icon={Shield} title="No Active Threats" description="No tactical anomalies detected in the current monitoring buffer. The network appears secure." />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default App;