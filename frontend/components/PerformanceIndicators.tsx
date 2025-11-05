/**
 * PerformanceIndicators Component
 * 
 * Displays real-time performance metrics including response times,
 * data freshness, system availability, and other key performance indicators.
 */

'use client';

import React, { useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts';
import { 
  Clock, 
  Activity, 
  Database, 
  Wifi, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { PerformanceMetric, SystemHealthMetric, TrendDataPoint } from '@/lib/metricsApi';
import { format } from 'date-fns';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface PerformanceIndicatorsProps {
  performanceData: PerformanceMetric[];
  healthData: SystemHealthMetric[];
  trendData: TrendDataPoint[];
  className?: string;
}

interface MetricCard {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  threshold_warning: number;
  threshold_critical: number;
  icon: React.ReactNode;
  description: string;
}

interface HealthStatus {
  component: string;
  status: 'up' | 'down' | 'degraded';
  uptime: number;
  responseTime?: number;
  icon: React.ReactNode;
}

// ============================================================================
// Configuration and Constants
// ============================================================================

const STATUS_COLORS = {
  good: '#10b981', // emerald-500
  warning: '#f59e0b', // amber-500
  critical: '#ef4444', // red-500
  up: '#10b981', // emerald-500
  degraded: '#f59e0b', // amber-500
  down: '#ef4444', // red-500
};

const CHART_COLORS = {
  performance: '#3b82f6', // blue-500
  area: '#3b82f6', // blue-500
  areaGradient: 'rgba(59, 130, 246, 0.2)',
  grid: '#374151', // gray-700
  text: '#d1d5db', // gray-300
};

const METRIC_ICONS = {
  'API Response Time': <Clock className="w-5 h-5" />,
  'Model Inference Time': <Activity className="w-5 h-5" />,
  'Data Freshness': <Database className="w-5 h-5" />,
  'Cache Hit Rate': <TrendingUp className="w-5 h-5" />,
  'Request Rate': <Wifi className="w-5 h-5" />,
  'Error Rate': <AlertTriangle className="w-5 h-5" />,
};

const HEALTH_ICONS = {
  'API Server': <Activity className="w-5 h-5" />,
  'Database': <Database className="w-5 h-5" />,
  'Redis Cache': <TrendingUp className="w-5 h-5" />,
  'ML Model': <Activity className="w-5 h-5" />,
};

// ============================================================================
// Helper Functions
// ============================================================================

const getStatusFromValue = (
  value: number,
  warningThreshold: number,
  criticalThreshold: number,
  inverted: boolean = false
): 'good' | 'warning' | 'critical' => {
  if (inverted) {
    // For metrics where lower is better (like response time)
    if (value >= criticalThreshold) return 'critical';
    if (value >= warningThreshold) return 'warning';
    return 'good';
  } else {
    // For metrics where higher is better (like uptime %)
    if (value <= criticalThreshold) return 'critical';
    if (value <= warningThreshold) return 'warning';
    return 'good';
  }
};

const getTrendFromData = (current: number, previous: number): 'up' | 'down' | 'stable' => {
  const change = Math.abs(current - previous) / previous;
  if (change < 0.05) return 'stable'; // Less than 5% change
  return current > previous ? 'up' : 'down';
};

const formatMetricValue = (value: number, unit: string): string => {
  if (unit === 'ms') {
    return value < 1000 ? `${value.toFixed(0)}ms` : `${(value / 1000).toFixed(2)}s`;
  }
  if (unit === '%') {
    return `${value.toFixed(1)}%`;
  }
  if (unit === 'minutes') {
    return value < 60 ? `${value.toFixed(0)}min` : `${(value / 60).toFixed(1)}h`;
  }
  return `${value.toFixed(1)}${unit}`;
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case 'good':
    case 'up':
      return <CheckCircle className="w-4 h-4 text-emerald-500" />;
    case 'warning':
    case 'degraded':
      return <AlertTriangle className="w-4 h-4 text-amber-500" />;
    case 'critical':
    case 'down':
      return <XCircle className="w-4 h-4 text-red-500" />;
    default:
      return <Minus className="w-4 h-4 text-gray-500" />;
  }
};

const TrendIcon: React.FC<{ trend: string; status: string }> = ({ trend, status }) => {
  const color = status === 'good' ? 'text-emerald-500' : 
                status === 'warning' ? 'text-amber-500' : 'text-red-500';
  
  switch (trend) {
    case 'up':
      return <TrendingUp className={`w-4 h-4 ${color}`} />;
    case 'down':
      return <TrendingDown className={`w-4 h-4 ${color}`} />;
    default:
      return <Minus className={`w-4 h-4 ${color}`} />;
  }
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
        <p className="text-gray-300 text-sm mb-2">{`Time: ${label}`}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-300 text-sm">
              {entry.name}: <span className="text-white font-medium">{entry.value}</span>
              {entry.unit || ''}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// ============================================================================
// Main Component
// ============================================================================

const PerformanceIndicators: React.FC<PerformanceIndicatorsProps> = ({
  performanceData,
  healthData,
  trendData,
  className = '',
}) => {
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);

  // Process performance metrics for display
  const processedMetrics = useMemo(() => {
    return performanceData.map((metric, index): MetricCard => {
      const isInverted = metric.unit === 'ms' || metric.unit === 'minutes'; // Lower is better
      const status = getStatusFromValue(
        metric.value,
        metric.threshold_warning,
        metric.threshold_critical,
        isInverted
      );
      
      // Simulate trend calculation (in real app, this would come from historical data)
      const trend = getTrendFromData(metric.value, metric.value * (0.9 + Math.random() * 0.2));
      
      return {
        name: metric.metric_name,
        value: metric.value,
        unit: metric.unit,
        status,
        trend,
        threshold_warning: metric.threshold_warning,
        threshold_critical: metric.threshold_critical,
        icon: METRIC_ICONS[metric.metric_name as keyof typeof METRIC_ICONS] || <Activity className="w-5 h-5" />,
        description: getMetricDescription(metric.metric_name),
      };
    });
  }, [performanceData]);

  // Process health data for display
  const processedHealth = useMemo(() => {
    return healthData.map((health): HealthStatus => ({
      component: health.component,
      status: health.status,
      uptime: health.uptime_percent,
      responseTime: health.response_time_ms,
      icon: HEALTH_ICONS[health.component as keyof typeof HEALTH_ICONS] || <Activity className="w-5 h-5" />,
    }));
  }, [healthData]);

  // Process trend data for charts
  const processedTrendData = useMemo(() => {
    return trendData.map((point) => ({
      timestamp: point.timestamp,
      time: format(new Date(point.timestamp), 'HH:mm'),
      value: point.value,
    }));
  }, [trendData]);

  // Calculate overall system status
  const overallStatus = useMemo(() => {
    const criticalCount = processedMetrics.filter(m => m.status === 'critical').length;
    const warningCount = processedMetrics.filter(m => m.status === 'warning').length;
    const downCount = processedHealth.filter(h => h.status === 'down').length;
    
    if (criticalCount > 0 || downCount > 0) return 'critical';
    if (warningCount > 0) return 'warning';
    return 'good';
  }, [processedMetrics, processedHealth]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overall Status Header */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <StatusIcon status={overallStatus} />
            <div>
              <h2 className="text-xl font-semibold text-white">System Performance</h2>
              <p className="text-sm text-gray-400">
                {overallStatus === 'good' ? 'All systems operational' :
                 overallStatus === 'warning' ? 'Some performance issues detected' :
                 'Critical issues require attention'}
              </p>
            </div>
          </div>
          
          <div className="text-right">
            <p className="text-sm text-gray-400">Last updated</p>
            <p className="text-sm text-white">
              {format(new Date(), 'MMM dd, HH:mm')}
            </p>
          </div>
        </div>
      </div>

      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {processedMetrics.map((metric) => (
          <div
            key={metric.name}
            className={`bg-gray-800 rounded-lg p-4 border cursor-pointer transition-all ${
              selectedMetric === metric.name 
                ? 'border-blue-500 bg-blue-950/20' 
                : 'border-gray-700 hover:border-gray-600'
            }`}
            onClick={() => setSelectedMetric(selectedMetric === metric.name ? null : metric.name)}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div style={{ color: STATUS_COLORS[metric.status] }}>
                  {metric.icon}
                </div>
                <h3 className="text-sm font-medium text-gray-300">{metric.name}</h3>
              </div>
              <TrendIcon trend={metric.trend} status={metric.status} />
            </div>
            
            <div className="flex items-baseline gap-2 mb-2">
              <span 
                className="text-2xl font-bold"
                style={{ color: STATUS_COLORS[metric.status] }}
              >
                {formatMetricValue(metric.value, metric.unit)}
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              <StatusIcon status={metric.status} />
              <span className="text-xs text-gray-400">{metric.description}</span>
            </div>

            {/* Threshold indicators */}
            <div className="mt-3 flex gap-1">
              <div className="flex-1 bg-gray-700 h-1 rounded-full overflow-hidden">
                <div
                  className="h-full transition-all duration-500"
                  style={{
                    backgroundColor: STATUS_COLORS[metric.status],
                    width: `${Math.min(100, (metric.value / metric.threshold_critical) * 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Performance Trend Chart */}
      {selectedMetric && processedTrendData.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            {selectedMetric} - Trend
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={processedTrendData}>
                <defs>
                  <linearGradient id="colorPerformance" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.area} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={CHART_COLORS.area} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                <XAxis
                  dataKey="time"
                  stroke={CHART_COLORS.text}
                  fontSize={12}
                />
                <YAxis stroke={CHART_COLORS.text} fontSize={12} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={CHART_COLORS.area}
                  fillOpacity={1}
                  fill="url(#colorPerformance)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* System Health Status */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">System Health</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {processedHealth.map((health) => (
            <div
              key={health.component}
              className="bg-gray-700 rounded-lg p-3 border border-gray-600"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div style={{ color: STATUS_COLORS[health.status] }}>
                    {health.icon}
                  </div>
                  <span className="text-sm font-medium text-white">{health.component}</span>
                </div>
                <StatusIcon status={health.status} />
              </div>
              
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Uptime</span>
                  <span className="text-white font-medium">{health.uptime.toFixed(2)}%</span>
                </div>
                
                {health.responseTime && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Response Time</span>
                    <span className="text-white font-medium">{health.responseTime.toFixed(0)}ms</span>
                  </div>
                )}
                
                <div className="mt-2 bg-gray-600 h-1 rounded-full overflow-hidden">
                  <div
                    className="h-full transition-all duration-500"
                    style={{
                      backgroundColor: STATUS_COLORS[health.status],
                      width: `${health.uptime}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Distribution Chart */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Performance Distribution</h3>
        
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={processedMetrics}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
              <XAxis
                dataKey="name"
                stroke={CHART_COLORS.text}
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis stroke={CHART_COLORS.text} fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #4b5563',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#d1d5db' }}
              />
              <Bar
                dataKey="value"
                fill={CHART_COLORS.area}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Helper Function for Descriptions
// ============================================================================

const getMetricDescription = (metricName: string): string => {
  switch (metricName) {
    case 'API Response Time':
      return 'Average time for API requests';
    case 'Model Inference Time':
      return 'Time to generate predictions';
    case 'Data Freshness':
      return 'Age of latest weather data';
    case 'Cache Hit Rate':
      return 'Percentage of cached responses';
    case 'Request Rate':
      return 'Requests per second';
    case 'Error Rate':
      return 'Percentage of failed requests';
    default:
      return 'System performance metric';
  }
};

export default PerformanceIndicators;