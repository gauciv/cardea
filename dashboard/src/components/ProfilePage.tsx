import { useState } from 'react';
import { User, Mail, Shield, Calendar, Activity, Server, AlertTriangle, CheckCircle, Clock, Edit2, Camera } from 'lucide-react';
import { Layout } from './Layout';
import { PageHeader } from './PageHeader';
import { useAuth } from '../lib/useAuth';
import { getDisplayName } from '../lib/auth';

export const ProfilePage = () => {
  const { user } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user ? getDisplayName(user) : 'User');

  const email = user?.userDetails || 'user@example.com';
  const provider = user?.identityProvider || 'local';
  const role = user?.userRoles?.includes('admin') ? 'Administrator' : 'Security Analyst';
  
  // Mock stats - in production these would come from the API
  const stats = {
    devicesManaged: 1,
    alertsReviewed: 47,
    actionsPerformed: 12,
    memberSince: '2026-01-01',
    lastLogin: new Date().toISOString()
  };

  const getProviderInfo = () => {
    const p = provider.toLowerCase();
    if (p.includes('google')) return { name: 'Google', color: 'bg-red-500', icon: '🔴' };
    if (p.includes('microsoft') || p.includes('aad') || p.includes('azure')) return { name: 'Microsoft', color: 'bg-blue-500', icon: '🔵' };
    if (p.includes('github')) return { name: 'GitHub', color: 'bg-slate-600', icon: '⚫' };
    return { name: 'Email', color: 'bg-cyan-500', icon: '🔷' };
  };

  const providerInfo = getProviderInfo();

  const getInitials = () => {
    const parts = displayName.split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return displayName.slice(0, 2).toUpperCase();
  };

  return (
    <Layout>
      <PageHeader title="Profile" subtitle="Manage your account" />

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {/* Profile Card */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
          {/* Banner */}
          <div className="h-24 bg-gradient-to-r from-cyan-900/50 via-slate-900 to-cyan-900/50" />
          
          {/* Avatar & Info */}
          <div className="px-6 pb-6">
            <div className="flex items-end gap-4 -mt-10">
              <div className="relative">
                <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-2xl font-bold text-white border-4 border-slate-950">
                  {getInitials()}
                </div>
                <button className="absolute -bottom-1 -right-1 p-1.5 bg-slate-800 rounded-lg border border-slate-700 hover:bg-slate-700 transition-colors">
                  <Camera className="w-3 h-3 text-slate-400" />
                </button>
              </div>
              
              <div className="flex-1 pb-1">
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={displayName}
                      onChange={e => setDisplayName(e.target.value)}
                      onBlur={() => setIsEditing(false)}
                      onKeyDown={e => e.key === 'Enter' && setIsEditing(false)}
                      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-lg font-semibold focus:border-cyan-500 outline-none"
                      autoFocus
                    />
                  ) : (
                    <>
                      <h2 className="text-lg font-semibold text-white">{displayName}</h2>
                      <button onClick={() => setIsEditing(true)} className="p-1 hover:bg-slate-800 rounded">
                        <Edit2 className="w-3 h-3 text-slate-500" />
                      </button>
                    </>
                  )}
                </div>
                <p className="text-sm text-slate-500">{email}</p>
              </div>

              <div className="flex items-center gap-2 pb-1">
                <span className={`w-2 h-2 rounded-full ${providerInfo.color}`} />
                <span className="text-xs text-slate-500">{providerInfo.name}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
            <Server className="w-5 h-5 text-cyan-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{stats.devicesManaged}</p>
            <p className="text-[10px] text-slate-500 uppercase">Devices</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
            <AlertTriangle className="w-5 h-5 text-yellow-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{stats.alertsReviewed}</p>
            <p className="text-[10px] text-slate-500 uppercase">Alerts Reviewed</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
            <CheckCircle className="w-5 h-5 text-green-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{stats.actionsPerformed}</p>
            <p className="text-[10px] text-slate-500 uppercase">Actions Taken</p>
          </div>
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
            <Activity className="w-5 h-5 text-purple-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">99%</p>
            <p className="text-[10px] text-slate-500 uppercase">Uptime</p>
          </div>
        </div>

        {/* Account Details */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-medium text-white mb-4">Account Details</h3>
          
          <div className="flex items-center gap-3 py-3 border-b border-slate-800">
            <User className="w-5 h-5 text-slate-500" />
            <div className="flex-1">
              <p className="text-[10px] text-slate-500 uppercase">Display Name</p>
              <p className="text-sm text-white">{displayName}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 py-3 border-b border-slate-800">
            <Mail className="w-5 h-5 text-slate-500" />
            <div className="flex-1">
              <p className="text-[10px] text-slate-500 uppercase">Email</p>
              <p className="text-sm text-white">{email}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 py-3 border-b border-slate-800">
            <Shield className="w-5 h-5 text-slate-500" />
            <div className="flex-1">
              <p className="text-[10px] text-slate-500 uppercase">Role</p>
              <p className="text-sm text-white">{role}</p>
            </div>
            <span className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 text-[10px] rounded">Active</span>
          </div>

          <div className="flex items-center gap-3 py-3 border-b border-slate-800">
            <Calendar className="w-5 h-5 text-slate-500" />
            <div className="flex-1">
              <p className="text-[10px] text-slate-500 uppercase">Member Since</p>
              <p className="text-sm text-white">{new Date(stats.memberSince).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 py-3">
            <Clock className="w-5 h-5 text-slate-500" />
            <div className="flex-1">
              <p className="text-[10px] text-slate-500 uppercase">Last Login</p>
              <p className="text-sm text-white">{new Date(stats.lastLogin).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Security Status */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <h3 className="text-sm font-medium text-white mb-4">Security Status</h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-slate-400">Password</span>
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="w-3 h-3" /> Set via {providerInfo.name}
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-slate-400">Two-Factor Auth</span>
              <span className="flex items-center gap-1 text-xs text-slate-500">
                Not enabled
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-slate-400">Session</span>
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="w-3 h-3" /> Active
              </span>
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
};
