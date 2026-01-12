import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "./components/PageHeader";
import { Toast } from "./components/common";
import { AIPersona, SimpleStats, ThreatMap, DetailedLogs, DeviceSetup } from "./components/dashboard";
import { useDashboardData } from "./hooks/useDashboardData";
import { useAuth } from "./lib/useAuth";

const App: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
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
      <PageHeader 
        showViewToggle={hasDevices === true}
        viewMode={viewMode}
        onViewModeChange={() => setViewMode(v => v === "simple" ? "detailed" : "simple")}
      />

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {hasDevices === false && !isLoading ? (
          <DeviceSetup />
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
            
            {/* Detailed Mode: Threat Map + Logs */}
            {viewMode === "detailed" && (
              <div className="space-y-6">
                <ThreatMap alerts={data?.alerts || []} isLoading={isLoading && !data} />
                <DetailedLogs alerts={data?.alerts || []} isLoading={isLoading && !data} />
              </div>
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
