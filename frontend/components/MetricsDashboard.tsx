/**
 * MetricsDashboard Component
 * 
 * Main dashboard component that orchestrates the display of forecast accuracy,
 * performance metrics, and system health indicators with interactive controls.
 */

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Download, 
  RefreshCw, 
  Filter, 
  Calendar, 
  BarChart3,
  Activity,
  AlertCircle,
  CheckCircle,
  Settings,
  Info,
} from 'lucide-react';
import { ForecastHorizon, WeatherVariable, FORECAST_HORIZONS, WEATHER_VARIABLES } from '@/types/api';
import { 
  metricsApi, 
  MetricsSummary, 
  TimeRange, 
  MetricsFilter,
  ExportFormat,
} from '@/lib/metricsApi';
import AccuracyChart from './AccuracyChart';
import PerformanceIndicators from './PerformanceIndicators';
import EmptyState from './EmptyState';
import ErrorBoundary from './ErrorBoundary';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface MetricsDashboardProps {
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // in seconds
}

interface DashboardState {
  data: MetricsSummary | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  dataSource?: 'api' | 'cache' | 'fallback';
  isEmpty?: boolean;
}

interface FilterState {
  timeRange: TimeRange;
  horizons: ForecastHorizon[];
  variables: WeatherVariable[];
  includeConfidence: boolean;
}

// ============================================================================
// Configuration and Constants
// ============================================================================

const DEFAULT_FILTER: FilterState = {
  timeRange: '24h',
  horizons: ['6h', '12h', '24h', '48h'],
  variables: ['t2m', 'u10', 'v10', 'msl', 'cape'],
  includeConfidence: true,
};

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '1h', label: 'Last Hour' },
  { value: '6h', label: 'Last 6 Hours' },
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
];

const VARIABLE_DISPLAY_NAMES: Record<WeatherVariable, string> = {
  't2m': '2m Temperature',
  'u10': '10m U Wind',
  'v10': '10m V Wind',
  'msl': 'Sea Level Pressure',
  'r850': '850hPa Humidity',
  'tp6h': '6h Precipitation',
  'cape': 'CAPE',
  't850': '850hPa Temperature',
  'z500': '500hPa Height',
};

// ============================================================================
// Helper Components
// ============================================================================

const LoadingSpinner: React.FC = () => (
  <ErrorBoundary componentName="MetricsDashboard-LoadingSpinner">
    <EmptyState
      type="loading-failed"
      title="Loading Metrics"
      description="Fetching system performance and forecast accuracy data..."
      size="lg"
      disableAnimations={false}
    />
  </ErrorBoundary>
);

const ErrorDisplay: React.FC<{ error: string; onRetry: () => void; showDetails?: boolean }> = ({ 
  error, 
  onRetry,
  showDetails = false 
}) => (
  <ErrorBoundary componentName="MetricsDashboard-ErrorDisplay">
    <EmptyState
      type="error"
      title="Metrics Error"
      description={showDetails ? error : "Unable to load metrics data. Please try again."}
      showRetry={true}
      onRetry={onRetry}
      size="lg"
    />
  </ErrorBoundary>
);

const StatusBadge: React.FC<{ status: 'good' | 'warning' | 'critical'; children: React.ReactNode }> = ({ 
  status, 
  children 
}) => {
  const colors = {
    good: 'bg-emerald-950/50 border-emerald-700 text-emerald-400',
    warning: 'bg-amber-950/50 border-amber-600 text-amber-400',
    critical: 'bg-red-950/50 border-red-700 text-red-400',
  };

  const icons = {
    good: <CheckCircle className="w-4 h-4" />,
    warning: <AlertCircle className="w-4 h-4" />,
    critical: <AlertCircle className="w-4 h-4" />,
  };

  return (
    <div className={`inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium border ${colors[status]}`}>
      {icons[status]}
      {children}
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  className = '',
  autoRefresh = true,
  refreshInterval = 30,
}) => {
  // State management
  const [state, setState] = useState<DashboardState>({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    dataSource: undefined,
    isEmpty: false,
  });

  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER);
  const [showFilters, setShowFilters] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Fetch metrics data
  const fetchMetrics = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setState(prev => ({ ...prev, loading: true, error: null, isEmpty: false }));
    }

    try {
      const data = await metricsApi.getMetricsSummary({
        timeRange: filter.timeRange,
        horizons: filter.horizons,
        variables: filter.variables,
        includeConfidence: filter.includeConfidence,
      });

      // Check if data is empty or contains no meaningful content
      const isEmpty = !data || 
        (!data.forecast_accuracy?.length && 
         !data.performance_metrics?.length && 
         !data.system_health?.length);

      // Determine data source (add fallback logic if needed)
      const dataSource: DashboardState['dataSource'] = data?.data_source as any || 'api';

      setState({
        data,
        loading: false,
        error: null,
        lastUpdated: new Date(),
        dataSource,
        isEmpty,
      });
    } catch (error) {
      console.error('Error fetching metrics:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to load metrics';
      
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
        isEmpty: false,
      }));
    }
  }, [filter]);

  // Auto-refresh effect
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchMetrics(false); // Silent refresh
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchMetrics]);

  // Filter handlers
  const handleTimeRangeChange = (timeRange: TimeRange) => {
    setFilter(prev => ({ ...prev, timeRange }));
  };

  const handleHorizonToggle = (horizon: ForecastHorizon) => {
    setFilter(prev => ({
      ...prev,
      horizons: prev.horizons.includes(horizon)
        ? prev.horizons.filter(h => h !== horizon)
        : [...prev.horizons, horizon],
    }));
  };

  const handleVariableToggle = (variable: WeatherVariable) => {
    setFilter(prev => ({
      ...prev,
      variables: prev.variables.includes(variable)
        ? prev.variables.filter(v => v !== variable)
        : [...prev.variables, variable],
    }));
  };

  const handleExport = async (format: 'png' | 'csv' | 'json') => {
    setIsExporting(true);
    try {
      const exportData = await metricsApi.exportMetrics(format, filter);
      
      // Create and trigger download
      const blob = new Blob([exportData.data], {
        type: format === 'json' ? 'application/json' : 'text/csv',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = exportData.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  // Calculate overall system status
  const overallStatus = useMemo(() => {
    if (!state.data || state.isEmpty) return 'warning';
    
    const criticalMetrics = state.data.performance_metrics?.filter(m => m.status === 'critical').length || 0;
    const downComponents = state.data.system_health?.filter(h => h.status === 'down').length || 0;
    const avgAccuracy = state.data.forecast_accuracy?.length > 0 
      ? state.data.forecast_accuracy.reduce((sum, a) => sum + a.accuracy_percent, 0) / state.data.forecast_accuracy.length
      : 0;
    
    if (criticalMetrics > 0 || downComponents > 0 || avgAccuracy < 80) return 'critical';
    if (avgAccuracy < 90) return 'warning';
    return 'good';
  }, [state.data, state.isEmpty]);

  if (state.loading && !state.data) {
    return <LoadingSpinner />;
  }

  if (state.error && !state.data) {
    return <ErrorDisplay error={state.error} onRetry={() => fetchMetrics()} />;
  }

  // Handle empty data state
  if (state.isEmpty || !state.data) {
    return (
      <ErrorBoundary componentName="MetricsDashboard-Empty">
        <div className={`space-y-6 ${className}`}>
          <EmptyState
            type="no-metrics"
            title="No Metrics Available"
            description={`No metrics data found for the selected time range (${filter.timeRange}). Try adjusting your filters or check back later.`}
            showRetry={true}
            onRetry={() => fetchMetrics()}
            size="lg"
            dataSource={state.dataSource === 'fallback' ? 'fallback' : undefined}
          />
        </div>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary componentName="MetricsDashboard">
      <div className={`space-y-6 ${className}`}>
      {/* Dashboard Header */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-blue-400" />
              <h1 className="text-xl font-bold text-white">Metrics Dashboard</h1>
            </div>
            <StatusBadge status={overallStatus}>
              {overallStatus === 'good' ? 'System Healthy' :
               overallStatus === 'warning' ? 'Attention Needed' :
               'Critical Issues'}
            </StatusBadge>
            {state.dataSource === 'fallback' && (
              <div className="px-2 py-1 bg-orange-900/50 border border-orange-700 text-orange-300 rounded text-xs font-medium">
                FALLBACK DATA
              </div>
            )}
            {state.dataSource === 'cache' && (
              <div className="px-2 py-1 bg-blue-900/50 border border-blue-700 text-blue-300 rounded text-xs font-medium">
                CACHED
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Time Range Selector */}
            <select
              value={filter.timeRange}
              onChange={(e) => handleTimeRangeChange(e.target.value as TimeRange)}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {TIME_RANGE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {/* Filter Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded text-sm transition-colors ${
                showFilters 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              title="Toggle Filters"
            >
              <Filter className="w-4 h-4" />
            </button>

            {/* Export Dropdown */}
            <div className="relative">
              <button
                onClick={() => handleExport('json')}
                disabled={isExporting}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-1.5 rounded text-sm transition-colors disabled:opacity-50"
                title="Export as JSON"
              >
                <Download className="w-4 h-4" />
                {isExporting ? 'Exporting...' : 'Export'}
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => fetchMetrics()}
              disabled={state.loading}
              className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-sm transition-colors disabled:opacity-50"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
            </button>

            {/* Last Updated */}
            {state.lastUpdated && (
              <span className="text-xs text-gray-400">
                Updated {state.lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-700 space-y-4">
            {/* Horizon Filters */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Forecast Horizons
              </label>
              <div className="flex flex-wrap gap-2">
                {FORECAST_HORIZONS.map(horizon => (
                  <button
                    key={horizon}
                    onClick={() => handleHorizonToggle(horizon)}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      filter.horizons.includes(horizon)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {horizon}
                  </button>
                ))}
              </div>
            </div>

            {/* Variable Filters */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Weather Variables
              </label>
              <div className="flex flex-wrap gap-2">
                {WEATHER_VARIABLES.slice(0, 6).map(variable => ( // Show main variables
                  <button
                    key={variable}
                    onClick={() => handleVariableToggle(variable)}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      filter.variables.includes(variable)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {VARIABLE_DISPLAY_NAMES[variable]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {state.error && (
        <ErrorDisplay error={state.error} onRetry={() => fetchMetrics()} showDetails={false} />
      )}

      {/* Dashboard Content */}
      {state.data && (
        <>
          {/* Performance Overview */}
          {state.data.performance_metrics && state.data.system_health ? (
            <ErrorBoundary componentName="PerformanceIndicators">
              <PerformanceIndicators
                performanceData={state.data.performance_metrics}
                healthData={state.data.system_health}
                trendData={state.data.trends?.performance_trends}
              />
            </ErrorBoundary>
          ) : (
            <EmptyState
              type="no-metrics"
              title="Performance Data Unavailable"
              description="System performance indicators could not be loaded."
              size="md"
              dataSource={state.dataSource === 'fallback' ? 'fallback' : undefined}
            />
          )}

          {/* Accuracy Analysis */}
          {state.data.forecast_accuracy && state.data.forecast_accuracy.length > 0 ? (
            <ErrorBoundary componentName="AccuracyChart">
              <AccuracyChart
                accuracyData={state.data.forecast_accuracy}
                trendData={state.data.trends?.accuracy_trends}
                selectedHorizons={filter.horizons}
                selectedVariables={filter.variables}
                timeRange={filter.timeRange}
              />
            </ErrorBoundary>
          ) : (
            <EmptyState
              type="no-data"
              title="No Accuracy Data"
              description="Forecast accuracy data is not available for the selected filters."
              size="md"
              dataSource={state.dataSource === 'fallback' ? 'fallback' : undefined}
            />
          )}

          {/* Quick Stats Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-medium text-gray-300">Average Accuracy</h3>
                {state.dataSource === 'fallback' && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-900/50 border border-orange-700 text-orange-300">
                    FALLBACK
                  </span>
                )}
              </div>
              <p className="text-2xl font-bold text-blue-400">
                {state.data.forecast_accuracy?.length > 0 
                  ? (state.data.forecast_accuracy.reduce((sum, a) => sum + (a.accuracy_percent || 0), 0) / state.data.forecast_accuracy.length).toFixed(1)
                  : '0.0'
                }%
              </p>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-medium text-gray-300">System Uptime</h3>
                {state.dataSource === 'fallback' && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-900/50 border border-orange-700 text-orange-300">
                    FALLBACK
                  </span>
                )}
              </div>
              <p className="text-2xl font-bold text-emerald-400">
                {state.data.system_health?.length > 0 
                  ? (state.data.system_health.reduce((sum, h) => sum + (h.uptime_percent || 0), 0) / state.data.system_health.length).toFixed(1)
                  : '0.0'
                }%
              </p>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-medium text-gray-300">Data Coverage</h3>
              </div>
              <div className="flex items-baseline gap-2">
                <p className="text-2xl font-bold text-amber-400">
                  {filter.timeRange}
                </p>
                {state.dataSource === 'cache' && (
                  <span className="text-xs text-blue-400">(cached)</span>
                )}
              </div>
            </div>
          </div>

          {/* Export Options */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-3">Export Options</h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleExport('json')}
                disabled={isExporting}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm transition-colors disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                Export JSON
              </button>
              <button
                onClick={() => handleExport('csv')}
                disabled={isExporting}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded text-sm transition-colors disabled:opacity-50"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            </div>
          </div>
        </>
      )}
    </div>
    </ErrorBoundary>
  );
};

export default MetricsDashboard;