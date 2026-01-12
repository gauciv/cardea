import { useEffect, useRef, useState } from 'react';
import { Globe, Shield, AlertTriangle } from 'lucide-react';
import type { Alert } from '../../types';

interface ThreatLocation {
  id: string;
  ip: string;
  lat: number;
  lng: number;
  country: string;
  city?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  alertTitle: string;
}

interface ThreatMapProps {
  alerts: Alert[];
  isLoading?: boolean;
}

// Extract IP from alert data
function extractIP(alert: Alert): string | null {
  const raw = alert.raw_data as Record<string, unknown> | undefined;
  if (!raw) return null;
  
  // Check various possible locations for IP
  const network = raw.network as Record<string, unknown> | undefined;
  if (network?.src_ip && typeof network.src_ip === 'string') return network.src_ip;
  if (raw.src_ip && typeof raw.src_ip === 'string') return raw.src_ip;
  if (raw.dest_ip && typeof raw.dest_ip === 'string') return raw.dest_ip;
  if (raw.ip && typeof raw.ip === 'string') return raw.ip;
  
  // Try to extract from title
  const ipMatch = alert.title.match(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/);
  return ipMatch ? ipMatch[1] : null;
}

// Check if IP is private/local
function isPrivateIP(ip: string): boolean {
  const parts = ip.split('.').map(Number);
  if (parts.length !== 4) return true;
  
  // 10.x.x.x, 172.16-31.x.x, 192.168.x.x, 127.x.x.x
  if (parts[0] === 10) return true;
  if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
  if (parts[0] === 192 && parts[1] === 168) return true;
  if (parts[0] === 127) return true;
  if (parts[0] === 0) return true;
  
  return false;
}

// Simple world map SVG path (simplified continents)
const WorldMapSVG = () => (
  <svg viewBox="0 0 1000 500" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient id="mapGradient" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#1e293b" />
        <stop offset="100%" stopColor="#0f172a" />
      </linearGradient>
    </defs>
    
    {/* Ocean background */}
    <rect width="1000" height="500" fill="url(#mapGradient)" />
    
    {/* Simplified continent outlines */}
    <g fill="#334155" stroke="#475569" strokeWidth="0.5" opacity="0.8">
      {/* North America */}
      <path d="M 50 80 Q 100 60 180 70 Q 220 90 240 130 Q 250 180 220 220 Q 180 250 140 240 Q 100 220 80 180 Q 60 140 50 80 Z" />
      {/* South America */}
      <path d="M 180 280 Q 220 270 240 300 Q 250 350 230 400 Q 200 440 170 420 Q 150 380 160 330 Q 170 290 180 280 Z" />
      {/* Europe */}
      <path d="M 440 80 Q 500 70 540 90 Q 560 120 540 150 Q 500 160 460 140 Q 440 110 440 80 Z" />
      {/* Africa */}
      <path d="M 460 180 Q 520 170 560 200 Q 580 260 560 320 Q 520 370 480 350 Q 450 300 460 240 Q 455 200 460 180 Z" />
      {/* Asia */}
      <path d="M 560 60 Q 700 50 800 80 Q 860 120 850 180 Q 800 220 700 200 Q 620 180 580 140 Q 560 100 560 60 Z" />
      {/* Australia */}
      <path d="M 780 320 Q 840 310 880 340 Q 900 380 870 410 Q 820 420 780 390 Q 760 360 780 320 Z" />
    </g>
    
    {/* Grid lines */}
    <g stroke="#334155" strokeWidth="0.3" opacity="0.3">
      {[...Array(9)].map((_, i) => (
        <line key={`h${i}`} x1="0" y1={(i + 1) * 50} x2="1000" y2={(i + 1) * 50} />
      ))}
      {[...Array(19)].map((_, i) => (
        <line key={`v${i}`} x1={(i + 1) * 50} y1="0" x2={(i + 1) * 50} y2="500" />
      ))}
    </g>
  </svg>
);

// Convert lat/lng to SVG coordinates
function geoToSVG(lat: number, lng: number): { x: number; y: number } {
  const x = ((lng + 180) / 360) * 1000;
  const y = ((90 - lat) / 180) * 500;
  return { x, y };
}

// Your network location (approximate - can be configured)
const HOME_LOCATION = { lat: 14.5995, lng: 120.9842, label: 'Your Network' }; // Manila, PH

export const ThreatMap: React.FC<ThreatMapProps> = ({ alerts, isLoading }) => {
  const [threats, setThreats] = useState<ThreatLocation[]>([]);
  const [geoCache, setGeoCache] = useState<Record<string, { lat: number; lng: number; country: string; city?: string }>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch GeoIP data for alerts
  useEffect(() => {
    const fetchGeoData = async () => {
      const uniqueIPs = new Set<string>();
      
      alerts.forEach(alert => {
        const ip = extractIP(alert);
        if (ip && !isPrivateIP(ip) && !geoCache[ip]) {
          uniqueIPs.add(ip);
        }
      });

      // Fetch geo data for new IPs (using free ip-api.com)
      const newGeoData: typeof geoCache = {};
      
      for (const ip of Array.from(uniqueIPs).slice(0, 10)) { // Limit to 10 to avoid rate limits
        try {
          const res = await fetch(`http://ip-api.com/json/${ip}?fields=status,country,city,lat,lon`);
          const data = await res.json();
          
          if (data.status === 'success') {
            newGeoData[ip] = {
              lat: data.lat,
              lng: data.lon,
              country: data.country,
              city: data.city
            };
          }
        } catch {
          // Skip failed lookups
        }
        
        // Small delay to avoid rate limiting
        await new Promise(r => setTimeout(r, 100));
      }

      if (Object.keys(newGeoData).length > 0) {
        setGeoCache(prev => ({ ...prev, ...newGeoData }));
      }
    };

    if (alerts.length > 0) {
      fetchGeoData();
    }
  }, [alerts, geoCache]);

  // Build threat locations from alerts + geo cache
  useEffect(() => {
    const locations: ThreatLocation[] = [];
    
    alerts.forEach(alert => {
      const ip = extractIP(alert);
      if (!ip || isPrivateIP(ip)) return;
      
      const geo = geoCache[ip];
      if (!geo) return;
      
      locations.push({
        id: `${alert.id}-${ip}`,
        ip,
        lat: geo.lat,
        lng: geo.lng,
        country: geo.country,
        city: geo.city,
        severity: alert.severity,
        timestamp: alert.timestamp,
        alertTitle: alert.title
      });
    });

    setThreats(locations);
  }, [alerts, geoCache]);

  const homePos = geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng);

  // Empty state
  if (!isLoading && threats.length === 0) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Threat Map</h3>
        </div>
        
        <div className="relative aspect-[2/1] bg-slate-950 rounded-lg overflow-hidden">
          <WorldMapSVG />
          
          {/* Home marker */}
          <div 
            className="absolute w-3 h-3 bg-cyan-500 rounded-full animate-pulse"
            style={{ left: `${homePos.x / 10}%`, top: `${homePos.y / 5}%`, transform: 'translate(-50%, -50%)' }}
          >
            <div className="absolute inset-0 bg-cyan-500 rounded-full animate-ping opacity-50" />
          </div>
          
          {/* Empty state overlay */}
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/60">
            <div className="text-center">
              <Shield className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No external threats detected</p>
              <p className="text-[10px] text-slate-600 mt-1">Monitoring for suspicious connections...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-500" />
          <h3 className="text-sm font-medium text-white">Threat Map</h3>
        </div>
        <span className="text-[10px] text-slate-500">
          {threats.length} external {threats.length === 1 ? 'source' : 'sources'}
        </span>
      </div>
      
      <div className="relative aspect-[2/1] bg-slate-950 rounded-lg overflow-hidden" ref={containerRef}>
        <WorldMapSVG />
        
        {/* SVG overlay for lines and markers */}
        <svg 
          viewBox="0 0 1000 500" 
          className="absolute inset-0 w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Attack lines */}
          {threats.map((threat, i) => {
            const pos = geoToSVG(threat.lat, threat.lng);
            const home = geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng);
            const color = threat.severity === 'critical' ? '#ef4444' : 
                         threat.severity === 'high' ? '#f97316' : 
                         threat.severity === 'medium' ? '#eab308' : '#22d3ee';
            
            return (
              <g key={threat.id}>
                {/* Animated line */}
                <line
                  x1={pos.x} y1={pos.y}
                  x2={home.x} y2={home.y}
                  stroke={color}
                  strokeWidth="1"
                  opacity="0.6"
                  strokeDasharray="5,5"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="10"
                    to="0"
                    dur="1s"
                    repeatCount="indefinite"
                  />
                </line>
                
                {/* Source marker */}
                <circle
                  cx={pos.x} cy={pos.y}
                  r="6"
                  fill={color}
                  opacity="0.8"
                >
                  <animate
                    attributeName="r"
                    values="4;8;4"
                    dur="2s"
                    repeatCount="indefinite"
                    begin={`${i * 0.3}s`}
                  />
                  <animate
                    attributeName="opacity"
                    values="0.8;0.4;0.8"
                    dur="2s"
                    repeatCount="indefinite"
                    begin={`${i * 0.3}s`}
                  />
                </circle>
              </g>
            );
          })}
          
          {/* Home marker */}
          <g>
            <circle
              cx={geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng).x}
              cy={geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng).y}
              r="8"
              fill="#22d3ee"
              opacity="0.3"
            >
              <animate attributeName="r" values="8;16;8" dur="2s" repeatCount="indefinite" />
            </circle>
            <circle
              cx={geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng).x}
              cy={geoToSVG(HOME_LOCATION.lat, HOME_LOCATION.lng).y}
              r="5"
              fill="#22d3ee"
            />
          </g>
        </svg>
        
        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex items-center gap-3 text-[9px] text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500" /> Your Network
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Critical
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-500" /> High
          </span>
        </div>
      </div>
      
      {/* Threat list */}
      {threats.length > 0 && (
        <div className="mt-4 space-y-2 max-h-32 overflow-y-auto">
          {threats.slice(0, 5).map(threat => (
            <div key={threat.id} className="flex items-center justify-between text-xs bg-slate-800/50 rounded px-3 py-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className={`w-3 h-3 ${
                  threat.severity === 'critical' ? 'text-red-500' :
                  threat.severity === 'high' ? 'text-orange-500' :
                  threat.severity === 'medium' ? 'text-yellow-500' : 'text-cyan-500'
                }`} />
                <span className="text-slate-300 font-mono">{threat.ip}</span>
              </div>
              <span className="text-slate-500">{threat.country}{threat.city ? `, ${threat.city}` : ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
