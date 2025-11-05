/**
 * AccuracyChart Component
 * 
 * Displays forecast accuracy metrics with interactive charts showing
 * accuracy trends, bias indicators, and Mean Absolute Error (MAE) over time.
 */

'use client';

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
} from 'recharts';
import { ForecastHorizon, WeatherVariable, VARIABLE_NAMES, VARIABLE_UNITS } from '@/types/api';
import { AccuracyMetric, TrendDataPoint } from '@/lib/metricsApi';
import { format } from 'date-fns';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface AccuracyChartProps {
  accuracyData: AccuracyMetric[];
  trendData: TrendDataPoint[];
  selectedHorizons: ForecastHorizon[];
  selectedVariables: WeatherVariable[];
  timeRange: string;
  className?: string;
}

interface ProcessedAccuracyData {
  horizon: string;
  variable: string;
  variableName: string;
  mae: number;
  bias: number;
  accuracy: number;
  confidence: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
}

interface ProcessedTrendData {
  timestamp: string;
  time: string;
  accuracy: number;
  mae: number;
  confidence: number;
}

// ============================================================================
// Chart Configuration
// ============================================================================

const CHART_COLORS = {
  accuracy: '#10b981', // emerald-500
  mae: '#f59e0b', // amber-500
  bias: '#ef4444', // red-500
  confidence: '#3b82f6', // blue-500
  grid: '#374151', // gray-700
  text: '#d1d5db', // gray-300
};

const ACCURACY_THRESHOLDS = {
  excellent: 95,
  good: 85,
  fair: 75,
  poor: 0,
};

// ============================================================================
// Helper Functions
// ============================================================================

const getAccuracyStatus = (accuracy: number): 'excellent' | 'good' | 'fair' | 'poor' => {
  if (accuracy >= ACCURACY_THRESHOLDS.excellent) return 'excellent';
  if (accuracy >= ACCURACY_THRESHOLDS.good) return 'good';
  if (accuracy >= ACCURACY_THRESHOLDS.fair) return 'fair';
  return 'poor';
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'excellent': return '#10b981'; // emerald-500
    case 'good': return '#3b82f6'; // blue-500
    case 'fair': return '#f59e0b'; // amber-500
    case 'poor': return '#ef4444'; // red-500
    default: return '#6b7280'; // gray-500
  }
};

const formatTooltipValue = (value: number, name: string): [string, string] => {
  switch (name) {
    case 'accuracy':
      return [`${value.toFixed(1)}%`, 'Accuracy'];
    case 'mae':
      return [value.toFixed(2), 'MAE'];
    case 'bias':
      return [value.toFixed(2), 'Bias'];
    case 'confidence':
      return [`${value.toFixed(1)}%`, 'Confidence'];
    default:
      return [value.toFixed(1), name];
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
              {entry.name === 'accuracy' || entry.name === 'confidence' ? '%' : ''}
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

const AccuracyChart: React.FC<AccuracyChartProps> = ({
  accuracyData,
  trendData,
  selectedHorizons,
  selectedVariables,
  timeRange,
  className = '',
}) => {
  const [chartType, setChartType] = useState<'accuracy' | 'mae' | 'bias'>('accuracy');
  const [showTrend, setShowTrend] = useState(true);

  // Process accuracy data for charts
  const processedAccuracyData = useMemo(() => {
    return accuracyData
      .filter(metric => 
        selectedHorizons.includes(metric.horizon) && 
        selectedVariables.includes(metric.variable)
      )
      .map((metric): ProcessedAccuracyData => ({
        horizon: metric.horizon,
        variable: metric.variable,
        variableName: VARIABLE_NAMES[metric.variable] || metric.variable,
        mae: metric.mae,
        bias: metric.bias,
        accuracy: metric.accuracy_percent,
        confidence: metric.confidence_interval,
        status: getAccuracyStatus(metric.accuracy_percent),
      }));
  }, [accuracyData, selectedHorizons, selectedVariables]);

  // Process trend data for time series
  const processedTrendData = useMemo(() => {
    return trendData.map((point): ProcessedTrendData => ({
      timestamp: point.timestamp,
      time: format(new Date(point.timestamp), 'MMM dd HH:mm'),
      accuracy: point.value,
      mae: point.value * 0.02, // Simulated MAE based on accuracy
      confidence: point.value * 0.9, // Simulated confidence
    }));
  }, [trendData]);

  // Group data by horizon for better visualization
  const dataByHorizon = useMemo(() => {
    const grouped = processedAccuracyData.reduce((acc, item) => {
      if (!acc[item.horizon]) {
        acc[item.horizon] = [];
      }
      acc[item.horizon].push(item);
      return acc;
    }, {} as Record<string, ProcessedAccuracyData[]>);

    return grouped;
  }, [processedAccuracyData]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Chart Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setChartType('accuracy')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              chartType === 'accuracy'
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Accuracy %
          </button>
          <button
            onClick={() => setChartType('mae')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              chartType === 'mae'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            MAE
          </button>
          <button
            onClick={() => setChartType('bias')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              chartType === 'bias'
                ? 'bg-red-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Bias
          </button>
        </div>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={showTrend}
            onChange={(e) => setShowTrend(e.target.checked)}
            className="rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <span className="text-sm text-gray-300">Show Trend</span>
        </label>
      </div>

      {/* Trend Chart */}
      {showTrend && processedTrendData.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            Accuracy Trends - Last {timeRange}
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={processedTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                <XAxis
                  dataKey="time"
                  stroke={CHART_COLORS.text}
                  fontSize={12}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke={CHART_COLORS.text} fontSize={12} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                
                {chartType === 'accuracy' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="accuracy"
                      stroke={CHART_COLORS.accuracy}
                      strokeWidth={2}
                      dot={{ fill: CHART_COLORS.accuracy, r: 3 }}
                      name="Accuracy"
                    />
                    <ReferenceLine y={85} stroke={CHART_COLORS.bias} strokeDasharray="5 5" />
                    <ReferenceLine y={95} stroke={CHART_COLORS.accuracy} strokeDasharray="5 5" />
                  </>
                )}
                
                {chartType === 'mae' && (
                  <Line
                    type="monotone"
                    dataKey="mae"
                    stroke={CHART_COLORS.mae}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS.mae, r: 3 }}
                    name="MAE"
                  />
                )}
                
                {chartType === 'bias' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="mae"
                      stroke={CHART_COLORS.bias}
                      strokeWidth={2}
                      dot={{ fill: CHART_COLORS.bias, r: 3 }}
                      name="Bias"
                    />
                    <ReferenceLine y={0} stroke={CHART_COLORS.text} strokeDasharray="2 2" />
                  </>
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Accuracy by Horizon Charts */}
      {Object.entries(dataByHorizon).map(([horizon, data]) => (
        <div key={horizon} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            {chartType.toUpperCase()} by Variable - {horizon}
          </h3>
          
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                <XAxis
                  dataKey="variableName"
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
                
                {chartType === 'accuracy' && (
                  <>
                    <Bar
                      dataKey="accuracy"
                      fill={CHART_COLORS.accuracy}
                      name="Accuracy %"
                      radius={[4, 4, 0, 0]}
                    />
                    <ReferenceLine y={85} stroke={CHART_COLORS.bias} strokeDasharray="5 5" />
                    <ReferenceLine y={95} stroke={CHART_COLORS.accuracy} strokeDasharray="5 5" />
                  </>
                )}
                
                {chartType === 'mae' && (
                  <Bar
                    dataKey="mae"
                    fill={CHART_COLORS.mae}
                    name="MAE"
                    radius={[4, 4, 0, 0]}
                  />
                )}
                
                {chartType === 'bias' && (
                  <>
                    <Bar
                      dataKey="bias"
                      fill={CHART_COLORS.bias}
                      name="Bias"
                      radius={[4, 4, 0, 0]}
                    />
                    <ReferenceLine y={0} stroke={CHART_COLORS.text} strokeDasharray="2 2" />
                  </>
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Status Indicators */}
          <div className="mt-4 flex flex-wrap gap-2">
            {data.map((item) => (
              <div
                key={`${item.variable}-${item.horizon}`}
                className="flex items-center gap-2 px-2 py-1 bg-gray-700 rounded-md"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getStatusColor(item.status) }}
                />
                <span className="text-sm text-gray-300">
                  {item.variableName}
                </span>
                <span className="text-sm text-white font-medium">
                  {chartType === 'accuracy' ? `${item.accuracy.toFixed(1)}%` :
                   chartType === 'mae' ? item.mae.toFixed(2) :
                   item.bias.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Summary Statistics */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Summary Statistics</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-700 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Average Accuracy</h4>
            <p className="text-2xl font-bold text-emerald-400">
              {processedAccuracyData.length > 0 
                ? (processedAccuracyData.reduce((sum, item) => sum + item.accuracy, 0) / processedAccuracyData.length).toFixed(1)
                : '0.0'
              }%
            </p>
          </div>
          
          <div className="bg-gray-700 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Average MAE</h4>
            <p className="text-2xl font-bold text-amber-400">
              {processedAccuracyData.length > 0 
                ? (processedAccuracyData.reduce((sum, item) => sum + item.mae, 0) / processedAccuracyData.length).toFixed(2)
                : '0.00'
              }
            </p>
          </div>
          
          <div className="bg-gray-700 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Average Bias</h4>
            <p className="text-2xl font-bold text-blue-400">
              {processedAccuracyData.length > 0 
                ? (processedAccuracyData.reduce((sum, item) => sum + Math.abs(item.bias), 0) / processedAccuracyData.length).toFixed(2)
                : '0.00'
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccuracyChart;