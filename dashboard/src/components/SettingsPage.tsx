import { useState, useEffect } from 'react';
import { Bell, Shield, Moon, Sun, Volume2, VolumeX, Mail, Smartphone, Clock, Save, Check } from 'lucide-react';
import { PageHeader } from './PageHeader';
import { useAuth } from '../lib/useAuth';

interface NotificationSettings {
  emailAlerts: boolean;
  pushNotifications: boolean;
  criticalOnly: boolean;
  quietHoursEnabled: boolean;
  quietHoursStart: string;
  quietHoursEnd: string;
  soundEnabled: boolean;
}

interface DisplaySettings {
  theme: 'dark' | 'light' | 'system';
  compactMode: boolean;
  autoRefresh: boolean;
  refreshInterval: number;
}

interface SecuritySettings {
  twoFactorEnabled: boolean;
  sessionTimeout: number;
  loginNotifications: boolean;
}

export const SettingsPage = () => {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'notifications' | 'display' | 'security'>('notifications');

  const [notifications, setNotifications] = useState<NotificationSettings>({
    emailAlerts: true,
    pushNotifications: true,
    criticalOnly: false,
    quietHoursEnabled: false,
    quietHoursStart: '22:00',
    quietHoursEnd: '07:00',
    soundEnabled: true
  });

  const [display, setDisplay] = useState<DisplaySettings>({
    theme: 'dark',
    compactMode: false,
    autoRefresh: true,
    refreshInterval: 30
  });

  const [security, setSecurity] = useState<SecuritySettings>({
    twoFactorEnabled: false,
    sessionTimeout: 60,
    loginNotifications: true
  });

  // Load settings from localStorage
  useEffect(() => {
    const savedSettings = localStorage.getItem('cardea_settings');
    if (savedSettings) {
      const parsed = JSON.parse(savedSettings);
      if (parsed.notifications) setNotifications(parsed.notifications);
      if (parsed.display) setDisplay(parsed.display);
      if (parsed.security) setSecurity(parsed.security);
    }
  }, []);

  const handleSave = () => {
    localStorage.setItem('cardea_settings', JSON.stringify({ notifications, display, security }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const Toggle: React.FC<{ enabled: boolean; onChange: (v: boolean) => void; disabled?: boolean }> = ({ enabled, onChange, disabled }) => (
    <button
      onClick={() => !disabled && onChange(!enabled)}
      disabled={disabled}
      className={`relative w-10 h-5 rounded-full transition-colors ${enabled ? 'bg-cyan-600' : 'bg-slate-700'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? 'translate-x-5' : ''}`} />
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <PageHeader />

      <main className="max-w-3xl mx-auto px-6 py-8">
        {/* Page Title */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-lg font-semibold">Settings</h1>
            <p className="text-xs text-slate-500">Customize your Cardea experience</p>
          </div>
          <button
            onClick={handleSave}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              saved ? 'bg-green-600 text-white' : 'bg-cyan-600 hover:bg-cyan-500 text-white'
            }`}
          >
            {saved ? <><Check className="w-4 h-4" /> Saved</> : <><Save className="w-4 h-4" /> Save</>}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 bg-slate-900 rounded-lg mb-8">
          {[
            { id: 'notifications', label: 'Notifications', icon: Bell },
            { id: 'display', label: 'Display', icon: Moon },
            { id: 'security', label: 'Security', icon: Shield }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.id ? 'bg-slate-800 text-white' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-5">
              <h3 className="text-sm font-medium text-white mb-4">Alert Preferences</h3>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-slate-500" />
                  <div>
                    <p className="text-sm text-white">Email Alerts</p>
                    <p className="text-xs text-slate-500">Receive security alerts via email</p>
                  </div>
                </div>
                <Toggle enabled={notifications.emailAlerts} onChange={v => setNotifications(p => ({ ...p, emailAlerts: v }))} />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Smartphone className="w-5 h-5 text-slate-500" />
                  <div>
                    <p className="text-sm text-white">Push Notifications</p>
                    <p className="text-xs text-slate-500">Browser notifications for new alerts</p>
                  </div>
                </div>
                <Toggle enabled={notifications.pushNotifications} onChange={v => setNotifications(p => ({ ...p, pushNotifications: v }))} />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-slate-500" />
                  <div>
                    <p className="text-sm text-white">Critical Alerts Only</p>
                    <p className="text-xs text-slate-500">Only notify for high/critical severity</p>
                  </div>
                </div>
                <Toggle enabled={notifications.criticalOnly} onChange={v => setNotifications(p => ({ ...p, criticalOnly: v }))} />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {notifications.soundEnabled ? <Volume2 className="w-5 h-5 text-slate-500" /> : <VolumeX className="w-5 h-5 text-slate-500" />}
                  <div>
                    <p className="text-sm text-white">Alert Sounds</p>
                    <p className="text-xs text-slate-500">Play sound for new alerts</p>
                  </div>
                </div>
                <Toggle enabled={notifications.soundEnabled} onChange={v => setNotifications(p => ({ ...p, soundEnabled: v }))} />
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-5 h-5 text-slate-500" />
                  <div>
                    <p className="text-sm text-white">Quiet Hours</p>
                    <p className="text-xs text-slate-500">Silence non-critical alerts during set hours</p>
                  </div>
                </div>
                <Toggle enabled={notifications.quietHoursEnabled} onChange={v => setNotifications(p => ({ ...p, quietHoursEnabled: v }))} />
              </div>

              {notifications.quietHoursEnabled && (
                <div className="flex items-center gap-4 pl-8">
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase">From</label>
                    <input
                      type="time"
                      value={notifications.quietHoursStart}
                      onChange={e => setNotifications(p => ({ ...p, quietHoursStart: e.target.value }))}
                      className="block mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase">To</label>
                    <input
                      type="time"
                      value={notifications.quietHoursEnd}
                      onChange={e => setNotifications(p => ({ ...p, quietHoursEnd: e.target.value }))}
                      className="block mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Display Tab */}
        {activeTab === 'display' && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-5">
              <h3 className="text-sm font-medium text-white mb-4">Appearance</h3>
              
              <div>
                <p className="text-sm text-white mb-3">Theme</p>
                <div className="flex gap-2">
                  {[
                    { id: 'dark', label: 'Dark', icon: Moon },
                    { id: 'light', label: 'Light', icon: Sun },
                  ].map(theme => (
                    <button
                      key={theme.id}
                      onClick={() => setDisplay(p => ({ ...p, theme: theme.id as 'dark' | 'light' }))}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                        display.theme === theme.id ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <theme.icon className="w-4 h-4" />
                      {theme.label}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-slate-600 mt-2">Light theme coming soon</p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">Compact Mode</p>
                  <p className="text-xs text-slate-500">Reduce spacing for more content</p>
                </div>
                <Toggle enabled={display.compactMode} onChange={v => setDisplay(p => ({ ...p, compactMode: v }))} />
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-5">
              <h3 className="text-sm font-medium text-white mb-4">Data Refresh</h3>
              
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">Auto-Refresh</p>
                  <p className="text-xs text-slate-500">Automatically update dashboard data</p>
                </div>
                <Toggle enabled={display.autoRefresh} onChange={v => setDisplay(p => ({ ...p, autoRefresh: v }))} />
              </div>

              {display.autoRefresh && (
                <div>
                  <label className="text-xs text-slate-500">Refresh Interval</label>
                  <select
                    value={display.refreshInterval}
                    onChange={e => setDisplay(p => ({ ...p, refreshInterval: Number(e.target.value) }))}
                    className="block mt-1 w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                  >
                    <option value={10}>Every 10 seconds</option>
                    <option value={30}>Every 30 seconds</option>
                    <option value={60}>Every minute</option>
                    <option value={300}>Every 5 minutes</option>
                  </select>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-5">
              <h3 className="text-sm font-medium text-white mb-4">Account Security</h3>
              
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">Two-Factor Authentication</p>
                  <p className="text-xs text-slate-500">Add an extra layer of security</p>
                </div>
                <Toggle enabled={security.twoFactorEnabled} onChange={v => setSecurity(p => ({ ...p, twoFactorEnabled: v }))} disabled />
              </div>
              <p className="text-[10px] text-slate-600 pl-0">2FA setup coming soon</p>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-white">Login Notifications</p>
                  <p className="text-xs text-slate-500">Get notified of new sign-ins</p>
                </div>
                <Toggle enabled={security.loginNotifications} onChange={v => setSecurity(p => ({ ...p, loginNotifications: v }))} />
              </div>

              <div>
                <label className="text-xs text-slate-500">Session Timeout</label>
                <select
                  value={security.sessionTimeout}
                  onChange={e => setSecurity(p => ({ ...p, sessionTimeout: Number(e.target.value) }))}
                  className="block mt-1 w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                >
                  <option value={30}>30 minutes</option>
                  <option value={60}>1 hour</option>
                  <option value={240}>4 hours</option>
                  <option value={480}>8 hours</option>
                </select>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-medium text-white mb-4">Connected Account</h3>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-cyan-600 flex items-center justify-center text-white font-bold">
                  {user?.userDetails?.slice(0, 2).toUpperCase() || 'U'}
                </div>
                <div>
                  <p className="text-sm text-white">{user?.userDetails || 'User'}</p>
                  <p className="text-xs text-slate-500">via {user?.identityProvider || 'Local'}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
