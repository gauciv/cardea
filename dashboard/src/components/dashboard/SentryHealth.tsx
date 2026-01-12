import { useState, useEffect } from 'react';
import { Server, Cpu, HardDrive, Activity, WifiOff, Thermometer, Clock, Zap, Shield } from 'lucide-react';

interface SentryHealthData {
  hardware_id: string;
  version: string;
  cpu_temp: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
  uptime: string | null;
}

interface LocalStats {
  anomaly_score: number;
  packets_sec: number;
  escalations: number;
}

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  details?: string;
}

interface SentryHealthProps {
  sentryUrl?: string;
  isDeviceOnline: boolean;
}

// Progress bar component
const ProgressBar: React.FC<{ value: number; max?: number; color?: string; size?: 'sm' | 'md' }> = ({ 
  value, 
  max = 100, 
  color = 'cyan',
  size = 'sm'
}) => {
  const percent = Math.min((value / max) * 100, 100);
  const colorClasses = {
    cyan: 'bg-cyan-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500'
  };
  
  // Dynamic color based on value
  let barColor = colorClasses[color as keyof typeof colorClasses] || colorClasses.cyan;
  if (color === 'auto') {
    if (percent > 80) barColor = colorClasses.red;
    else if (percent > 60) barColor = colorClasses.yellow;
    else barColor = colorClasses.green;
  }
  
  return (
    <div className={`w-full bg-slate-800 rounded-full overflow-hidden ${size === 'sm' ? 'h-1.5' : 'h-2'}`}>
      <div 
        className={`h-full ${barColor} transition-all duration-500`}
        style={{ width: `${percent}%` }}
      />
    </div>
  );
};

export const SentryHealth: React.FC<SentryHealthProps> = ({ 
  sentryUrl = 'http://localhost:8001',
  isDeviceOnline 
}) => {
  const [health, setHealth] = useState<SentryHealthData | null>(null);
  const [stats, setStats] = useState<LocalStats | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      if (!isDeviceOnline) {
        setIsLoading(false);
        return;
      }

      try {
        // Fetch device info
        const [deviceRes, statsRes, kitnetRes] = await Promise.allSettled([
          fetch(`${sentryUrl}/api/device-info`),
          fetch(`${sentryUrl}/api/local-stats`),
          fetch(`${sentryUrl}/api/kitnet-stats`)
        ]);

        if (deviceRes.status === 'fulfilled' && deviceRes.value.ok) {
          setHealth(await deviceRes.value.json());
        }

        if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
          setStats(await statsRes.value.json());
        }

        // Build service status
        const serviceList: ServiceStatus[] = [
          { name: 'Bridge', status: 'healthy', details: 'API responding' },
          { name: 'Zeek', status: 'unknown' },
          { name: 'Suricata', status: 'unknown' },
          { name: 'KitNET', status: kitnetRes.status === 'fulfilled' && kitnetRes.value.ok ? 'healthy' : 'unknown' }
        ];
        setServices(serviceList);
      } catch {
        // Cannot reach Sentry
      } finally {
        setIsLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [sentryUrl, isDeviceOnline]);

  // Offline state
  if (!isDeviceOnline) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-slate-500" />
          <h3 className="text-sm font-medium text-white">Sentry Health</h3>
        </div>
        
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <WifiOff className="w-10 h-10 text-slate-700 mb-3" />
          <p className="text-sm text-slate-500">Sentry device offline</p>
          <p className="text-xs text-slate-600 mt-1">Health metrics unavailable</p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading && !health) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Sentry Health</h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-12 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Sentry Health</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-[10px] text-green-400">Online</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* CPU Temp */}
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Thermometer className="w-4 h-4 text-orange-400" />
            <span className="text-[10px] text-slate-500 uppercase">CPU Temp</span>
          </div>
          {health?.cpu_temp !== null ? (
            <>
              <p className="text-lg font-semibold text-white">{health?.cpu_temp}°C</p>
              <ProgressBar 
                value={health?.cpu_temp || 0} 
                max={85} 
                color={health?.cpu_temp && health.cpu_temp > 70 ? 'red' : health?.cpu_temp && health.cpu_temp > 55 ? 'yellow' : 'green'} 
              />
            </>
          ) : (
            <p className="text-sm text-slate-600">N/A</p>
          )}
        </div>

        {/* Memory */}
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span className="text-[10px] text-slate-500 uppercase">Memory</span>
          </div>
          {health?.memory_percent !== null ? (
            <>
              <p className="text-lg font-semibold text-white">{health?.memory_percent}%</p>
              <ProgressBar value={health?.memory_percent || 0} color="auto" />
            </>
          ) : (
            <p className="text-sm text-slate-600">N/A</p>
          )}
        </div>

        {/* Disk */}
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <HardDrive className="w-4 h-4 text-blue-400" />
            <span className="text-[10px] text-slate-500 uppercase">Disk</span>
          </div>
          {health?.disk_percent !== null ? (
            <>
              <p className="text-lg font-semibold text-white">{health?.disk_percent}%</p>
              <ProgressBar value={health?.disk_percent || 0} color="auto" />
            </>
          ) : (
            <p className="text-sm text-slate-600">N/A</p>
          )}
        </div>

        {/* Uptime */}
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] text-slate-500 uppercase">Uptime</span>
          </div>
          <p className="text-lg font-semibold text-white">{health?.uptime || 'N/A'}</p>
        </div>
      </div>

      {/* Live Stats */}
      {stats && (
        <div className="bg-slate-800/30 rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-slate-400">
                  <span className="text-white font-mono">{stats.packets_sec}</span> pkt/s
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-xs text-slate-400">
                  Anomaly: <span className="text-white font-mono">{(stats.anomaly_score * 100).toFixed(1)}%</span>
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-400" />
              <span className="text-xs text-slate-400">
                <span className="text-white font-mono">{stats.escalations}</span> escalated
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Services Status */}
      <div>
        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Services</p>
        <div className="flex flex-wrap gap-2">
          {services.map(service => (
            <div 
              key={service.name}
              className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] ${
                service.status === 'healthy' 
                  ? 'bg-green-500/10 text-green-400' 
                  : service.status === 'unhealthy'
                  ? 'bg-red-500/10 text-red-400'
                  : 'bg-slate-700/50 text-slate-500'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                service.status === 'healthy' ? 'bg-green-500' :
                service.status === 'unhealthy' ? 'bg-red-500' : 'bg-slate-500'
              }`} />
              {service.name}
            </div>
          ))}
        </div>
      </div>

      {/* Device ID */}
      {health?.hardware_id && (
        <div className="mt-4 pt-3 border-t border-slate-800">
          <p className="text-[10px] text-slate-600">
            Device: <span className="font-mono text-slate-500">{health.hardware_id}</span>
            {health.version && <span className="ml-2">v{health.version}</span>}
          </p>
        </div>
      )}
    </div>
  );
};
