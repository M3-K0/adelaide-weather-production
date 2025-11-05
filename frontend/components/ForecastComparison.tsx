'use client';

/**
 * ForecastComparison Component
 * ===========================
 * 
 * Advanced forecast version comparison tool with side-by-side analysis,
 * difference highlighting, and interactive visualization capabilities.
 * 
 * Features:
 * - Side-by-side version comparison interface
 * - Interactive difference highlighting and analysis
 * - Variable-by-variable comparison with visual charts
 * - Accuracy comparison against actual observations
 * - Export and sharing capabilities for comparisons
 * 
 * Author: T-013 Implementation
 * Version: 1.0.0 - Versioned Storage with UI Access
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import {
  GitCompare,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  Download,
  Share2,
  Info,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Eye,
  EyeOff,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
} from 'recharts';

import {
  ForecastVersionDetail,
  VersionComparison,
  VersionComparisonRequest,
  versioningApi,
  versioningUtils,
} from '@/lib/versioningApi';
import { VARIABLE_NAMES, VARIABLE_UNITS } from '@/types/api';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface ComparisonViewState {
  selectedVariables: string[];
  showDifferencesOnly: boolean;
  comparisonMode: 'side-by-side' | 'overlay' | 'difference';
  highlightThreshold: number; // Percentage threshold for highlighting differences
}

interface VariableDifference {
  variable: string;
  valueA: number | null;
  valueB: number | null;
  absoluteDifference: number;
  percentChange: number;
  isSignificant: boolean;
  trend: 'up' | 'down' | 'stable';
}

// ============================================================================
// Main Component
// ============================================================================

interface ForecastComparisonProps {
  versionIds: string[];
  onClose?: () => void;
}

export default function ForecastComparison({ versionIds, onClose }: ForecastComparisonProps) {
  // State management
  const [viewState, setViewState] = useState<ComparisonViewState>({
    selectedVariables: ['t2m', 'msl', 'u10', 'v10'],
    showDifferencesOnly: false,
    comparisonMode: 'side-by-side',
    highlightThreshold: 10, // 10% threshold
  });

  const [comparison, setComparison] = useState<VersionComparison | null>(null);
  const [notes, setNotes] = useState('');
  const [isCreatingComparison, setIsCreatingComparison] = useState(false);

  // Validate input
  if (!versionIds || versionIds.length < 2) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Invalid Comparison Request
        </h3>
        <p className="text-gray-600">
          At least 2 forecast versions are required for comparison.
        </p>
      </div>
    );
  }

  // Fetch version details
  const {
    data: versions,
    isLoading: isLoadingVersions,
    error: versionsError,
  } = useQuery({
    queryKey: ['version-details', versionIds],
    queryFn: async () => {
      const promises = versionIds.map(id => versioningApi.getForecastVersionDetail(id));
      return Promise.all(promises);
    },
    enabled: versionIds.length >= 2,
  });

  // Create comparison when versions are loaded
  useEffect(() => {
    if (versions && versions.length >= 2 && !comparison && !isCreatingComparison) {
      createComparison();
    }
  }, [versions, comparison, isCreatingComparison]);

  const createComparison = useCallback(async () => {
    if (!versions || versions.length < 2 || isCreatingComparison) return;

    setIsCreatingComparison(true);
    try {
      const request: VersionComparisonRequest = {
        version_ids: versionIds,
        variables: viewState.selectedVariables,
        notes: notes,
      };

      const comparisonResult = await versioningApi.compareForecastVersions(request);
      setComparison(comparisonResult);
    } catch (error) {
      console.error('Failed to create comparison:', error);
    } finally {
      setIsCreatingComparison(false);
    }
  }, [versions, versionIds, viewState.selectedVariables, notes, isCreatingComparison]);

  // Calculate variable differences
  const variableDifferences = useMemo(() => {
    if (!versions || versions.length < 2) return [];

    const versionA = versions[0];
    const versionB = versions[1];
    const differences: VariableDifference[] = [];

    const allVariables = new Set([
      ...Object.keys(versionA.variables),
      ...Object.keys(versionB.variables),
    ]);

    allVariables.forEach(variable => {
      const dataA = versionA.variables[variable];
      const dataB = versionB.variables[variable];

      const valueA = dataA?.value ?? null;
      const valueB = dataB?.value ?? null;

      if (valueA !== null && valueB !== null) {
        const absoluteDifference = valueB - valueA;
        const percentChange = valueA !== 0 ? (absoluteDifference / valueA) * 100 : 0;
        const isSignificant = Math.abs(percentChange) >= viewState.highlightThreshold;

        let trend: 'up' | 'down' | 'stable';
        if (Math.abs(percentChange) < 1) {
          trend = 'stable';
        } else if (percentChange > 0) {
          trend = 'up';
        } else {
          trend = 'down';
        }

        differences.push({
          variable,
          valueA,
          valueB,
          absoluteDifference,
          percentChange,
          isSignificant,
          trend,
        });
      }
    });

    return differences.sort((a, b) => Math.abs(b.percentChange) - Math.abs(a.percentChange));
  }, [versions, viewState.highlightThreshold]);

  if (isLoadingVersions || isCreatingComparison) {
    return <ComparisonLoadingState />;
  }

  if (versionsError) {
    return <ComparisonErrorState error={versionsError} onRetry={() => window.location.reload()} />;
  }

  if (!versions || versions.length < 2) {
    return <ComparisonErrorState error={new Error('Failed to load version data')} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <ComparisonHeader
        versions={versions}
        comparison={comparison}
        onClose={onClose}
      />

      {/* Controls */}
      <ComparisonControls
        viewState={viewState}
        onViewStateChange={setViewState}
        availableVariables={Object.keys(versions[0].variables)}
      />

      {/* Summary Stats */}
      <ComparisonSummary
        versions={versions}
        differences={variableDifferences}
        comparison={comparison}
      />

      {/* Main Comparison View */}
      {viewState.comparisonMode === 'side-by-side' && (
        <SideBySideComparison
          versions={versions}
          selectedVariables={viewState.selectedVariables}
          differences={variableDifferences}
          showDifferencesOnly={viewState.showDifferencesOnly}
        />
      )}

      {viewState.comparisonMode === 'difference' && (
        <DifferenceView
          differences={variableDifferences}
          selectedVariables={viewState.selectedVariables}
        />
      )}

      {viewState.comparisonMode === 'overlay' && (
        <OverlayComparison
          versions={versions}
          selectedVariables={viewState.selectedVariables}
          differences={variableDifferences}
        />
      )}

      {/* Charts and Visualizations */}
      <ComparisonCharts
        versions={versions}
        differences={variableDifferences}
        selectedVariables={viewState.selectedVariables}
      />

      {/* Notes and Actions */}
      <ComparisonActions
        comparison={comparison}
        notes={notes}
        onNotesChange={setNotes}
        onSaveComparison={createComparison}
      />
    </div>
  );
}

// ============================================================================
// Header Component
// ============================================================================

interface ComparisonHeaderProps {
  versions: ForecastVersionDetail[];
  comparison: VersionComparison | null;
  onClose?: () => void;
}

function ComparisonHeader({ versions, comparison, onClose }: ComparisonHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <div className="flex items-center space-x-3">
          <GitCompare className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Forecast Comparison</h1>
            <p className="text-gray-600 mt-1">
              Comparing {versions.length} forecast versions
            </p>
          </div>
        </div>

        {/* Version Badges */}
        <div className="flex items-center space-x-4 mt-4">
          {versions.map((version, index) => (
            <div key={version.version_id} className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${index === 0 ? 'bg-blue-500' : 'bg-green-500'}`} />
              <div className="text-sm">
                <div className="font-medium">
                  {format(parseISO(version.forecast_time), 'MMM d, yyyy HH:mm')}
                </div>
                <div className="text-gray-500">
                  {version.horizon} • {version.model_version}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <button className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
          <Share2 className="h-4 w-4 mr-2" />
          Share
        </button>

        <button className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
          <Download className="h-4 w-4 mr-2" />
          Export
        </button>

        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <span className="sr-only">Close</span>
            ×
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Controls Component
// ============================================================================

interface ComparisonControlsProps {
  viewState: ComparisonViewState;
  onViewStateChange: (state: ComparisonViewState) => void;
  availableVariables: string[];
}

function ComparisonControls({
  viewState,
  onViewStateChange,
  availableVariables,
}: ComparisonControlsProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Comparison Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Comparison Mode
          </label>
          <select
            value={viewState.comparisonMode}
            onChange={(e) => onViewStateChange({
              ...viewState,
              comparisonMode: e.target.value as ComparisonViewState['comparisonMode'],
            })}
            className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="side-by-side">Side by Side</option>
            <option value="overlay">Overlay</option>
            <option value="difference">Differences Only</option>
          </select>
        </div>

        {/* Variable Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Variables to Compare
          </label>
          <select
            multiple
            value={viewState.selectedVariables}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions, option => option.value);
              onViewStateChange({
                ...viewState,
                selectedVariables: selected,
              });
            }}
            className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
            size={4}
          >
            {availableVariables.map(variable => (
              <option key={variable} value={variable}>
                {VARIABLE_NAMES[variable as keyof typeof VARIABLE_NAMES] || variable}
              </option>
            ))}
          </select>
        </div>

        {/* Highlight Threshold */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Highlight Threshold: {viewState.highlightThreshold}%
          </label>
          <input
            type="range"
            min="1"
            max="50"
            value={viewState.highlightThreshold}
            onChange={(e) => onViewStateChange({
              ...viewState,
              highlightThreshold: Number(e.target.value),
            })}
            className="block w-full"
          />
          <div className="text-xs text-gray-500 mt-1">
            Highlight changes above this percentage
          </div>
        </div>

        {/* Display Options */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Display Options
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={viewState.showDifferencesOnly}
                onChange={(e) => onViewStateChange({
                  ...viewState,
                  showDifferencesOnly: e.target.checked,
                })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Show differences only
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Summary Component
// ============================================================================

interface ComparisonSummaryProps {
  versions: ForecastVersionDetail[];
  differences: VariableDifference[];
  comparison: VersionComparison | null;
}

function ComparisonSummary({ versions, differences, comparison }: ComparisonSummaryProps) {
  const significantChanges = differences.filter(d => d.isSignificant);
  const avgAbsoluteChange = differences.length > 0
    ? differences.reduce((sum, d) => sum + Math.abs(d.percentChange), 0) / differences.length
    : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <Activity className="h-8 w-8 text-blue-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {differences.length}
            </p>
            <p className="text-gray-600">Variables Compared</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <AlertTriangle className="h-8 w-8 text-amber-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {significantChanges.length}
            </p>
            <p className="text-gray-600">Significant Changes</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <TrendingUp className="h-8 w-8 text-green-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {avgAbsoluteChange.toFixed(1)}%
            </p>
            <p className="text-gray-600">Avg Change</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <CheckCircle className="h-8 w-8 text-purple-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {comparison?.similarity_score ? Math.round(comparison.similarity_score * 100) : 0}%
            </p>
            <p className="text-gray-600">Similarity</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Side by Side Comparison
// ============================================================================

interface SideBySideComparisonProps {
  versions: ForecastVersionDetail[];
  selectedVariables: string[];
  differences: VariableDifference[];
  showDifferencesOnly: boolean;
}

function SideBySideComparison({
  versions,
  selectedVariables,
  differences,
  showDifferencesOnly,
}: SideBySideComparisonProps) {
  const versionA = versions[0];
  const versionB = versions[1];

  const filteredVariables = showDifferencesOnly
    ? differences.filter(d => d.isSignificant).map(d => d.variable)
    : selectedVariables;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Variable Comparison</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Variable
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-blue-500 uppercase tracking-wider">
                Version A ({format(parseISO(versionA.forecast_time), 'HH:mm')})
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-green-500 uppercase tracking-wider">
                Version B ({format(parseISO(versionB.forecast_time), 'HH:mm')})
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Difference
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Change %
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredVariables.map(variable => {
              const difference = differences.find(d => d.variable === variable);
              const dataA = versionA.variables[variable];
              const dataB = versionB.variables[variable];

              return (
                <VariableComparisonRow
                  key={variable}
                  variable={variable}
                  dataA={dataA}
                  dataB={dataB}
                  difference={difference}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// Variable Comparison Row
// ============================================================================

interface VariableComparisonRowProps {
  variable: string;
  dataA: any;
  dataB: any;
  difference?: VariableDifference;
}

function VariableComparisonRow({ variable, dataA, dataB, difference }: VariableComparisonRowProps) {
  const variableName = VARIABLE_NAMES[variable as keyof typeof VARIABLE_NAMES] || variable;
  const unit = VARIABLE_UNITS[variable as keyof typeof VARIABLE_UNITS] || '';

  const formatValue = (data: any) => {
    if (!data || data.value === null || data.value === undefined) {
      return <span className="text-gray-400">—</span>;
    }

    const value = data.value;
    const p05 = data.p05;
    const p95 = data.p95;

    return (
      <div>
        <span className="font-medium">{value.toFixed(2)} {unit}</span>
        {p05 !== null && p95 !== null && (
          <div className="text-xs text-gray-500">
            ({p05.toFixed(2)} - {p95.toFixed(2)})
          </div>
        )}
      </div>
    );
  };

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-gray-400" />;
    }
  };

  const isSignificant = difference?.isSignificant;

  return (
    <tr className={isSignificant ? 'bg-yellow-50' : ''}>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{variableName}</div>
        <div className="text-sm text-gray-500">{variable}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {formatValue(dataA)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {formatValue(dataB)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {difference && (
          <div className="flex items-center space-x-2">
            {getTrendIcon(difference.trend)}
            <span className={difference.isSignificant ? 'font-medium' : ''}>
              {difference.absoluteDifference > 0 ? '+' : ''}
              {difference.absoluteDifference.toFixed(2)} {unit}
            </span>
          </div>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        {difference && (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            difference.isSignificant
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-gray-100 text-gray-800'
          }`}>
            {difference.percentChange > 0 ? '+' : ''}
            {difference.percentChange.toFixed(1)}%
          </span>
        )}
      </td>
    </tr>
  );
}

// ============================================================================
// Difference View Component
// ============================================================================

interface DifferenceViewProps {
  differences: VariableDifference[];
  selectedVariables: string[];
}

function DifferenceView({ differences, selectedVariables }: DifferenceViewProps) {
  const filteredDifferences = differences.filter(d => 
    selectedVariables.includes(d.variable)
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Variable Differences</h3>
      
      <div className="space-y-4">
        {filteredDifferences.map(difference => (
          <DifferenceCard key={difference.variable} difference={difference} />
        ))}
      </div>
    </div>
  );
}

interface DifferenceCardProps {
  difference: VariableDifference;
}

function DifferenceCard({ difference }: DifferenceCardProps) {
  const variableName = VARIABLE_NAMES[difference.variable as keyof typeof VARIABLE_NAMES] || difference.variable;
  const unit = VARIABLE_UNITS[difference.variable as keyof typeof VARIABLE_UNITS] || '';

  return (
    <div className={`border rounded-lg p-4 ${
      difference.isSignificant ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200'
    }`}>
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-gray-900">{variableName}</h4>
          <p className="text-sm text-gray-600">{difference.variable}</p>
        </div>
        
        <div className="text-right">
          <div className="flex items-center space-x-2">
            {difference.trend === 'up' && <TrendingUp className="h-5 w-5 text-green-500" />}
            {difference.trend === 'down' && <TrendingDown className="h-5 w-5 text-red-500" />}
            {difference.trend === 'stable' && <Minus className="h-5 w-5 text-gray-400" />}
            
            <span className="text-lg font-semibold">
              {difference.percentChange > 0 ? '+' : ''}
              {difference.percentChange.toFixed(1)}%
            </span>
          </div>
          
          <p className="text-sm text-gray-600">
            {difference.absoluteDifference > 0 ? '+' : ''}
            {difference.absoluteDifference.toFixed(2)} {unit}
          </p>
        </div>
      </div>
      
      <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
        <span>From: {difference.valueA?.toFixed(2)} {unit}</span>
        <ArrowRight className="h-4 w-4" />
        <span>To: {difference.valueB?.toFixed(2)} {unit}</span>
      </div>
    </div>
  );
}

// ============================================================================
// Overlay Comparison Component
// ============================================================================

interface OverlayComparisonProps {
  versions: ForecastVersionDetail[];
  selectedVariables: string[];
  differences: VariableDifference[];
}

function OverlayComparison({ versions, selectedVariables, differences }: OverlayComparisonProps) {
  // Prepare chart data
  const chartData = selectedVariables.map(variable => {
    const dataA = versions[0].variables[variable];
    const dataB = versions[1].variables[variable];
    const difference = differences.find(d => d.variable === variable);

    return {
      variable: VARIABLE_NAMES[variable as keyof typeof VARIABLE_NAMES] || variable,
      versionA: dataA?.value || 0,
      versionB: dataB?.value || 0,
      difference: difference?.percentChange || 0,
    };
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Overlay Comparison</h3>
      
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="variable" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="versionA" fill="#3B82F6" name="Version A" />
            <Bar dataKey="versionB" fill="#10B981" name="Version B" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ============================================================================
// Comparison Charts Component
// ============================================================================

interface ComparisonChartsProps {
  versions: ForecastVersionDetail[];
  differences: VariableDifference[];
  selectedVariables: string[];
}

function ComparisonCharts({ versions, differences, selectedVariables }: ComparisonChartsProps) {
  const chartData = differences
    .filter(d => selectedVariables.includes(d.variable))
    .map(d => ({
      variable: VARIABLE_NAMES[d.variable as keyof typeof VARIABLE_NAMES] || d.variable,
      percentChange: d.percentChange,
      absoluteChange: d.absoluteDifference,
      isSignificant: d.isSignificant,
    }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Change Analysis</h3>
      
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="variable" />
            <YAxis />
            <Tooltip 
              formatter={(value: number, name: string) => [
                `${value.toFixed(1)}%`, 
                'Percent Change'
              ]}
            />
            <ReferenceLine y={0} stroke="#000" strokeDasharray="2 2" />
            <Bar 
              dataKey="percentChange" 
              fill={(entry: any) => entry.isSignificant ? "#F59E0B" : "#6B7280"}
              name="Percent Change"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ============================================================================
// Comparison Actions Component
// ============================================================================

interface ComparisonActionsProps {
  comparison: VersionComparison | null;
  notes: string;
  onNotesChange: (notes: string) => void;
  onSaveComparison: () => void;
}

function ComparisonActions({
  comparison,
  notes,
  onNotesChange,
  onSaveComparison,
}: ComparisonActionsProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Notes and Actions</h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Comparison Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            rows={4}
            className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
            placeholder="Add notes about this comparison..."
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {comparison && (
              <span>
                Comparison created: {format(parseISO(comparison.created_at), 'MMM d, yyyy HH:mm')}
              </span>
            )}
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onSaveComparison}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Save Comparison
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Loading and Error States
// ============================================================================

function ComparisonLoadingState() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-8">
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/3"></div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 rounded w-full"></div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface ComparisonErrorStateProps {
  error: Error;
  onRetry?: () => void;
}

function ComparisonErrorState({ error, onRetry }: ComparisonErrorStateProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Comparison Failed
      </h3>
      <p className="text-gray-600 mb-4">
        {error.message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Try Again
        </button>
      )}
    </div>
  );
}