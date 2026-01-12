import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { ORACLE_URL } from '../config';
import type { AnalyticsResponse, Device } from '../types';

interface UseDashboardDataReturn {
  data: AnalyticsResponse | null;
  isConnected: boolean;
  isLoading: boolean;
  hasDevices: boolean | null;
  devices: Device[];
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDashboardData(isAuthenticated: boolean): UseDashboardDataReturn {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasDevices, setHasDevices] = useState<boolean | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState<string | null>(null);
  const retryRef = useRef(0);
  const isDev = import.meta.env.DEV;

  const fetchData = useCallback(async () => {
    if (!isAuthenticated && !isDev) return;

    const token = localStorage.getItem("cardea_auth_token");

    try {
      const devRes = await axios.get<Device[]>(`${ORACLE_URL}/api/devices/list`, { 
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        timeout: 5000
      });
      const deviceList = Array.isArray(devRes.data) ? devRes.data : [];
      setDevices(deviceList);
      setHasDevices(deviceList.length > 0);
    } catch {
      if (isDev) setHasDevices(false);
    }

    try {
      const res = await axios.get<AnalyticsResponse>(`${ORACLE_URL}/api/analytics?time_range=today`, { 
        timeout: 5000 
      });
      setData(res.data);
      setIsConnected(true);
      setError(null);
      retryRef.current = 0;
    } catch {
      setIsConnected(false);
      retryRef.current++;
      if (retryRef.current >= 3 && !isDev) {
        setError("Connection to Oracle lost");
      }
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, isDev]);

  useEffect(() => {
    if (isAuthenticated || isDev) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [fetchData, isAuthenticated, isDev]);

  return {
    data,
    isConnected,
    isLoading,
    hasDevices,
    devices,
    error,
    refetch: fetchData
  };
}
