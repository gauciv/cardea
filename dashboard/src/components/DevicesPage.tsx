import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Server, Plus, Wifi, WifiOff, 
  Monitor, Cpu, RefreshCw, Trash2, Key, Check
} from 'lucide-react';
// FIX: Added 'type' keyword here to satisfy verbatimModuleSyntax
import type { Device } from '../types';

// Environment config
const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || "http://localhost:8000";

export const DevicesPage = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [claimToken, setClaimToken] = useState("");
  const [claimName, setClaimName] = useState("");
  const [isClaiming, setIsClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // New Device Credentials (shown only once)
  const [newDeviceKey, setNewDeviceKey] = useState<string | null>(null);

  // Fetch devices
  const fetchDevices = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get<Device[]>(`${ORACLE_URL}/api/devices/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDevices(res.data);
    } catch (err) {
      console.error("Failed to fetch devices", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  // Handle Claiming
  const handleClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsClaiming(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      // 1. Claim the device
      const res = await axios.post(`${ORACLE_URL}/api/devices/claim`, {
        claim_token: claimToken,
        friendly_name: claimName || `Sentry Device`
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      // 2. Show the API Key to the user
      if (res.data.api_key) {
        setNewDeviceKey(res.data.api_key as string);
        setClaimToken(""); 
        setClaimName("");
        fetchDevices();
      } else {
        setError("Device claimed, but no API key returned. Check backend logs.");
      }

    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Failed to claim device. Check the code and try again.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setIsClaiming(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <Server className="w-8 h-8 text-cyan-500" />
            Sentry Devices
          </h1>
          <p className="text-slate-400 mt-1">Manage your physical security probes</p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg font-bold transition-all shadow-lg shadow-cyan-900/20"
        >
          <Plus className="w-5 h-5" />
          Add Device
        </button>
      </div>

      {/* Device Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          [...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-slate-900/50 rounded-xl animate-pulse border border-slate-800" />
          ))
        ) : devices.length === 0 ? (
          <div className="col-span-full py-20 text-center bg-slate-900/30 rounded-2xl border border-slate-800 border-dashed">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <Monitor className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-xl font-bold text-slate-300">No Devices Connected</h3>
            <p className="text-slate-500 mt-2 max-w-md mx-auto">
              Get a Cardea Sentry device to start monitoring your physical network traffic.
            </p>
            <button 
              onClick={() => setShowAddModal(true)}
              className="mt-6 text-cyan-400 hover:text-cyan-300 font-bold text-sm"
            >
              + Link a Device Now
            </button>
          </div>
        ) : (
          devices.map(device => (
            <div key={device.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 hover:border-cyan-500/30 transition-all group relative overflow-hidden">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${device.status === 'online' ? 'bg-green-500/10 text-green-400' : 'bg-slate-800 text-slate-500'}`}>
                    <Cpu className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200">{device.name}</h3>
                    <p className="text-xs text-slate-500 font-mono">{device.hardware_id}</p>
                  </div>
                </div>
                <div className={`flex items-center gap-1.5 text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider ${
                  device.status === 'online' 
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {device.status === 'online' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                  {device.status}
                </div>
              </div>
              
              <div className="space-y-2 text-sm text-slate-400">
                <div className="flex justify-between">
                  <span>IP Address:</span>
                  <span className="font-mono text-slate-300">{device.ip_address || "Unknown"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Last Seen:</span>
                  <span className="text-slate-300">
                    {device.last_seen ? new Date(device.last_seen).toLocaleTimeString() : "Never"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Version:</span>
                  <span className="font-mono text-cyan-600">{device.version}</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800/50 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-2 hover:bg-red-500/10 text-slate-600 hover:text-red-400 rounded transition-colors" title="Remove Device">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button className="p-2 hover:bg-cyan-500/10 text-slate-600 hover:text-cyan-400 rounded transition-colors" title="Configure">
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Claim Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            
            {newDeviceKey ? (
              // SUCCESS STATE - SHOW API KEY
              <div className="p-8 text-center space-y-6">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto text-green-400">
                  <Check className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold text-white">Device Linked!</h2>
                <p className="text-slate-400 text-sm">
                  Copy this API Key and paste it into your Sentry device to complete the setup.
                </p>
                
                <div className="bg-black/50 border border-slate-700 rounded-lg p-4 relative group text-left">
                  <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">Device API Key</p>
                  <code className="text-cyan-400 font-mono text-sm break-all">{newDeviceKey}</code>
                  <button 
                    onClick={() => navigator.clipboard.writeText(newDeviceKey)}
                    className="absolute top-2 right-2 p-2 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 transition-colors"
                    title="Copy to Clipboard"
                  >
                    <Key className="w-4 h-4" />
                  </button>
                </div>

                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded p-3 text-xs text-yellow-200/80 text-left">
                  ⚠️ This key will only be shown once. If you lose it, you will need to reset the device.
                </div>

                <button 
                  onClick={() => {
                    setShowAddModal(false);
                    setNewDeviceKey(null);
                  }}
                  className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold transition-colors"
                >
                  Close
                </button>
              </div>
            ) : (
              // INPUT STATE
              <div className="p-8">
                <h2 className="text-xl font-bold text-white mb-6">Add New Sentry</h2>
                <form onSubmit={handleClaim} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Claim Token</label>
                    <input 
                      type="text" 
                      placeholder="000-000"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-center text-2xl font-mono tracking-widest text-white focus:border-cyan-500 outline-none"
                      value={claimToken}
                      onChange={e => setClaimToken(e.target.value.toUpperCase())}
                      maxLength={7}
                      required
                    />
                    <p className="text-xs text-slate-500 mt-2">Enter the 6-digit code shown on your device screen.</p>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Device Name</label>
                    <input 
                      type="text" 
                      placeholder="e.g. Home Office Sentry"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-cyan-500 outline-none"
                      value={claimName}
                      onChange={e => setClaimName(e.target.value)}
                    />
                  </div>

                  {error && (
                    <div className="p-3 bg-red-500/20 border border-red-500/50 rounded text-red-200 text-sm">
                      {error}
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                    <button 
                      type="button"
                      onClick={() => setShowAddModal(false)}
                      className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-bold transition-colors"
                    >
                      Cancel
                    </button>
                    <button 
                      type="submit"
                      disabled={isClaiming || claimToken.length < 6}
                      className="flex-1 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-bold transition-colors flex items-center justify-center gap-2"
                    >
                      {isClaiming ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Link Device"}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};