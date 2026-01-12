import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, AlertTriangle, Eye, BarChart3 } from "lucide-react";
import { UserMenu } from "./components/UserMenu";
import { useAuth } from "./lib/useAuth";
import { Toast } from "./components/common";
import { AIPersona, SimpleStats, NoDevicesState, ThreatMap, AlertTimeline, ActionableAlertsPanel } from "./components/dashboard";
import { OnboardingOverlay } from "./components/onboarding";
import { useDashboardData } from "./hooks/useDashboardData";
import { useOnboarding } from "./hooks/useOnboarding";

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate();
  const isDev = import.meta.env.DEV;
  const effectiveAuth = isDev || isAuthenticated;

  const { data, isLoading, hasDevices, devices, error } = useDashboardData(effectiveAuth);
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
        <img src="/cardea-logo.png" alt="Cardea" className="w-12 h-12 animate-pulse" />
      </div>
    );
  }

  if (!effectiveAuth) return null;

  // Compute risk level from data
  const riskScore = data?.risk_score || 0;
  const riskLevel: 'low' | 'medium' | 'high' = riskScore >= 0.7 ? 'high' : riskScore >= 0.4 ? 'medium' : 'low';
  
  // Use actual device status from devices list, not Oracle connection status
  const onlineDevices = devices.filter(d => d.status === 'online');
  const deviceStatus: 'online' | 'offline' = onlineDevices.length > 0 ? 'online' : 'offline';
  const primaryDevice = onlineDevices[0] || devices[0];
  
  const critical = data?.alerts_by_severity?.critical || 0;
  const high = data?.alerts_by_severity?.high || 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40 px-6 py-3">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <img src="/cardea-logo.png" alt="Cardea" className="w-6 h-6" />
            <span className="font-bold text-sm tracking-tight">CARDEA</span>
          </div>
          <div className="flex items-center gap-4">
            {hasDevices && (
              <button onClick={() => setViewMode(v => v === "simple" ? "detailed" : "simple")}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-medium transition-all ${viewMode === "detailed" ? "bg-cyan-900/40 text-cyan-400" : "bg-slate-800/50 text-slate-500 hover:text-slate-300"}`}>
                {viewMode === "detailed" ? <><BarChart3 className="w-3 h-3" />Detailed</> : <><Eye className="w-3 h-3" />Simple</>}
              </button>
            )}
            <div className="flex items-center gap-3 text-[10px] text-slate-500">
              {hasDevices && (critical > 0 || high > 0) && (
                <span className="text-red-500 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{critical + high}</span>
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
            <AIPersona insight={null} isLoading={false} isOffline={true} />
            <NoDevicesState showOnboarding={showOnboarding} onboardingStep={onboardingStep} onNextStep={nextStep} onSkip={skip} onboardingRef={onboardingRef} />
          </>
        ) : hasDevices === true ? (
          <>
            {/* AI Persona - Always shown */}
            <AIPersona 
              insight={data?.ai_insight} 
              isLoading={isLoading && !data} 
              deviceStatus={deviceStatus}
              riskLevel={riskLevel}
            />
            
            {/* Simple Mode: Just status cards */}
            {viewMode === "simple" && (
              <SimpleStats 
                deviceStatus={deviceStatus} 
                riskLevel={riskLevel}
                deviceName={primaryDevice?.name}
              />
            )}
            
            {/* Detailed Mode: Full analytics */}
            {viewMode === "detailed" && (
              <>
                <SimpleStats deviceStatus={deviceStatus} riskLevel={riskLevel} deviceName={primaryDevice?.name} />
                
                {/* Threat Map */}
                <ThreatMap alerts={data?.alerts || []} isLoading={isLoading && !data} />
                
                {/* Two-column layout for Timeline and Actions */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <AlertTimeline alerts={data?.alerts || []} isLoading={isLoading && !data} />
                  <ActionableAlertsPanel alerts={data?.alerts || []} isLoading={isLoading && !data} />
                </div>
              </>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-6 h-6 text-slate-600 animate-spin" />
          </div>
        )}
      </main>

      {/* Onboarding overlays */}
      {showOnboarding && hasDevices === false && <OnboardingOverlay step={onboardingStep} onNext={nextStep} onSkip={skip} />}
    </div>
  );
};

export default App;
