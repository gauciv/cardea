import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Server, Plus, Wifi, WifiOff, 
  Monitor, Cpu, RefreshCw, Trash2, Key, Check, ArrowLeft
} from 'lucide-react';
import type { Device } from '../types';

// Extend the Device type to include the database field we just patched
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

  const fetchDevices = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }
      const res = await axios.get<ExtendedDevice[]>(`${ORACLE_URL}/api/devices/list`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDevices(res.data);
    } catch (err) {
      console.error("Failed to fetch devices", err);
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const handleClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsClaiming(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${ORACLE_URL}/api/devices/claim`, {
        claim_token: claimToken,
        friendly_name: claimName || `Sentry Device`
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.api_key) {
        setNewDeviceKey(res.data.api_key as string);
        setClaimToken(""); 
        setClaimName("");
        fetchDevices();
      } else {
        setError("Device claimed, but no API key returned.");
      }
    } catch (err: unknown) {
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
            <div className="col-span-full py-24 text-center bg-slate-900/20 rounded-2xl border border-slate-800 border-dashed">
              <div className="w-20 h-20 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-6">
                <Monitor className="w-10 h-10 text-slate-600" />
              </div>
              <h3 className="text-2xl font-bold text-slate-300">No Devices Connected</h3>
              <p className="text-slate-500 mt-2 max-w-md mx-auto">
                Connect a Sentry device to start monitoring your network traffic in real-time.
              </p>
              <button 
                onClick={() => setShowAddModal(true)}
                className="mt-8 px-8 py-3 bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded-full font-bold transition-colors border border-slate-700"
              >
                + Link a Device Now
              </button>
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
                  <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto text-green-400">
                    <Check className="w-8 h-8" />
                  </div>
                  <h2 className="text-2xl font-bold text-white">Device Linked!</h2>
                  <p className="text-slate-400 text-sm">Copy this API Key into your Sentry device to complete the setup.</p>
                  <div className="bg-black/40 border border-slate-700 rounded-lg p-4 relative text-left">
                    <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">Device API Key</p>
                    <code className="text-cyan-400 font-mono text-xs break-all">{newDeviceKey}</code>
                    <button 
                      onClick={() => navigator.clipboard.writeText(newDeviceKey)}
                      className="absolute top-2 right-2 p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-300"
                    >
                      <Key className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <button 
                    onClick={() => { setShowAddModal(false); setNewDeviceKey(null); }}
                    className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold"
                  >
                    Close
                  </button>
                </div>
              ) : (
                <div className="p-8">
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white">Add New Sentry</h2>
                    <button onClick={() => setShowAddModal(false)} className="text-slate-500 hover:text-white">✕</button>
                  </div>
                  <form onSubmit={handleClaim} className="space-y-5">
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Claim Token</label>
                      <input 
                        type="text" 
                        placeholder="ABC-123"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-center text-2xl font-mono tracking-widest text-white focus:border-cyan-500 outline-none transition-colors"
                        value={claimToken}
                        onChange={e => setClaimToken(e.target.value.toUpperCase())}
                        maxLength={7}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Friendly Name</label>
                      <input 
                        type="text" 
                        placeholder="Home Office"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-cyan-500 outline-none transition-colors"
                        value={claimName}
                        onChange={e => setClaimName(e.target.value)}
                      />
                    </div>
                    {error && <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">{error}</div>}
                    <div className="flex gap-3 pt-2">
                      <button type="button" onClick={() => setShowAddModal(false)} className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-bold">Cancel</button>
                      <button 
                        type="submit" 
                        disabled={isClaiming || claimToken.length < 6}
                        className="flex-1 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg font-bold flex items-center justify-center gap-2"
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
    </div>
  );
};