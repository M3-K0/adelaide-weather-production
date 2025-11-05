'use client';

/**
 * ForecastVersions Component
 * =========================
 * 
 * Comprehensive forecast version browser with filtering, search, and management capabilities.
 * Provides the main interface for accessing historical forecasts and version management.
 * 
 * Features:
 * - Paginated version listing with advanced filtering
 * - Real-time search with multiple criteria
 * - Version comparison and analysis tools
 * - Export functionality for historical data
 * - Performance analytics and trends visualization
 * 
 * Author: T-013 Implementation
 * Version: 1.0.0 - Versioned Storage with UI Access
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { format, parseISO, subDays, startOfDay, endOfDay } from 'date-fns';
import {
  Calendar,
  Search,
  Filter,
  Download,
  GitCompare,
  BarChart3,
  Clock,
  Database,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Info,
  Settings,
  Eye,
  ExternalLink,
} from 'lucide-react';

import {
  ForecastVersionSummary,
  VersionListResponse,
  VersionSearchRequest,
  versioningApi,
  versioningUtils,
} from '@/lib/versioningApi';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface FilterState {
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  horizons: string[];
  modelVersions: string[];
  confidenceRange: {
    min: number;
    max: number;
  };
  riskLevels: string[];
  searchQuery: string;
}

interface SortConfig {
  field: 'forecast_time' | 'confidence_score' | 'latency_ms' | 'analog_count';
  direction: 'asc' | 'desc';
}

// ============================================================================
// Main Component
// ============================================================================

export default function ForecastVersions() {
  const queryClient = useQueryClient();

  // State management
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'forecast_time',
    direction: 'desc',
  });

  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    dateRange: {
      start: subDays(new Date(), 7),
      end: new Date(),
    },
    horizons: [],
    modelVersions: [],
    confidenceRange: {
      min: 0,
      max: 1,
    },
    riskLevels: [],
    searchQuery: '',
  });

  // Quick filter presets
  const quickFilters = useMemo(() => [
    {
      label: 'Last 24 Hours',
      onClick: () => setFilters(prev => ({
        ...prev,
        dateRange: {
          start: subDays(new Date(), 1),
          end: new Date(),
        },
      })),
    },
    {
      label: 'Last Week',
      onClick: () => setFilters(prev => ({
        ...prev,
        dateRange: {
          start: subDays(new Date(), 7),
          end: new Date(),
        },
      })),
    },
    {
      label: 'High Confidence',
      onClick: () => setFilters(prev => ({
        ...prev,
        confidenceRange: { min: 0.8, max: 1 },
      })),
    },
    {
      label: 'High Risk',
      onClick: () => setFilters(prev => ({
        ...prev,
        riskLevels: ['high', 'extreme'],
      })),
    },
  ], []);

  // Build query parameters from filters
  const queryParams = useMemo(() => {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: currentPage * pageSize,
    };

    if (filters.dateRange.start) {
      params.start_date = filters.dateRange.start.toISOString();
    }
    if (filters.dateRange.end) {
      params.end_date = filters.dateRange.end.toISOString();
    }

    return params;
  }, [filters, currentPage, pageSize]);

  // Fetch forecast versions
  const {
    data: versionsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<VersionListResponse>({
    queryKey: ['forecast-versions', queryParams],
    queryFn: () => versioningApi.getForecastVersions(queryParams),
    staleTime: 30000, // 30 seconds
  });

  const versions = versionsResponse?.data || [];
  const pagination = versionsResponse?.pagination;

  // Handle version selection
  const handleVersionSelect = useCallback((versionId: string, selected: boolean) => {
    setSelectedVersions(prev => 
      selected 
        ? [...prev, versionId]
        : prev.filter(id => id !== versionId)
    );
  }, []);

  const handleSelectAll = useCallback((selected: boolean) => {
    setSelectedVersions(selected ? versions.map(v => v.version_id) : []);
  }, [versions]);

  // Handle sorting
  const handleSort = useCallback((field: SortConfig['field']) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  // Reset filters
  const resetFilters = useCallback(() => {
    setFilters({
      dateRange: {
        start: subDays(new Date(), 7),
        end: new Date(),
      },
      horizons: [],
      modelVersions: [],
      confidenceRange: { min: 0, max: 1 },
      riskLevels: [],
      searchQuery: '',
    });
    setCurrentPage(0);
  }, []);

  // Handle pagination
  const goToPage = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const totalPages = Math.ceil((pagination?.total_count || 0) / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Forecast Versions</h1>
          <p className="text-gray-600 mt-1">
            Browse and manage historical weather forecasts with version control
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </button>
        </div>
      </div>

      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
        {quickFilters.map((filter, index) => (
          <button
            key={index}
            onClick={filter.onClick}
            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors"
          >
            {filter.label}
          </button>
        ))}
        <button
          onClick={resetFilters}
          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 hover:bg-gray-200 transition-colors"
        >
          Clear All
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showFilters && (
        <FilterPanel
          filters={filters}
          onFiltersChange={setFilters}
          onClose={() => setShowFilters(false)}
        />
      )}

      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search forecast narratives, notes, and metadata..."
          value={filters.searchQuery}
          onChange={(e) => setFilters(prev => ({
            ...prev,
            searchQuery: e.target.value,
          }))}
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Action Bar */}
      {selectedVersions.length > 0 && (
        <ActionBar
          selectedVersions={selectedVersions}
          onClearSelection={() => setSelectedVersions([])}
        />
      )}

      {/* Results Summary */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-600">
              <Database className="h-4 w-4 mr-2" />
              {pagination?.total_count || 0} versions found
            </div>
            {filters.dateRange.start && filters.dateRange.end && (
              <div className="flex items-center text-sm text-gray-600">
                <Calendar className="h-4 w-4 mr-2" />
                {format(filters.dateRange.start, 'MMM d')} - {format(filters.dateRange.end, 'MMM d, yyyy')}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Per page:</label>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="rounded border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error loading forecast versions
              </h3>
              <div className="mt-2 text-sm text-red-700">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Versions Table */}
      {!error && (
        <VersionsTable
          versions={versions}
          isLoading={isLoading}
          selectedVersions={selectedVersions}
          sortConfig={sortConfig}
          onVersionSelect={handleVersionSelect}
          onSelectAll={handleSelectAll}
          onSort={handleSort}
        />
      )}

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalCount={pagination.total_count}
          pageSize={pageSize}
          onPageChange={goToPage}
        />
      )}
    </div>
  );
}

// ============================================================================
// Filter Panel Component
// ============================================================================

interface FilterPanelProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onClose: () => void;
}

function FilterPanel({ filters, onFiltersChange, onClose }: FilterPanelProps) {
  const availableHorizons = ['6h', '12h', '24h', '48h'];
  const availableRiskLevels = ['minimal', 'low', 'moderate', 'high', 'extreme'];

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Advanced Filters</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
        >
          <span className="sr-only">Close</span>
          ×
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Date Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Date Range
          </label>
          <div className="space-y-2">
            <input
              type="date"
              value={filters.dateRange.start ? format(filters.dateRange.start, 'yyyy-MM-dd') : ''}
              onChange={(e) => onFiltersChange({
                ...filters,
                dateRange: {
                  ...filters.dateRange,
                  start: e.target.value ? new Date(e.target.value) : null,
                },
              })}
              className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
            />
            <input
              type="date"
              value={filters.dateRange.end ? format(filters.dateRange.end, 'yyyy-MM-dd') : ''}
              onChange={(e) => onFiltersChange({
                ...filters,
                dateRange: {
                  ...filters.dateRange,
                  end: e.target.value ? new Date(e.target.value) : null,
                },
              })}
              className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Horizons */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Forecast Horizons
          </label>
          <div className="space-y-2">
            {availableHorizons.map((horizon) => (
              <label key={horizon} className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.horizons.includes(horizon)}
                  onChange={(e) => {
                    const newHorizons = e.target.checked
                      ? [...filters.horizons, horizon]
                      : filters.horizons.filter(h => h !== horizon);
                    onFiltersChange({
                      ...filters,
                      horizons: newHorizons,
                    });
                  }}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">{horizon}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Risk Levels */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Risk Levels
          </label>
          <div className="space-y-2">
            {availableRiskLevels.map((level) => (
              <label key={level} className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.riskLevels.includes(level)}
                  onChange={(e) => {
                    const newLevels = e.target.checked
                      ? [...filters.riskLevels, level]
                      : filters.riskLevels.filter(l => l !== level);
                    onFiltersChange({
                      ...filters,
                      riskLevels: newLevels,
                    });
                  }}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className={`ml-2 text-sm capitalize ${versioningUtils.getRiskLevelColor(level)}`}>
                  {level}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Confidence Range */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Confidence Range: {Math.round(filters.confidenceRange.min * 100)}% - {Math.round(filters.confidenceRange.max * 100)}%
          </label>
          <div className="flex items-center space-x-4">
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={filters.confidenceRange.min}
              onChange={(e) => onFiltersChange({
                ...filters,
                confidenceRange: {
                  ...filters.confidenceRange,
                  min: Number(e.target.value),
                },
              })}
              className="flex-1"
            />
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={filters.confidenceRange.max}
              onChange={(e) => onFiltersChange({
                ...filters,
                confidenceRange: {
                  ...filters.confidenceRange,
                  max: Number(e.target.value),
                },
              })}
              className="flex-1"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Action Bar Component
// ============================================================================

interface ActionBarProps {
  selectedVersions: string[];
  onClearSelection: () => void;
}

function ActionBar({ selectedVersions, onClearSelection }: ActionBarProps) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <CheckCircle className="h-5 w-5 text-blue-600 mr-2" />
          <span className="text-sm font-medium text-blue-900">
            {selectedVersions.length} version{selectedVersions.length !== 1 ? 's' : ''} selected
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <button
            className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            disabled={selectedVersions.length < 2}
          >
            <GitCompare className="h-4 w-4 mr-1" />
            Compare
          </button>

          <button className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
            <Download className="h-4 w-4 mr-1" />
            Export
          </button>

          <button
            onClick={onClearSelection}
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            Clear selection
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Versions Table Component
// ============================================================================

interface VersionsTableProps {
  versions: ForecastVersionSummary[];
  isLoading: boolean;
  selectedVersions: string[];
  sortConfig: SortConfig;
  onVersionSelect: (versionId: string, selected: boolean) => void;
  onSelectAll: (selected: boolean) => void;
  onSort: (field: SortConfig['field']) => void;
}

function VersionsTable({
  versions,
  isLoading,
  selectedVersions,
  sortConfig,
  onVersionSelect,
  onSelectAll,
  onSort,
}: VersionsTableProps) {
  const getSortIcon = (field: SortConfig['field']) => {
    if (sortConfig.field !== field) return null;
    return sortConfig.direction === 'desc' ? '↓' : '↑';
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="animate-pulse p-8">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded w-full"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No forecast versions found</h3>
        <p className="text-gray-600">
          Try adjusting your filters or date range to find forecast versions.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left">
              <input
                type="checkbox"
                checked={selectedVersions.length === versions.length}
                onChange={(e) => onSelectAll(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort('forecast_time')}
            >
              Forecast Time {getSortIcon('forecast_time')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Horizon
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort('confidence_score')}
            >
              Confidence {getSortIcon('confidence_score')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Risk Level
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Model
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort('analog_count')}
            >
              Analogs {getSortIcon('analog_count')}
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort('latency_ms')}
            >
              Latency {getSortIcon('latency_ms')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {versions.map((version) => (
            <VersionRow
              key={version.version_id}
              version={version}
              isSelected={selectedVersions.includes(version.version_id)}
              onSelect={(selected) => onVersionSelect(version.version_id, selected)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// Version Row Component
// ============================================================================

interface VersionRowProps {
  version: ForecastVersionSummary;
  isSelected: boolean;
  onSelect: (selected: boolean) => void;
}

function VersionRow({ version, isSelected, onSelect }: VersionRowProps) {
  const forecastDate = parseISO(version.forecast_time);
  const timeAgo = versioningUtils.getTimeAgo(version.forecast_time);

  return (
    <tr className={`hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}>
      <td className="px-6 py-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(e.target.checked)}
          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">
          {format(forecastDate, 'MMM d, yyyy HH:mm')}
        </div>
        <div className="text-sm text-gray-500">{timeAgo}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {version.horizon}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {version.confidence_score ? (
          <div className="text-sm text-gray-900">
            {Math.round(version.confidence_score * 100)}%
          </div>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {version.risk_level ? (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${versioningUtils.getRiskLevelColor(version.risk_level)}`}>
            {version.risk_level}
          </span>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {version.model_version}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {version.analog_count || '—'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {version.latency_ms ? `${version.latency_ms}ms` : '—'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
        <div className="flex items-center space-x-2">
          <button className="text-blue-600 hover:text-blue-900">
            <Eye className="h-4 w-4" />
          </button>
          <button className="text-gray-400 hover:text-gray-600">
            <ExternalLink className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ============================================================================
// Pagination Component
// ============================================================================

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

function Pagination({
  currentPage,
  totalPages,
  totalCount,
  pageSize,
  onPageChange,
}: PaginationProps) {
  const startRecord = currentPage * pageSize + 1;
  const endRecord = Math.min((currentPage + 1) * pageSize, totalCount);

  return (
    <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6 rounded-lg border border-gray-200">
      <div className="flex-1 flex justify-between sm:hidden">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 0}
          className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages - 1}
          className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Next
        </button>
      </div>

      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{startRecord}</span> to{' '}
            <span className="font-medium">{endRecord}</span> of{' '}
            <span className="font-medium">{totalCount}</span> results
          </p>
        </div>

        <div>
          <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 0}
              className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>

            {[...Array(Math.min(totalPages, 7))].map((_, index) => {
              let pageNum;
              if (totalPages <= 7) {
                pageNum = index;
              } else if (currentPage < 3) {
                pageNum = index;
              } else if (currentPage >= totalPages - 3) {
                pageNum = totalPages - 7 + index;
              } else {
                pageNum = currentPage - 3 + index;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                    currentPage === pageNum
                      ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                      : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {pageNum + 1}
                </button>
              );
            })}

            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages - 1}
              className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
}