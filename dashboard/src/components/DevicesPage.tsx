import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Server, Plus, Wifi, WifiOff, 
  Monitor, Cpu, RefreshCw, Trash2, Check, ArrowLeft, Copy, CheckCircle
} from 'lucide-react';
import type { Device } from '../types';

// Extend the Device type to include the database field patched in the backend
interface ExtendedDevice extends Device {
  friendly_name: string;
}

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || "http://localhost:8000";

export const DevicesPage = () => {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<ExtendedDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [claimToken, setClaimToken] = useState("");
  const [claimName, setClaimName] = useState("");
  const [isClaiming, setIsClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newDeviceKey, setNewDeviceKey] = useState<string | null>(null);
  const [keyCopied, setKeyCopied] = useState(false);

  const fetchDevices = useCallback(async () => {
    const token = localStorage.getItem('token');
    
    // Prevent flicker/redirect loop: If token is missing, just stop loading.
    // Main app router should handle the primary redirect to login.
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const res = await axios.get<ExtendedDevice[]>(`${ORACLE_URL}/api/devices/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDevices(res.data);
    } catch (err) {
      console.error("Failed to fetch devices", err);
    } finally {
      setIsLoading(false);
    }
  }, [ORACLE_URL]);

  useEffect(() => {
    let isMounted = true;

    if (isMounted) {
      fetchDevices();
    }

    // Refresh interval: 30s to keep Azure warm without hammering the API
    const interval = setInterval(() => {
      if (isMounted) fetchDevices();
    }, 30000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fetchDevices]);

  const handleClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsClaiming(true);
    setError(null);

    try {
      console.log('🔑 Claiming device with code:', claimToken);
      const token = localStorage.getItem('token');
      const res = await axios.post(`${ORACLE_URL}/api/devices/claim`, {
        claim_token: claimToken,
        friendly_name: claimName || `Sentry Device`
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      console.log('✅ Device claimed successfully!', res.data);

      if (res.data.api_key) {
        setNewDeviceKey(res.data.api_key as string);
        setClaimToken(""); 
        setClaimName("");
        
        // Immediately refresh device list
        console.log('📋 Refreshing device list...');
        await fetchDevices();
        console.log('✅ Device list refreshed');
      } else {
        setError("Device claimed, but no API key returned.");
      }
    } catch (err: unknown) {
        console.error('❌ Failed to claim device:', err);
        if (axios.isAxiosError(err)) {
            setError(err.response?.data?.detail || "Failed to claim device.");
        } else {
            setError("An unexpected error occurred.");
        }
    } finally {
      setIsClaiming(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="p-6 max-w-7xl mx-auto space-y-8">
        
        {/* HEADER AREA */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 border-b border-slate-800 pb-8">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white"
              title="Back to Dashboard"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Server className="w-8 h-8 text-cyan-500" />
                Sentry Devices
              </h1>
              <p className="text-slate-400 mt-1">Manage your physical security probes</p>
            </div>
          </div>
          
          <button 
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-2.5 rounded-lg font-bold transition-all shadow-lg shadow-cyan-900/20"
          >
            <Plus className="w-5 h-5" />
            Add Device
          </button>
        </div>

        {/* DEVICE GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            [...Array(3)].map((_, i) => (
              <div key={i} className="h-48 bg-slate-900/50 rounded-xl animate-pulse border border-slate-800" />
            ))
          ) : devices.length === 0 ? (
            <div className="col-span-full py-16 text-center bg-gradient-to-br from-slate-900/40 to-cyan-950/20 rounded-2xl border border-slate-800 border-dashed relative overflow-hidden">
              {/* Background decoration */}
              <div className="absolute inset-0 opacity-5">
                <div className="absolute top-10 left-10 w-32 h-32 border border-cyan-500 rounded-full" />
                <div className="absolute bottom-10 right-10 w-48 h-48 border border-cyan-500 rounded-full" />
              </div>
              
              <div className="relative z-10">
                <div className="w-24 h-24 bg-gradient-to-br from-cyan-500/20 to-slate-800/50 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-cyan-500/20 shadow-lg shadow-cyan-500/10">
                  <Monitor className="w-12 h-12 text-cyan-400" />
                </div>
                
                <h3 className="text-3xl font-bold text-white mb-3">Connect Your First Sentry</h3>
                <p className="text-slate-400 mt-2 max-w-lg mx-auto leading-relaxed">
                  Your Cardea Sentry device is waiting to be paired. Enter the <span className="text-cyan-400 font-semibold">6-character pairing code</span> displayed on your Sentry's local portal to establish a secure connection.
                </p>
                
                {/* Instructions */}
                <div className="mt-8 max-w-md mx-auto bg-slate-900/60 rounded-xl p-6 border border-slate-800 text-left">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">How to Connect</h4>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs font-bold shrink-0">1</span>
                      <p className="text-sm text-slate-300">Power on your Sentry device and connect it to your network</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs font-bold shrink-0">2</span>
                      <p className="text-sm text-slate-300">Access the Sentry portal at <code className="text-cyan-400 bg-slate-800 px-1.5 py-0.5 rounded text-xs">http://sentry.local:8001</code></p>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs font-bold shrink-0">3</span>
                      <p className="text-sm text-slate-300">Copy the pairing code displayed on your Sentry device and click below</p>
                    </div>
                  </div>
                </div>
                
                <button 
                  onClick={() => setShowAddModal(true)}
                  className="mt-8 px-10 py-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-cyan-900/30 hover:shadow-cyan-900/50 hover:scale-105 flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-5 h-5" />
                  Enter Pairing Code
                </button>
              </div>
            </div>
          ) : (
            devices.map(device => (
              <div key={device.id} className="bg-slate-900/40 border border-slate-800 rounded-xl p-6 hover:border-cyan-500/30 transition-all group">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-lg ${device.status === 'online' ? 'bg-green-500/10 text-green-400' : 'bg-slate-800 text-slate-500'}`}>
                      <Cpu className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-100">{device.friendly_name}</h3>
                      <p className="text-xs text-slate-500 font-mono">{device.hardware_id}</p>
                    </div>
                  </div>
                  <div className={`flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                    device.status === 'online' 
                      ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    {device.status === 'online' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                    {device.status}
                  </div>
                </div>
                
                <div className="space-y-2.5 text-sm text-slate-400">
                  <div className="flex justify-between">
                    <span>IP Address:</span>
                    <span className="font-mono text-slate-300">{device.ip_address || "Pending..."}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Last Seen:</span>
                    <span className="text-slate-300">
                      {device.last_seen ? new Date(device.last_seen).toLocaleTimeString() : "Never"}
                    </span>
                  </div>
                  <div className="flex justify-between border-t border-slate-800/50 pt-2.5 mt-2.5">
                    <span>Firmware:</span>
                    <span className="font-mono text-cyan-600">{device.version}</span>
                  </div>
                </div>

                <div className="mt-6 flex justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="p-2 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-all" title="Remove">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <button className="p-2 bg-slate-800 hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-400 rounded-lg transition-all" title="Update">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* CLAIM MODAL */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
              {newDeviceKey ? (
                <div className="p-8 text-center space-y-6">
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-20 h-20 bg-green-500/20 rounded-full animate-ping" />
                    </div>
                    <div className="relative w-20 h-20 bg-gradient-to-br from-green-500/30 to-green-600/20 rounded-full flex items-center justify-center mx-auto border-2 border-green-500/40">
                      <Check className="w-10 h-10 text-green-400" />
                    </div>
                  </div>
                  
                  <div>
                    <h2 className="text-2xl font-bold text-white">Almost There!</h2>
                    <p className="text-slate-400 text-sm mt-2">Copy the API key below and paste it into your Sentry device to complete the connection.</p>
                  </div>
                  
                  <div className={`bg-slate-950/80 border-2 border-dashed rounded-xl p-5 relative text-left transition-all duration-300 ${keyCopied ? 'border-green-500/50 bg-green-950/20' : 'border-cyan-500/30'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <p className={`text-[10px] uppercase font-bold tracking-wider transition-colors ${keyCopied ? 'text-green-400' : 'text-cyan-500'}`}>
                        {keyCopied ? '✓ Copied to Clipboard!' : 'Device API Key'}
                      </p>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(newDeviceKey);
                          setKeyCopied(true);
                          setTimeout(() => setKeyCopied(false), 3000);
                        }}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-white text-xs font-bold transition-all ${
                          keyCopied 
                            ? 'bg-green-600 hover:bg-green-500' 
                            : 'bg-cyan-600 hover:bg-cyan-500'
                        }`}
                      >
                        {keyCopied ? (
                          <>
                            <CheckCircle className="w-3 h-3" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <code className={`font-mono text-sm break-all leading-relaxed transition-colors ${keyCopied ? 'text-green-400' : 'text-cyan-400'}`}>{newDeviceKey}</code>
                  </div>
                  
                  <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-left">
                    <p className="text-xs text-slate-500 mb-2 font-medium">Next Step:</p>
                    <p className="text-sm text-slate-300">Go to your Sentry device portal, paste this key in the "Device API Key" field, and click <span className="text-cyan-400 font-semibold">"Connect Sentry"</span></p>
                  </div>
                  
                  <button 
                    onClick={() => { setShowAddModal(false); setNewDeviceKey(null); setKeyCopied(false); }}
                    className="w-full py-3.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold transition-colors"
                  >
                    Done
                  </button>
                </div>
              ) : (
                <div className="p-8">
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h2 className="text-xl font-bold text-white">Pair Your Sentry Device</h2>
                      <p className="text-sm text-slate-500 mt-1">Enter the code shown on your Sentry's screen</p>
                    </div>
                    <button onClick={() => setShowAddModal(false)} className="text-slate-500 hover:text-white p-1 hover:bg-slate-800 rounded">✕</button>
                  </div>
                  
                  <form onSubmit={handleClaim} className="space-y-5">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Pairing Code</label>
                      <input 
                        type="text" 
                        placeholder="XXX-XXX"
                        className="w-full bg-slate-950 border-2 border-slate-700 rounded-xl p-4 text-center text-3xl font-mono tracking-[0.4em] text-white focus:border-cyan-500 outline-none transition-colors placeholder:text-slate-700 placeholder:tracking-[0.4em]"
                        value={claimToken}
                        onChange={e => {
                          let val = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
                          // Auto-insert hyphen after 3 characters
                          if (val.length === 3 && !val.includes('-')) {
                            val = val + '-';
                          }
                          setClaimToken(val);
                        }}
                        maxLength={7}
                        required
                        autoFocus
                      />
                      <p className="text-xs text-slate-600 text-center mt-2">Find this code on your Sentry device's setup screen</p>
                    </div>
                    
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Device Name <span className="text-slate-600 font-normal">(optional)</span></label>
                      <input 
                        type="text" 
                        placeholder="e.g., Office Network, Home Lab"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-cyan-500 outline-none transition-colors placeholder:text-slate-600"
                        value={claimName}
                        onChange={e => setClaimName(e.target.value)}
                      />
                    </div>
                    
                    {error && (
                      <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center shrink-0 mt-0.5">
                          <span className="text-red-400 text-xs">!</span>
                        </div>
                        <div>
                          <p className="text-red-400 text-sm font-medium">Pairing Failed</p>
                          <p className="text-red-400/70 text-xs mt-1">{error}</p>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex gap-3 pt-2">
                      <button type="button" onClick={() => setShowAddModal(false)} className="flex-1 py-3.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-bold transition-colors">Cancel</button>
                      <button 
                        type="submit" 
                        disabled={isClaiming || claimToken.length < 7}
                        className="flex-1 py-3.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-bold flex items-center justify-center gap-2 transition-all"
                      >
                        {isClaiming ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          "Pair Device"
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};