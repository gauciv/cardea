import { useMemo } from 'react';
import { 
  Shield, Activity, TrendingUp, TrendingDown, Minus,
  Globe, Server, AlertTriangle, Clock,
  Wifi, Database, Lock, Eye
} from 'lucide-react';
import type { Alert } from '../types';

interface ThreatOverviewProps {
  alerts: Alert[];
  severityStats: Record<string, number>;
  isConnected: boolean;
}

// Source type icons
const sourceIcons: Record<string, React.ElementType> = {
  suricata: Shield,
  zeek: Eye,
  kitnet: Activity,
  network: Globe,
  endpoint: Server,
  default: Wifi,
};

// Alert type to human-readable mapping
const alertTypeLabels: Record<string, string> = {
  network_anomaly: 'Network Anomaly',
  intrusion_detection: 'Intrusion Attempt',
  malware_detection: 'Malware Detected',
  suspicious_behavior: 'Suspicious Behavior',
  data_exfiltration: 'Data Exfiltration',
  unauthorized_access: 'Unauthorized Access',
  port_scan: 'Port Scanning',
  dos_attack: 'DoS Attack',
};

export const ThreatOverview: React.FC<ThreatOverviewProps> = ({ 
  alerts, 
  severityStats, 
  isConnected 
}) => {
  // FIX: Create a strictly typed local reference to prevent 'never' inference errors
  const safeSeverityStats = (severityStats || {}) as Record<string, number>;

  // Calculate stats from alerts
  const stats = useMemo(() => {
    if (!alerts || alerts.length === 0) {
      return {
        bySource: {} as Record<string, number>,
        byType: {} as Record<string, number>,
        recentTimeline: [] as { time: string; count: number; severity: string }[],
        topSources: [] as { source: string; count: number; percentage: number }[],
        topTypes: [] as { type: string; count: number }[],
        averageThreatScore: 0,
        trend: 'stable' as 'up' | 'down' | 'stable',
      };
    }

    // Count by source
    const bySource: Record<string, number> = {};
    const byType: Record<string, number> = {};
    let totalThreatScore = 0;
    let scoreCount = 0;

    alerts.forEach((alert) => {
      const source = alert.source?.toLowerCase() || 'unknown';
      bySource[source] = (bySource[source] || 0) + 1;
      
      const type = alert.alert_type || 'unknown';
      byType[type] = (byType[type] || 0) + 1;

      if (alert.threat_score !== undefined && alert.threat_score !== null) {
        totalThreatScore += alert.threat_score;
        scoreCount++;
      }
    });

    // Calculate top sources with percentages
    const total = alerts.length;
    const topSources = Object.entries(bySource)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 4)
      .map(([source, count]) => ({
        source,
        count,
        percentage: Math.round((count / total) * 100),
      }));

    // Calculate top alert types
    const topTypes = Object.entries(byType)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([type, count]) => ({ type, count }));

    // Calculate hourly timeline (last 6 hours)
    const now = new Date();
    const recentTimeline: { time: string; count: number; severity: string }[] = [];
    for (let i = 5; i >= 0; i--) {
      const hourStart = new Date(now);
      hourStart.setHours(hourStart.getHours() - i, 0, 0, 0);
      const hourEnd = new Date(hourStart);
      hourEnd.setHours(hourEnd.getHours() + 1);
      
      const hourAlerts = alerts.filter((a) => {
        const alertTime = new Date(a.timestamp);
        return alertTime >= hourStart && alertTime < hourEnd;
      });

      const highestSeverity = hourAlerts.reduce((acc, a) => {
        const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        const current = severityOrder[a.severity] || 0;
        const best = severityOrder[acc as keyof typeof severityOrder] || 0;
        return current > best ? a.severity : acc;
      }, 'low');

      recentTimeline.push({
        time: hourStart.toLocaleTimeString([], { hour: '2-digit', hour12: false }),
        count: hourAlerts.length,
        severity: highestSeverity,
      });
    }

    // Simple trend detection
    const firstHalf = recentTimeline.slice(0, 3).reduce((a, b) => a + b.count, 0);
    const secondHalf = recentTimeline.slice(3).reduce((a, b) => a + b.count, 0);
    const trend: 'up' | 'down' | 'stable' = 
      secondHalf > firstHalf * 1.2 ? 'up' : 
      secondHalf < firstHalf * 0.8 ? 'down' : 'stable';

    return {
      bySource,
      byType,
      recentTimeline,
      topSources,
      topTypes,
      averageThreatScore: scoreCount > 0 ? totalThreatScore / scoreCount : 0,
      trend,
    };
  }, [alerts]);

  const TrendIcon = stats.trend === 'up' ? TrendingUp : stats.trend === 'down' ? TrendingDown : Minus;
  const trendColor = stats.trend === 'up' ? 'text-red-400' : stats.trend === 'down' ? 'text-green-400' : 'text-slate-500';
  const trendLabel = stats.trend === 'up' ? 'Increasing' : stats.trend === 'down' ? 'Decreasing' : 'Stable';

  // Empty/offline state
  if (!isConnected) {
    return (
      <div className="h-full w-full min-h-112.5 bg-slate-900/40 rounded-xl border border-slate-900 flex items-center justify-center">
        <div className="text-center px-8">
          <div className="p-4 bg-slate-800/50 rounded-2xl inline-block mb-4">
            <Shield className="w-12 h-12 text-slate-600" />
          </div>
          <h3 className="text-lg font-medium text-slate-400 mb-2">Awaiting Connection</h3>
          <p className="text-sm text-slate-600 max-w-xs">
            Connect to the Oracle backend to view threat intelligence overview
          </p>
        </div>
      </div>
    );
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="h-full w-full min-h-112.5 bg-slate-900/40 rounded-xl border border-slate-900 flex items-center justify-center">
        <div className="text-center px-8">
          <div className="p-4 bg-green-950/30 rounded-2xl inline-block mb-4">
            <Shield className="w-12 h-12 text-green-500" />
          </div>
          <h3 className="text-lg font-medium text-green-400 mb-2">All Clear</h3>
          <p className="text-sm text-slate-500 max-w-xs">
            No active threats detected. Your network appears secure.
          </p>
        </div>
      </div>
    );
  }

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-cyan-500',
  };

  return (
    <div className="h-full w-full min-h-112.5 bg-slate-900/40 rounded-xl border border-slate-900 overflow-hidden">
      <div className="p-6 space-y-6">
        {/* Header with trend */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-500" />
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
              Threat Intelligence Overview
            </h3>
          </div>
          <div className={`flex items-center gap-1.5 text-[10px] font-bold uppercase ${trendColor}`}>
            <TrendIcon className="w-3 h-3" />
            {trendLabel}
          </div>
        </div>

        {/* Activity Timeline */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase tracking-wider">
            <Clock className="w-3 h-3" />
            <span>6-Hour Activity</span>
          </div>
          <div className="flex items-end gap-1 h-16">
            {stats.recentTimeline.map((hour, i) => {
              const maxCount = Math.max(...stats.recentTimeline.map(h => h.count), 1);
              const height = hour.count > 0 ? Math.max((hour.count / maxCount) * 100, 10) : 5;
              const barColor = severityColors[hour.severity] || 'bg-slate-700';
              
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div 
                    className={`w-full rounded-t transition-all duration-500 ${hour.count > 0 ? barColor : 'bg-slate-800'}`}
                    style={{ height: `${height}%` }}
                    title={`${hour.time}: ${hour.count} alerts`}
                  />
                  <span className="text-[8px] text-slate-600 font-mono">{hour.time}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Two Column Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Sources Breakdown */}
          <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800/50">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-3 h-3 text-purple-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Alert Sources
              </span>
            </div>
            <div className="space-y-2">
              {stats.topSources.map(({ source, count, percentage }) => {
                const Icon = sourceIcons[source] || sourceIcons.default;
                return (
                  <div key={source} className="flex items-center gap-2">
                    <Icon className="w-3 h-3 text-slate-500" />
                    <span className="text-[10px] text-slate-400 uppercase flex-1 truncate">
                      {source}
                    </span>
                    <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-purple-500 rounded-full transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono w-8 text-right">
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Alert Types */}
          <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800/50">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-3 h-3 text-orange-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Threat Categories
              </span>
            </div>
            <div className="space-y-2">
              {stats.topTypes.slice(0, 4).map(({ type, count }) => (
                <div key={type} className="flex items-center justify-between gap-2">
                  <span className="text-[10px] text-slate-400 truncate">
                    {alertTypeLabels[type] || type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[10px] text-orange-400 font-bold tabular-nums">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Severity Distribution */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase tracking-wider">
            <Lock className="w-3 h-3" />
            <span>Severity Distribution</span>
          </div>
          <div className="flex gap-1 h-3 rounded-full overflow-hidden bg-slate-800">
            {/* FIX: Use safeSeverityStats */}
            {Object.entries(safeSeverityStats).map(([severity, count]) => {
              const total = Object.values(safeSeverityStats).reduce((a, b) => a + b, 0);
              const percentage = total > 0 ? (count / total) * 100 : 0;
              if (percentage === 0) return null;
              return (
                <div
                  key={severity}
                  className={`${severityColors[severity]} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                  title={`${severity}: ${count} (${percentage.toFixed(1)}%)`}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-[8px] text-slate-600 uppercase">
            {/* FIX: Use safeSeverityStats */}
            {Object.entries(safeSeverityStats).map(([severity, count]) => (
              <span key={severity} className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${severityColors[severity]}`} />
                {severity}: {count}
              </span>
            ))}
          </div>
        </div>

        {/* Average Threat Score */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
            Avg Threat Score
          </span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all ${
                  stats.averageThreatScore >= 0.7 ? 'bg-red-500' :
                  stats.averageThreatScore >= 0.4 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${stats.averageThreatScore * 100}%` }}
              />
            </div>
            <span className={`text-sm font-bold tabular-nums ${
              stats.averageThreatScore >= 0.7 ? 'text-red-400' :
              stats.averageThreatScore >= 0.4 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {(stats.averageThreatScore * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};