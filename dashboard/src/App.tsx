import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import {
  Shield, Activity, Zap, Server, AlertTriangle, Info, XCircle, Sparkles,
  CheckCircle2, WifiOff, RefreshCw, Eye, BarChart3, Plus, ChevronRight, X
} from "lucide-react";
import type { AnalyticsResponse, Alert, AIInsight, Device } from "./types";
import { ThreatOverview } from "./components/ThreatOverview";
import { UserMenu } from "./components/UserMenu";
import { useAuth } from "./lib/useAuth";

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || "http://localhost:8000";

const severityConfig = {
  critical: { color: "text-red-500", bg: "bg-red-950/30 border-red-900/50", icon: XCircle },
  high: { color: "text-orange-500", bg: "bg-orange-950/30 border-orange-900/50", icon: AlertTriangle },
  medium: { color: "text-yellow-500", bg: "bg-yellow-950/30 border-yellow-900/50", icon: AlertTriangle },
  low: { color: "text-cyan-500", bg: "bg-cyan-950/30 border-cyan-900/50", icon: Info },
};

// Toast Component
const Toast: React.FC<{ message: string; type: "error" | "success"; onDismiss: () => void }> = ({ message, type, onDismiss }) => {
  useEffect(() => { if (type === "success") { const t = setTimeout(onDismiss, 3000); return () => clearTimeout(t); } }, [type, onDismiss]);
  return (
    <div className={`fixed bottom-4 right-4 z-50 ${type === "error" ? "bg-red-950/95 border-red-800" : "bg-green-950/95 border-green-800"} border rounded-lg px-4 py-3 flex items-center gap-3 animate-in slide-in-from-bottom-2`}>
      {type === "error" ? <XCircle className="w-4 h-4 text-red-400" /> : <CheckCircle2 className="w-4 h-4 text-green-400" />}
      <span className="text-sm">{message}</span>
      <button onClick={onDismiss} className="text-slate-500 hover:text-white ml-2"><X className="w-4 h-4" /></button>
    </div>
  );
};

// Onboarding Tooltip
const OnboardingTooltip: React.FC<{ step: number; total: number; title: string; desc: string; onNext: () => void; onSkip: () => void; position?: string }> = 
  ({ step, total, title, desc, onNext, onSkip, position = "bottom" }) => (
  <div className={`absolute z-50 w-72 bg-slate-900 border border-cyan-500/50 rounded-xl p-4 shadow-2xl shadow-cyan-500/10 animate-in fade-in slide-in-from-${position === "top" ? "bottom" : "top"}-2 duration-300`}
       style={{ [position === "top" ? "bottom" : "top"]: "100%", left: "50%", transform: "translateX(-50%)", marginTop: position === "top" ? 0 : 8, marginBottom: position === "top" ? 8 : 0 }}>
    <div className={`absolute ${position === "top" ? "bottom-0 translate-y-1/2" : "top-0 -translate-y-1/2"} left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-${position === "top" ? "b border-r" : "t border-l"} border-cyan-500/50 rotate-45`} />
    <div className="flex items-center justify-between mb-2">
      <span className="text-[10px] text-cyan-400 font-medium">Step {step}/{total}</span>
      <button onClick={onSkip} className="text-[10px] text-slate-500 hover:text-slate-300">Skip tour</button>
    </div>
    <h4 className="text-sm font-semibold text-white mb-1">{title}</h4>
    <p className="text-xs text-slate-400 mb-3">{desc}</p>
    <button onClick={onNext} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium py-2 rounded-lg flex items-center justify-center gap-1 transition-colors">
      {step === total ? "Got it!" : "Next"} <ChevronRight className="w-3 h-3" />
    </button>
  </div>
);

// AI Insight Card
const AIInsightCard: React.FC<{ insight: AIInsight | null | undefined; isLoading: boolean; isOffline?: boolean }> = ({ insight, isLoading, isOffline }) => {
  const [showTech, setShowTech] = useState(false);

  if (isOffline) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-slate-800 rounded-lg"><Sparkles className="w-5 h-5 text-slate-600" /></div>
          <div>
            <h2 className="text-sm font-medium text-slate-500">AI Analysis</h2>
            <span className="text-[10px] text-slate-600">Offline</span>
          </div>
        </div>
        <p className="text-sm text-slate-500">Connect a Sentry device to enable AI-powered threat analysis.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 animate-pulse">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-900/30 rounded-lg"><Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" /></div>
          <div className="space-y-1"><div className="h-4 w-32 bg-slate-800 rounded" /><div className="h-3 w-20 bg-slate-800 rounded" /></div>
        </div>
        <div className="space-y-2"><div className="h-3 bg-slate-800 rounded w-full" /><div className="h-3 bg-slate-800 rounded w-4/5" /></div>
      </div>
    );
  }

  if (!insight) return null;

  const emoji = insight.status_emoji || "🟢";
  const gradient = emoji === "🔴" || emoji === "🚨" ? "from-red-950/40 border-red-900/40" : emoji === "🟠" ? "from-orange-950/40 border-orange-900/40" : emoji === "🟡" ? "from-yellow-950/30 border-yellow-900/30" : "from-green-950/30 border-green-900/30";

  return (
    <div className={`bg-gradient-to-br ${gradient} to-slate-900/80 border rounded-xl p-6`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{emoji}</span>
          <div>
            <p className="text-sm text-slate-400">{insight.greeting}</p>
            <h2 className="text-lg font-semibold text-white">{insight.headline || insight.summary}</h2>
          </div>
        </div>
        <span className="text-[10px] text-slate-600 font-mono">{insight.generated_at ? new Date(insight.generated_at).toLocaleTimeString([], { hour12: false }) : ""}</span>
      </div>
      {insight.story && <p className="text-sm text-slate-300 mb-4 leading-relaxed">{insight.story}</p>}
      {insight.actions_taken && insight.actions_taken.length > 0 && (
        <div className="bg-slate-900/50 rounded-lg p-3 mb-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Actions taken</p>
          <ul className="space-y-1">{insight.actions_taken.map((a, i) => <li key={i} className="text-xs text-slate-400 flex items-center gap-2"><CheckCircle2 className="w-3 h-3 text-green-500" />{a}</li>)}</ul>
        </div>
      )}
      {insight.technical_summary && (
        <button onClick={() => setShowTech(!showTech)} className="text-[10px] text-slate-500 hover:text-slate-400 flex items-center gap-1">
          <Info className="w-3 h-3" />{showTech ? "Hide" : "Show"} technical details
        </button>
      )}
      {showTech && insight.technical_summary && <p className="mt-2 text-[10px] text-slate-500 font-mono bg-slate-900/50 rounded p-2">{insight.technical_summary}</p>}
      <div className="mt-4 pt-3 border-t border-slate-800/50 flex items-center justify-between">
        <span className="text-[10px] text-cyan-500 flex items-center gap-1"><Sparkles className="w-3 h-3" />AI Analysis</span>
        <span className="text-[10px] text-slate-600">{((insight.confidence || 0) * 100).toFixed(0)}% confidence</span>
      </div>
    </div>
  );
};

// Empty State for No Devices
const NoDevicesState: React.FC<{ showOnboarding: boolean; onboardingStep: number; onNextStep: () => void; onSkip: () => void }> = ({ showOnboarding, onboardingStep, onNextStep, onSkip }) => (
  <div className="max-w-lg mx-auto text-center py-12">
    <div className="relative inline-block mb-6">
      <div className="w-16 h-16 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center">
        <Server className="w-8 h-8 text-slate-600" />
      </div>
      <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-slate-800 rounded-full flex items-center justify-center border-2 border-slate-950">
        <Plus className="w-3 h-3 text-slate-500" />
      </div>
    </div>
    <h2 className="text-xl font-semibold text-white mb-2">No Sentry Devices</h2>
    <p className="text-sm text-slate-500 mb-6">Connect your first Sentry device to start monitoring your network.</p>
    
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
        <span>Quick Setup</span>
        <span className="text-slate-600">~2 min</span>
      </div>
      <div className="flex justify-between">
        {[{ n: 1, t: "Power on" }, { n: 2, t: "Get code" }, { n: 3, t: "Enter here" }].map((s, i) => (
          <div key={s.n} className="flex flex-col items-center gap-1">
            <div className="w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-xs font-bold text-cyan-400">{s.n}</div>
            <span className="text-[10px] text-slate-500">{s.t}</span>
            {i < 2 && <ChevronRight className="w-3 h-3 text-slate-700 absolute" style={{ marginLeft: "80px", marginTop: "10px" }} />}
          </div>
        ))}
      </div>
    </div>

    <div className="relative inline-block">
      <Link to="/devices" className="inline-flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-2.5 rounded-lg font-medium text-sm transition-all hover:scale-105 active:scale-95">
        <Plus className="w-4 h-4" /> Connect Device
      </Link>
      {showOnboarding && onboardingStep === 1 && (
        <OnboardingTooltip step={1} total={3} title="Start Here" desc="Click to add your first Sentry device and begin monitoring." onNext={onNextStep} onSkip={onSkip} />
      )}
    </div>
  </div>
);

// Stats Cards
const StatsGrid: React.FC<{ data: AnalyticsResponse | null; isConnected: boolean }> = ({ data, isConnected }) => {
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
        <div className="flex items-center gap-2 mb-2"><Zap className="w-3 h-3 text-cyan-500" /><span className="text-[10px] text-slate-500 uppercase tracking-wider">Risk</span></div>
        <p className={`text-sm font-semibold ${risk >= 0.7 ? "text-red-400" : risk >= 0.4 ? "text-yellow-400" : "text-cyan-400"}`}>{risk >= 0.7 ? "High" : risk >= 0.4 ? "Medium" : "Low"}</p>
      </div>
      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2"><Activity className="w-3 h-3 text-purple-500" /><span className="text-[10px] text-slate-500 uppercase tracking-wider">Events</span></div>
        <p className="text-sm font-semibold text-slate-200">{data.total_alerts || 0}</p>
      </div>
      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2"><Shield className="w-3 h-3 text-green-500" /><span className="text-[10px] text-slate-500 uppercase tracking-wider">Protection</span></div>
        <p className="text-sm font-semibold text-green-400">Active</p>
      </div>
    </div>
  );
};

// Alert Table
const AlertTable: React.FC<{ alerts: Alert[]; isConnected: boolean }> = ({ alerts, isConnected }) => {
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
              <span className="text-[10px] text-slate-600 font-mono w-16">{new Date(alert.timestamp).toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit" })}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-300 truncate">{(alert.alert_type || "Unknown").replaceAll("_", " ")}</p>
                <p className="text-[10px] text-slate-500 truncate">{alert.description}</p>
              </div>
              <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${cfg.bg} ${cfg.color}`}>{alert.severity.toUpperCase()}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate();

  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasDevices, setHasDevices] = useState<boolean | null>(null);
  const [viewMode, setViewMode] = useState<"simple" | "detailed">("simple");
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);
  
  // Onboarding
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(1);
  const retryRef = useRef(0);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) navigate("/login");
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    // Show onboarding for new users (no devices, first visit)
    if (hasDevices === false && !localStorage.getItem("cardea_onboarding_done")) {
      setShowOnboarding(true);
    }
  }, [hasDevices]);

  const skipOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem("cardea_onboarding_done", "true");
  };

  const nextOnboardingStep = () => {
    if (onboardingStep >= 3) skipOnboarding();
    else setOnboardingStep(s => s + 1);
  };

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) return;
    const token = localStorage.getItem("token");

    try {
      const devRes = await axios.get<Device[]>(`${ORACLE_URL}/api/devices/list`, { headers: { Authorization: `Bearer ${token}` } });
      const count = Array.isArray(devRes.data) ? devRes.data.length : 0;
      setHasDevices(count > 0);
    } catch { /* ignore */ }

    try {
      const res = await axios.get<AnalyticsResponse>(`${ORACLE_URL}/api/analytics?time_range=today`, { timeout: 30000 });
      setData(res.data);
      setIsConnected(true);
      retryRef.current = 0;
    } catch {
      setIsConnected(false);
      retryRef.current++;
      if (retryRef.current >= 3) setToast({ message: "Connection to Oracle lost", type: "error" });
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [fetchData, isAuthenticated]);

  useEffect(() => { document.title = "Cardea | Dashboard"; }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Shield className="w-10 h-10 text-cyan-500 animate-pulse" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const critical = data?.alerts_by_severity?.critical || 0;
  const high = data?.alerts_by_severity?.high || 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40 px-6 py-3">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-500" />
            <span className="font-bold text-sm tracking-tight">CARDEA</span>
          </div>
          <div className="flex items-center gap-4">
            {hasDevices && (
              <button onClick={() => setViewMode(v => v === "simple" ? "detailed" : "simple")}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-medium transition-all ${viewMode === "detailed" ? "bg-cyan-900/40 text-cyan-400" : "bg-slate-800/50 text-slate-500 hover:text-slate-300"}`}>
                {viewMode === "detailed" ? <><BarChart3 className="w-3 h-3" />Technical</> : <><Eye className="w-3 h-3" />Simple</>}
              </button>
            )}
            <div className="flex items-center gap-3 text-[10px] text-slate-500">
              {hasDevices && (critical > 0 || high > 0) && (
                <span className="text-red-500 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{critical + high}</span>
              )}
              {hasDevices && (
                <span className="flex items-center gap-1">
                  {isConnected ? <><div className="w-1.5 h-1.5 rounded-full bg-green-500" />Online</> : <><RefreshCw className="w-3 h-3 animate-spin" />Connecting</>}
                </span>
              )}
            </div>
            {user && <UserMenu user={user} />}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {hasDevices === false && !isLoading ? (
          <>
            <AIInsightCard insight={null} isLoading={false} isOffline={true} />
            <NoDevicesState showOnboarding={showOnboarding} onboardingStep={onboardingStep} onNextStep={nextOnboardingStep} onSkip={skipOnboarding} />
          </>
        ) : hasDevices === true ? (
          <>
            <AIInsightCard insight={data?.ai_insight} isLoading={isLoading && !data} />
            {viewMode === "simple" && <StatsGrid data={data} isConnected={isConnected} />}
            {viewMode === "detailed" && (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <div className="col-span-2"><ThreatOverview alerts={data?.alerts || []} severityStats={data?.alerts_by_severity || {}} isConnected={isConnected} /></div>
                  <div className="space-y-4">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2"><Zap className="w-3 h-3 text-cyan-500" /><span className="text-[10px] text-slate-500 uppercase">Risk Index</span></div>
                      <p className={`text-3xl font-light ${(data?.risk_score || 0) >= 0.7 ? "text-red-400" : (data?.risk_score || 0) >= 0.4 ? "text-yellow-400" : "text-cyan-400"}`}>
                        {((data?.risk_score || 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2"><Activity className="w-3 h-3 text-purple-500" /><span className="text-[10px] text-slate-500 uppercase">Events Today</span></div>
                      <p className="text-3xl font-light">{data?.total_alerts || 0}</p>
                    </div>
                  </div>
                </div>
                <AlertTable alerts={data?.alerts || []} isConnected={isConnected} />
              </>
            )}
            {viewMode === "simple" && <AlertTable alerts={data?.alerts || []} isConnected={isConnected} />}
          </>
        ) : (
          <div className="flex items-center justify-center py-20"><RefreshCw className="w-6 h-6 text-slate-600 animate-spin" /></div>
        )}
      </main>

      {/* Onboarding overlay for other steps */}
      {showOnboarding && onboardingStep === 2 && hasDevices === false && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-sm text-center animate-in zoom-in-95">
            <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center mx-auto mb-4"><Sparkles className="w-6 h-6 text-cyan-400" /></div>
            <h3 className="text-lg font-semibold text-white mb-2">AI-Powered Protection</h3>
            <p className="text-sm text-slate-400 mb-4">Once connected, Cardea's AI will analyze your network traffic in real-time and provide actionable insights.</p>
            <button onClick={nextOnboardingStep} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-2 rounded-lg text-sm font-medium">Continue</button>
          </div>
        </div>
      )}
      {showOnboarding && onboardingStep === 3 && hasDevices === false && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-sm text-center animate-in zoom-in-95">
            <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-4"><CheckCircle2 className="w-6 h-6 text-green-400" /></div>
            <h3 className="text-lg font-semibold text-white mb-2">You're All Set!</h3>
            <p className="text-sm text-slate-400 mb-4">Click "Connect Device" to add your Sentry and start protecting your network.</p>
            <button onClick={skipOnboarding} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-2 rounded-lg text-sm font-medium">Get Started</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
