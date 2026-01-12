import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, RefreshCw, AlertTriangle, Zap, Activity, Eye, BarChart3 } from "lucide-react";
import { ThreatOverview } from "./components/ThreatOverview";
import { UserMenu } from "./components/UserMenu";
import { useAuth } from "./lib/useAuth";
import { Toast } from "./components/common";
import { AIInsightCard, StatsGrid, AlertTable, NoDevicesState } from "./components/dashboard";
import { OnboardingOverlay } from "./components/onboarding";
import { useDashboardData } from "./hooks/useDashboardData";
import { useOnboarding } from "./hooks/useOnboarding";

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate();
  const isDev = import.meta.env.DEV;
  const effectiveAuth = isDev || isAuthenticated;

  const { data, isConnected, isLoading, hasDevices, error } = useDashboardData(effectiveAuth);
  const { showOnboarding, onboardingStep, nextStep, skip } = useOnboarding(hasDevices);
  
  const [viewMode, setViewMode] = useState<"simple" | "detailed">("simple");
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);
  const onboardingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !effectiveAuth) {
      navigate("/login", { replace: true });
    }
  }, [authLoading, effectiveAuth, navigate]);

  useEffect(() => {
    if (showOnboarding) {
      setTimeout(() => onboardingRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 100);
    }
  }, [showOnboarding]);

  useEffect(() => {
    if (error) setToast({ message: error, type: "error" });
  }, [error]);

  useEffect(() => { document.title = "Cardea | Dashboard"; }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Shield className="w-10 h-10 text-cyan-500 animate-pulse" />
      </div>
    );
  }

  if (!effectiveAuth) return null;

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
            <NoDevicesState showOnboarding={showOnboarding} onboardingStep={onboardingStep} onNextStep={nextStep} onSkip={skip} onboardingRef={onboardingRef} />
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

      {/* Onboarding overlays */}
      {showOnboarding && hasDevices === false && <OnboardingOverlay step={onboardingStep} onNext={nextStep} onSkip={skip} />}
    </div>
  );
};

export default App;
