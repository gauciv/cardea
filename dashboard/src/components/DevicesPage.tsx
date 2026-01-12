import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Server, Plus, Wifi, WifiOff, RefreshCw, Trash2, ArrowLeft, Copy, CheckCircle, X, AlertTriangle } from 'lucide-react';
import type { Device } from '../types';

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
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    const token = localStorage.getItem('cardea_auth_token');

    try {
      const res = await axios.get<ExtendedDevice[]>(`${ORACLE_URL}/api/devices/list`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      setDevices(res.data);
    } catch (err) {
      console.error("Failed to fetch devices", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const handleClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsClaiming(true);
    setError(null);

    try {
      const token = localStorage.getItem('cardea_auth_token');
      const res = await axios.post(`${ORACLE_URL}/api/devices/claim`, {
        claim_token: claimToken,
        friendly_name: claimName || `Sentry Device`
      }, { headers: { Authorization: `Bearer ${token}` } });

      if (res.data.api_key) {
        setNewDeviceKey(res.data.api_key);
        setClaimToken("");
        setClaimName("");
        await fetchDevices();
      } else {
        setError("Device claimed, but no API key returned.");
      }
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || "Failed to claim device.");
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setIsClaiming(false);
    }
  };

  const handleDelete = async (deviceId: string) => {
    try {
      const token = localStorage.getItem('cardea_auth_token');
      await axios.delete(`${ORACLE_URL}/api/devices/${deviceId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      setDeleteConfirm(null);
      await fetchDevices();
    } catch (err) {
      console.error("Failed to delete device", err);
    }
  };

  const copyKey = () => {
    if (newDeviceKey) {
      navigator.clipboard.writeText(newDeviceKey);
      setKeyCopied(true);
      setTimeout(() => setKeyCopied(false), 2000);
    }
  };

  const closeModal = () => {
    setShowAddModal(false);
    setNewDeviceKey(null);
    setError(null);
    setClaimToken("");
    setClaimName("");
    setKeyCopied(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-4xl mx-auto px-6 py-8">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-500" /> Devices
              </h1>
              <p className="text-xs text-slate-500">{devices.length} connected</p>
            </div>
          </div>
          <button onClick={() => setShowAddModal(true)} className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105 active:scale-95">
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>

        {/* Device List */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map(i => <div key={i} className="h-20 bg-slate-900/50 rounded-xl animate-pulse" />)}
          </div>
        ) : devices.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/30 border border-slate-800 border-dashed rounded-xl">
            <Server className="w-10 h-10 text-slate-700 mx-auto mb-3" />
            <p className="text-sm text-slate-500 mb-4">No devices connected yet</p>
            <button onClick={() => setShowAddModal(true)} className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
              + Add your first device
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {devices.map(device => (
              <div key={device.id} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${device.status === 'online' ? 'bg-green-500/10 border border-green-500/20' : 'bg-slate-800'}`}>
                      {device.status === 'online' ? <Wifi className="w-5 h-5 text-green-400" /> : <WifiOff className="w-5 h-5 text-slate-500" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{device.friendly_name || 'Sentry Device'}</p>
                      <p className="text-[10px] text-slate-500 font-mono">{device.hardware_id?.slice(0, 16)}...</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-medium px-2 py-1 rounded ${device.status === 'online' ? 'bg-green-500/10 text-green-400' : 'bg-slate-800 text-slate-500'}`}>
                      {device.status === 'online' ? 'Online' : 'Offline'}
                    </span>
                    <button onClick={() => setDeleteConfirm(device.id)} className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {device.last_seen && (
                  <p className="text-[10px] text-slate-600 mt-2">Last seen: {new Date(device.last_seen).toLocaleString()}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Device Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={closeModal}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-sm animate-in zoom-in-95" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Add Device</h2>
              <button onClick={closeModal} className="text-slate-500 hover:text-white p-1"><X className="w-4 h-4" /></button>
            </div>

            {newDeviceKey ? (
              <div className="p-4">
                <div className="text-center mb-4">
                  <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <CheckCircle className="w-6 h-6 text-green-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">Device Added!</h3>
                  <p className="text-xs text-slate-400 mt-1">Copy this API key to your Sentry device</p>
                </div>
                <div className="bg-slate-950 border border-slate-700 rounded-lg p-3 mb-4">
                  <p className="text-[10px] text-slate-500 mb-1">API Key (copy now - shown once)</p>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-cyan-400 font-mono flex-1 break-all">{newDeviceKey}</code>
                    <button onClick={copyKey} className={`p-2 rounded-lg transition-colors ${keyCopied ? 'bg-green-500/20 text-green-400' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
                      {keyCopied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <button onClick={closeModal} className="w-full bg-slate-800 hover:bg-slate-700 text-white py-2 rounded-lg text-sm font-medium">Done</button>
              </div>
            ) : (
              <form onSubmit={handleClaim} className="p-4 space-y-4">
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-wider">Pairing Code</label>
                  <input type="text" value={claimToken} onChange={e => setClaimToken(e.target.value.toUpperCase())}
                    className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-sm text-center font-mono tracking-widest focus:border-cyan-500 outline-none"
                    placeholder="ABC-123" maxLength={7} required />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-wider">Device Name (optional)</label>
                  <input type="text" value={claimName} onChange={e => setClaimName(e.target.value)}
                    className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-sm focus:border-cyan-500 outline-none"
                    placeholder="Office Sentry" />
                </div>
                {error && <p className="text-xs text-red-400 text-center">{error}</p>}
                <button type="submit" disabled={isClaiming || !claimToken}
                  className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 text-white py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors">
                  {isClaiming ? <><RefreshCw className="w-4 h-4 animate-spin" />Connecting...</> : 'Connect Device'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xs p-4 text-center animate-in zoom-in-95" onClick={e => e.stopPropagation()}>
            <div className="w-10 h-10 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1">Remove Device?</h3>
            <p className="text-xs text-slate-400 mb-4">This device will need to be re-paired to reconnect.</p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-2 rounded-lg text-sm">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 bg-red-600 hover:bg-red-500 text-white py-2 rounded-lg text-sm">Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
