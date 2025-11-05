'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Activity, 
  Database, 
  Brain, 
  Clock, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  Wifi,
  Gauge,
  Server,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import { useMetrics } from '@/lib/ClientMetricsProvider';
import type { HealthResponse } from '@/types';

// Client-side only timestamp component to prevent hydration mismatch
const ClientTimestamp = ({ timestamp }: { timestamp: Date }) => {
  const [mounted, setMounted] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    setMounted(true);
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!mounted) {
    return <span className="text-slate-400 font-mono">--:--:--</span>;
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-AU', {
      timeZone: 'Australia/Adelaide',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const secondsSinceUpdate = Math.floor((currentTime.getTime() - timestamp.getTime()) / 1000);

  return (
    <>
      <span className="text-slate-400 font-mono">
        {formatTimestamp(currentTime)}
      </span>
      <span className="text-slate-500 ml-2">
        ({secondsSinceUpdate}s ago)
      </span>
    </>
  );
};

/**
 * StatusBar Component - Real-time System Status Indicators
 * 
 * Displays live status for:
 * - FAISS index (13,148 patterns, recall percentage)
 * - Dataset status (ERA5-2024-10, last updated timestamp)
 * - Model status (Analog-v2.1, version info)
 * - Latency monitoring with color-coded alerts
 * 
 * Integrates with Prometheus metrics and health check API
 */

interface SystemStatus {
  faiss: {
    status: 'healthy' | 'warning' | 'error';
    patterns: number;
    recall: number;
    lastUpdated: string;
  };
  dataset: {
    status: 'healthy' | 'warning' | 'error';
    version: string;
    lastUpdated: string;
    coverage: number;
  };
  model: {
    status: 'healthy' | 'warning' | 'error';
    version: string;
    hash: string;
    matchRatio: number;
  };
  latency: {
    current: number;
    average: number;
    p95: number;
    status: 'green' | 'yellow' | 'red';
  };
  overall: 'healthy' | 'degraded' | 'critical';
}

interface StatusIndicatorProps {
  status: 'healthy' | 'warning' | 'error' | 'green' | 'yellow' | 'red';
  icon: React.ReactNode;
  label: string;
  value: string;
  detail?: string;
  isLatency?: boolean;
}

interface LatencyDisplayProps {
  latency: SystemStatus['latency'];
  onRefresh: () => void;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ 
  status, 
  icon, 
  label, 
  value, 
  detail,
  isLatency = false 
}) => {
  const getStatusColor = () => {
    if (isLatency) {
      switch (status) {
        case 'green': return 'text-green-400 bg-green-500/10 border-green-500/20';
        case 'yellow': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
        case 'red': return 'text-red-400 bg-red-500/10 border-red-500/20';
        default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
      }
    }
    
    switch (status) {
      case 'healthy': return 'text-green-400 bg-green-500/10 border-green-500/20';
      case 'warning': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
      case 'error': return 'text-red-400 bg-red-500/10 border-red-500/20';
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
    }
  };

  const getStatusIcon = () => {
    if (isLatency) {
      switch (status) {
        case 'green': return <CheckCircle size={12} className="text-green-400" />;
        case 'yellow': return <AlertTriangle size={12} className="text-yellow-400" />;
        case 'red': return <XCircle size={12} className="text-red-400" />;
        default: return <AlertTriangle size={12} className="text-slate-400" />;
      }
    }
    
    switch (status) {
      case 'healthy': return <CheckCircle size={12} className="text-green-400" />;
      case 'warning': return <AlertTriangle size={12} className="text-yellow-400" />;
      case 'error': return <XCircle size={12} className="text-red-400" />;
      default: return <AlertTriangle size={12} className="text-slate-400" />;
    }
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${getStatusColor()}`}>
      <div className="flex items-center gap-1.5">
        {icon}
        {getStatusIcon()}
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-200">{label}</span>
          <span className="text-xs font-mono text-slate-300">{value}</span>
        </div>
        {detail && (
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            {detail}
          </div>
        )}
      </div>
    </div>
  );
};

const LatencyDisplay: React.FC<LatencyDisplayProps> = ({ latency, onRefresh }) => {
  return (
    <div className="flex items-center gap-2">
      <StatusIndicator
        status={latency.status}
        icon={<Gauge size={14} />}
        label="Latency"
        value={`${latency.current}ms`}
        detail={`avg: ${latency.average}ms, p95: ${latency.p95}ms`}
        isLatency={true}
      />
      <button
        onClick={onRefresh}
        className="p-1.5 rounded-md bg-slate-800/50 border border-slate-700 hover:bg-slate-700/50 transition-colors"
        title="Refresh latency metrics"
      >
        <RefreshCw size={12} className="text-slate-400" />
      </button>
    </div>
  );
};

export const StatusBar: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    faiss: {
      status: 'healthy',
      patterns: 13148,
      recall: 95.3,
      lastUpdated: '2024-10-29T10:30:00Z'
    },
    dataset: {
      status: 'healthy',
      version: 'ERA5-2024-10',
      lastUpdated: '2024-10-29T06:00:00Z',
      coverage: 98.7
    },
    model: {
      status: 'healthy',
      version: 'Analog-v2.1',
      hash: 'a7c3f92',
      matchRatio: 99.8
    },
    latency: {
      current: 42,
      average: 38,
      p95: 85,
      status: 'green'
    },
    overall: 'healthy'
  });

  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [updateInterval, setUpdateInterval] = useState<number>(5000); // 5 seconds
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const metrics = useMetrics();

  // Fetch health data from API
  const fetchHealthData = useCallback(async () => {
    const timer = metrics.startTimer();
    
    try {
      const response = await fetch('/api/health', {
        headers: {
          'Cache-Control': 'no-cache',
        },
      });

      const duration = timer();
      
      if (response.ok) {
        const healthData: HealthResponse = await response.json();
        
        // Track API response time
        metrics.trackAPICall('/api/health', response.status, duration);
        
        // Update system status based on health data
        const newStatus: SystemStatus = {
          faiss: {
            status: healthData.index.ntotal > 0 ? 'healthy' : 'error',
            patterns: healthData.index.ntotal || 13148,
            recall: 95.3, // Would come from metrics in real implementation
            lastUpdated: new Date().toISOString()
          },
          dataset: {
            status: healthData.datasets.length > 0 ? 'healthy' : 'warning',
            version: 'ERA5-2024-10',
            lastUpdated: new Date().toISOString(),
            coverage: healthData.datasets.length > 0 
              ? Math.min(...healthData.datasets.map(d => 
                  Math.min(...Object.values(d.valid_pct_by_var))
                )) 
              : 0
          },
          model: {
            status: healthData.model.matched_ratio > 0.95 ? 'healthy' : 'warning',
            version: healthData.model.version,
            hash: healthData.model.hash.substring(0, 7),
            matchRatio: healthData.model.matched_ratio * 100
          },
          latency: {
            current: Math.round(duration * 1000), // Convert to ms
            average: systemStatus.latency.average,
            p95: systemStatus.latency.p95,
            status: duration < 0.1 ? 'green' : duration < 0.2 ? 'yellow' : 'red'
          },
          overall: healthData.ready ? 'healthy' : 'degraded'
        };

        setSystemStatus(newStatus);
        setLastUpdated(new Date());
      } else {
        // Track error
        metrics.trackAPICall('/api/health', response.status, duration);
        
        // Update status to reflect API errors
        setSystemStatus(prev => ({
          ...prev,
          overall: 'critical',
          latency: {
            ...prev.latency,
            current: Math.round(duration * 1000),
            status: 'red'
          }
        }));
      }
    } catch (error) {
      const duration = timer();
      console.error('Health check failed:', error);
      
      // Track error
      metrics.trackAPICall('/api/health', 0, duration);
      
      setSystemStatus(prev => ({
        ...prev,
        overall: 'critical',
        latency: {
          ...prev.latency,
          current: Math.round(duration * 1000),
          status: 'red'
        }
      }));
    }
  }, [metrics, systemStatus.latency.average, systemStatus.latency.p95]);

  // Fetch Prometheus metrics for enhanced latency data
  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch('/api/metrics');
      if (response.ok) {
        const metricsText = await response.text();
        
        // Parse basic latency metrics from Prometheus format
        // This is a simplified parser - in production, use a proper Prometheus client
        const lines = metricsText.split('\n');
        const apiResponseTime = lines.find(line => 
          line.includes('frontend_api_response_time_seconds') && 
          line.includes('quantile="0.95"')
        );
        
        if (apiResponseTime) {
          const p95Value = parseFloat(apiResponseTime.split(' ')[1]) * 1000; // Convert to ms
          setSystemStatus(prev => ({
            ...prev,
            latency: {
              ...prev.latency,
              p95: Math.round(p95Value)
            }
          }));
        }
      }
    } catch (error) {
      console.error('Metrics fetch failed:', error);
    }
  }, []);

  // Manual refresh function
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([fetchHealthData(), fetchMetrics()]);
    setTimeout(() => setIsRefreshing(false), 500); // Visual feedback
  }, [fetchHealthData, fetchMetrics]);

  // Set up polling for real-time updates
  useEffect(() => {
    // Initial fetch
    fetchHealthData();
    fetchMetrics();

    // Set up intervals
    const healthInterval = setInterval(fetchHealthData, updateInterval);
    const metricsInterval = setInterval(fetchMetrics, updateInterval * 2); // Less frequent for metrics

    return () => {
      clearInterval(healthInterval);
      clearInterval(metricsInterval);
    };
  }, [fetchHealthData, fetchMetrics, updateInterval]);

  // Get overall status color
  const getOverallStatusColor = () => {
    switch (systemStatus.overall) {
      case 'healthy': return 'text-green-400';
      case 'degraded': return 'text-yellow-400';
      case 'critical': return 'text-red-400';
      default: return 'text-slate-400';
    }
  };


  return (
    <div className="bg-[#0E1116]/95 border-t border-[#2A2F3A] px-4 py-3">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Left section - System status indicators */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Overall status */}
            <div className="flex items-center gap-2">
              <Activity size={14} className={getOverallStatusColor()} />
              <span className={`text-sm font-medium ${getOverallStatusColor()}`}>
                System {systemStatus.overall}
              </span>
            </div>

            {/* FAISS Index Status */}
            <StatusIndicator
              status={systemStatus.faiss.status}
              icon={<Database size={14} />}
              label="FAISS"
              value={`${systemStatus.faiss.patterns.toLocaleString()} patterns`}
              detail={`recall: ${systemStatus.faiss.recall}%`}
            />

            {/* Dataset Status */}
            <StatusIndicator
              status={systemStatus.dataset.status}
              icon={<Server size={14} />}
              label="Dataset"
              value={systemStatus.dataset.version}
              detail={`coverage: ${systemStatus.dataset.coverage}%`}
            />

            {/* Model Status */}
            <StatusIndicator
              status={systemStatus.model.status}
              icon={<Brain size={14} />}
              label="Model"
              value={systemStatus.model.version}
              detail={`hash: ${systemStatus.model.hash}, match: ${systemStatus.model.matchRatio}%`}
            />
          </div>

          {/* Right section - Latency and update info */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Latency Display */}
            <LatencyDisplay 
              latency={systemStatus.latency} 
              onRefresh={handleRefresh}
            />

            {/* Update timestamp */}
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 border border-slate-700/50 rounded-lg">
              <Clock size={12} className="text-slate-500" />
              <div className="text-xs">
                <ClientTimestamp timestamp={lastUpdated} />
              </div>
              {isRefreshing && (
                <RefreshCw size={12} className="text-cyan-400 animate-spin" />
              )}
            </div>

            {/* Connection status */}
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-800/30 border border-slate-700/50 rounded">
              <Wifi size={10} className="text-green-400" />
              <span className="text-[10px] text-green-400 font-mono">LIVE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};