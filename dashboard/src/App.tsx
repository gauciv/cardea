import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, Eye, BarChart3 } from "lucide-react";
import { UserMenu } from "./components/UserMenu";
import { useAuth } from "./lib/useAuth";
import { Toast } from "./components/common";
import { AIPersona, SimpleStats, ThreatMap } from "./components/dashboard";
import { useDashboardData } from "./hooks/useDashboardData";

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const navigate = useNavigate();
  const isDev = import.meta.env.DEV;
  const effectiveAuth = isDev || isAuthenticated;

  const { data, isLoading, hasDevices, devices, error, refetch } = useDashboardData(effectiveAuth);
  
  const [viewMode, setViewMode] = useState<"simple" | "detailed">("simple");
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);
  const [threatResolved, setThreatResolved] = useState(false);

  useEffect(() => {
    if (!authLoading && !effectiveAuth) {
      navigate("/login", { replace: true });
    }
  }, [authLoading, effectiveAuth, navigate]);

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

  // Compute risk level - override to 'low' if threat was resolved
  const riskScore = data?.risk_score || 0;
  const insightRiskLevel = data?.ai_insight?.risk_level;
  const riskLevel: 'low' | 'medium' | 'high' = threatResolved ? 'low' : (insightRiskLevel || (riskScore >= 0.7 ? 'high' : riskScore >= 0.4 ? 'medium' : 'low'));
  
  // Use actual device status from devices list, not Oracle connection status
  const onlineDevices = devices.filter(d => d.status === 'online');
  const deviceStatus: 'online' | 'offline' = onlineDevices.length > 0 ? 'online' : 'offline';
  const primaryDevice = onlineDevices[0] || devices[0];

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
            {user && <UserMenu user={user} />}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {hasDevices === false && !isLoading ? (
          <AIPersona insight={null} isLoading={false} isOffline={true} />
        ) : hasDevices === true ? (
          <>
            {/* AI Persona - Shows everything: message, actions, execution */}
            <AIPersona 
              insight={data?.ai_insight} 
              isLoading={isLoading && !data} 
              deviceStatus={deviceStatus}
              riskLevel={riskLevel}
              onActionComplete={() => refetch()}
              onResolvedChange={setThreatResolved}
            />
            
            {/* Status cards */}
            <SimpleStats 
              deviceStatus={deviceStatus} 
              riskLevel={riskLevel}
              deviceName={primaryDevice?.name}
            />
            
            {/* Detailed Mode: Just Threat Map */}
            {viewMode === "detailed" && (
              <ThreatMap alerts={data?.alerts || []} isLoading={isLoading && !data} />
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-6 h-6 text-slate-600 animate-spin" />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
