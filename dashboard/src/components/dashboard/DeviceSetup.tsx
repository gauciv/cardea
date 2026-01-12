import { useNavigate } from 'react-router-dom';
import { Server, Plus } from 'lucide-react';

export const DeviceSetup: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="max-w-md mx-auto text-center py-12">
      <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-center mx-auto mb-4">
        <Server className="w-7 h-7 text-slate-500" />
      </div>
      <h2 className="text-lg font-medium text-white mb-1">No Sentry Devices</h2>
      <p className="text-sm text-slate-500 mb-6">Add a device to start monitoring your network</p>
      <button
        onClick={() => navigate('/devices')}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        <Plus className="w-4 h-4" />
        Add Device
      </button>
    </div>
  );
};
