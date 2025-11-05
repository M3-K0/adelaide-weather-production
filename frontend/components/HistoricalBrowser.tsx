'use client';

/**
 * HistoricalBrowser Component
 * ==========================
 * 
 * Advanced historical forecast browser with calendar navigation, search capabilities,
 * and timeline visualization for exploring forecast evolution over time.
 * 
 * Features:
 * - Interactive calendar-based navigation
 * - Advanced search and filtering capabilities
 * - Timeline visualization of forecast evolution
 * - Detailed forecast history with version tracking
 * - Export functionality for historical analysis
 * 
 * Author: T-013 Implementation
 * Version: 1.0.0 - Versioned Storage with UI Access
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  format, 
  parseISO, 
  startOfMonth, 
  endOfMonth, 
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  startOfDay,
  endOfDay,
  subDays,
  addDays,
} from 'date-fns';
import {
  Calendar,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  TrendingUp,
  BarChart3,
  Download,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  AlertCircle,
  CheckCircle,
  Info,
  Layers,
  Map,
  Activity,
  Zap,
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
  Area,
  AreaChart,
  ScatterChart,
  Scatter,
} from 'recharts';

import {
  ForecastVersionSummary,
  VersionSearchRequest,
  VersionAnalytics,
  versioningApi,
  versioningUtils,
} from '@/lib/versioningApi';
import { VARIABLE_NAMES, VARIABLE_UNITS } from '@/types/api';

// ============================================================================
// Types and Interfaces
// ============================================================================

interface CalendarState {
  currentMonth: Date;
  selectedDate: Date | null;
  selectedDateRange: {
    start: Date | null;
    end: Date | null;
  };
  viewMode: 'calendar' | 'timeline' | 'list';
}

interface SearchState {
  query: string;
  horizons: string[];
  variables: string[];
  confidenceRange: [number, number];
  riskLevels: string[];
  modelVersions: string[];
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}

interface ForecastDayData {
  date: string;
  versions: ForecastVersionSummary[];
  count: number;
  avgConfidence: number;
  riskDistribution: Record<string, number>;
}

// ============================================================================
// Main Component
// ============================================================================

export default function HistoricalBrowser() {
  // State management
  const [calendarState, setCalendarState] = useState<CalendarState>({
    currentMonth: new Date(),
    selectedDate: null,
    selectedDateRange: { start: null, end: null },
    viewMode: 'calendar',
  });

  const [searchState, setSearchState] = useState<SearchState>({
    query: '',
    horizons: [],
    variables: [],
    confidenceRange: [0, 1],
    riskLevels: [],
    modelVersions: [],
    dateRange: {
      start: subDays(new Date(), 30),
      end: new Date(),
    },
  });

  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);

  // Calendar data calculation
  const calendarDays = useMemo(() => {
    const start = startOfMonth(calendarState.currentMonth);
    const end = endOfMonth(calendarState.currentMonth);
    return eachDayOfInterval({ start, end });
  }, [calendarState.currentMonth]);

  // Build search parameters
  const searchParams = useMemo((): VersionSearchRequest => {
    return {
      query: searchState.query || undefined,
      start_date: searchState.dateRange.start?.toISOString(),
      end_date: searchState.dateRange.end?.toISOString(),
      horizons: searchState.horizons.length > 0 ? searchState.horizons : undefined,
      confidence_min: searchState.confidenceRange[0],
      confidence_max: searchState.confidenceRange[1],
      risk_levels: searchState.riskLevels.length > 0 ? searchState.riskLevels : undefined,
      variables: searchState.variables.length > 0 ? searchState.variables : undefined,
      limit: 500, // Large limit for calendar view
    };
  }, [searchState]);

  // Fetch historical data
  const {
    data: searchResults,
    isLoading: isLoadingSearch,
    error: searchError,
  } = useQuery({
    queryKey: ['historical-search', searchParams],
    queryFn: () => versioningApi.searchForecastVersions(searchParams),
    staleTime: 60000, // 1 minute
  });

  // Fetch analytics data
  const {
    data: analytics,
    isLoading: isLoadingAnalytics,
  } = useQuery({
    queryKey: ['version-analytics', 30],
    queryFn: () => versioningApi.getVersionAnalytics(30),
    staleTime: 300000, // 5 minutes
  });

  // Group versions by date for calendar display
  const versionsByDate = useMemo(() => {
    if (!searchResults?.data) return new Map<string, ForecastDayData>();

    const grouped = new Map<string, ForecastDayData>();

    searchResults.data.forEach(version => {
      const dateKey = format(parseISO(version.forecast_time), 'yyyy-MM-dd');
      
      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, {
          date: dateKey,
          versions: [],
          count: 0,
          avgConfidence: 0,
          riskDistribution: {},
        });
      }

      const dayData = grouped.get(dateKey)!;
      dayData.versions.push(version);
      dayData.count++;

      // Update confidence average
      if (version.confidence_score) {
        const totalConfidence = dayData.avgConfidence * (dayData.count - 1) + version.confidence_score;
        dayData.avgConfidence = totalConfidence / dayData.count;
      }

      // Update risk distribution
      if (version.risk_level) {
        dayData.riskDistribution[version.risk_level] = 
          (dayData.riskDistribution[version.risk_level] || 0) + 1;
      }
    });

    return grouped;
  }, [searchResults]);

  // Handle date selection
  const handleDateSelect = useCallback((date: Date) => {
    setCalendarState(prev => ({
      ...prev,
      selectedDate: date,
    }));

    // Update search to focus on selected date
    setSearchState(prev => ({
      ...prev,
      dateRange: {
        start: startOfDay(date),
        end: endOfDay(date),
      },
    }));
  }, []);

  // Handle date range selection
  const handleDateRangeSelect = useCallback((start: Date | null, end: Date | null) => {
    setCalendarState(prev => ({
      ...prev,
      selectedDateRange: { start, end },
    }));

    if (start && end) {
      setSearchState(prev => ({
        ...prev,
        dateRange: { start, end },
      }));
    }
  }, []);

  // Navigate calendar months
  const navigateMonth = useCallback((direction: 'prev' | 'next') => {
    setCalendarState(prev => ({
      ...prev,
      currentMonth: direction === 'prev' 
        ? subMonths(prev.currentMonth, 1)
        : addMonths(prev.currentMonth, 1),
    }));
  }, []);

  // Quick date filters
  const quickDateFilters = useMemo(() => [
    {
      label: 'Today',
      onClick: () => handleDateSelect(new Date()),
    },
    {
      label: 'Yesterday',
      onClick: () => handleDateSelect(subDays(new Date(), 1)),
    },
    {
      label: 'Last 7 Days',
      onClick: () => handleDateRangeSelect(subDays(new Date(), 7), new Date()),
    },
    {
      label: 'Last 30 Days',
      onClick: () => handleDateRangeSelect(subDays(new Date(), 30), new Date()),
    },
    {
      label: 'This Month',
      onClick: () => handleDateRangeSelect(
        startOfMonth(new Date()),
        endOfMonth(new Date())
      ),
    },
  ], [handleDateSelect, handleDateRangeSelect]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Historical Browser</h1>
          <p className="text-gray-600 mt-1">
            Explore forecast evolution and version history over time
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <ViewModeSelector
            currentMode={calendarState.viewMode}
            onModeChange={(mode) => setCalendarState(prev => ({ ...prev, viewMode: mode }))}
          />
          
          <button
            onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </button>
        </div>
      </div>

      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
        {quickDateFilters.map((filter, index) => (
          <button
            key={index}
            onClick={filter.onClick}
            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Search and Advanced Filters */}
      <SearchInterface
        searchState={searchState}
        onSearchStateChange={setSearchState}
        showAdvanced={showAdvancedSearch}
        onToggleAdvanced={() => setShowAdvancedSearch(!showAdvancedSearch)}
      />

      {/* Analytics Summary */}
      {analytics && (
        <AnalyticsSummary analytics={analytics} />
      )}

      {/* Main Content Based on View Mode */}
      {calendarState.viewMode === 'calendar' && (
        <CalendarView
          calendarState={calendarState}
          versionsByDate={versionsByDate}
          onDateSelect={handleDateSelect}
          onNavigateMonth={navigateMonth}
          isLoading={isLoadingSearch}
        />
      )}

      {calendarState.viewMode === 'timeline' && (
        <TimelineView
          versions={searchResults?.data || []}
          analytics={analytics}
          isLoading={isLoadingSearch}
        />
      )}

      {calendarState.viewMode === 'list' && (
        <ListView
          versions={searchResults?.data || []}
          selectedVersions={selectedVersions}
          onVersionSelect={setSelectedVersions}
          isLoading={isLoadingSearch}
        />
      )}

      {/* Selected Date Details */}
      {calendarState.selectedDate && (
        <DateDetailsPanel
          date={calendarState.selectedDate}
          dayData={versionsByDate.get(format(calendarState.selectedDate, 'yyyy-MM-dd'))}
        />
      )}
    </div>
  );
}

// ============================================================================
// View Mode Selector Component
// ============================================================================

interface ViewModeSelectorProps {
  currentMode: CalendarState['viewMode'];
  onModeChange: (mode: CalendarState['viewMode']) => void;
}

function ViewModeSelector({ currentMode, onModeChange }: ViewModeSelectorProps) {
  const modes = [
    { id: 'calendar' as const, icon: Calendar, label: 'Calendar' },
    { id: 'timeline' as const, icon: Activity, label: 'Timeline' },
    { id: 'list' as const, icon: Layers, label: 'List' },
  ];

  return (
    <div className="inline-flex rounded-md shadow-sm">
      {modes.map((mode, index) => (
        <button
          key={mode.id}
          onClick={() => onModeChange(mode.id)}
          className={`${
            index === 0 ? 'rounded-l-md' : ''
          } ${
            index === modes.length - 1 ? 'rounded-r-md' : ''
          } ${
            currentMode === mode.id
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          } relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium focus:z-10 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
        >
          <mode.icon className="h-4 w-4 mr-2" />
          {mode.label}
        </button>
      ))}
    </div>
  );
}

// ============================================================================
// Search Interface Component
// ============================================================================

interface SearchInterfaceProps {
  searchState: SearchState;
  onSearchStateChange: (state: SearchState) => void;
  showAdvanced: boolean;
  onToggleAdvanced: () => void;
}

function SearchInterface({
  searchState,
  onSearchStateChange,
  showAdvanced,
  onToggleAdvanced,
}: SearchInterfaceProps) {
  const availableHorizons = ['6h', '12h', '24h', '48h'];
  const availableRiskLevels = ['minimal', 'low', 'moderate', 'high', 'extreme'];
  const availableVariables = Object.keys(VARIABLE_NAMES);

  return (
    <div className="space-y-4">
      {/* Basic Search */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search historical forecasts..."
          value={searchState.query}
          onChange={(e) => onSearchStateChange({
            ...searchState,
            query: e.target.value,
          })}
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Advanced Search Panel */}
      {showAdvanced && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Advanced Search</h3>
            <button
              onClick={onToggleAdvanced}
              className="text-gray-400 hover:text-gray-600"
            >
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
                  value={searchState.dateRange.start ? format(searchState.dateRange.start, 'yyyy-MM-dd') : ''}
                  onChange={(e) => onSearchStateChange({
                    ...searchState,
                    dateRange: {
                      ...searchState.dateRange,
                      start: e.target.value ? new Date(e.target.value) : null,
                    },
                  })}
                  className="block w-full rounded-md border-gray-300 text-sm focus:ring-blue-500 focus:border-blue-500"
                />
                <input
                  type="date"
                  value={searchState.dateRange.end ? format(searchState.dateRange.end, 'yyyy-MM-dd') : ''}
                  onChange={(e) => onSearchStateChange({
                    ...searchState,
                    dateRange: {
                      ...searchState.dateRange,
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
                      checked={searchState.horizons.includes(horizon)}
                      onChange={(e) => {
                        const newHorizons = e.target.checked
                          ? [...searchState.horizons, horizon]
                          : searchState.horizons.filter(h => h !== horizon);
                        onSearchStateChange({
                          ...searchState,
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
                      checked={searchState.riskLevels.includes(level)}
                      onChange={(e) => {
                        const newLevels = e.target.checked
                          ? [...searchState.riskLevels, level]
                          : searchState.riskLevels.filter(l => l !== level);
                        onSearchStateChange({
                          ...searchState,
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
                Confidence Range: {Math.round(searchState.confidenceRange[0] * 100)}% - {Math.round(searchState.confidenceRange[1] * 100)}%
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={searchState.confidenceRange[0]}
                  onChange={(e) => onSearchStateChange({
                    ...searchState,
                    confidenceRange: [Number(e.target.value), searchState.confidenceRange[1]],
                  })}
                  className="flex-1"
                />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={searchState.confidenceRange[1]}
                  onChange={(e) => onSearchStateChange({
                    ...searchState,
                    confidenceRange: [searchState.confidenceRange[0], Number(e.target.value)],
                  })}
                  className="flex-1"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Analytics Summary Component
// ============================================================================

interface AnalyticsSummaryProps {
  analytics: VersionAnalytics;
}

function AnalyticsSummary({ analytics }: AnalyticsSummaryProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <Activity className="h-8 w-8 text-blue-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {analytics.total_versions.toLocaleString()}
            </p>
            <p className="text-gray-600">Total Versions</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <Clock className="h-8 w-8 text-green-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {Math.round(analytics.avg_latency_ms)}ms
            </p>
            <p className="text-gray-600">Avg Latency</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <CheckCircle className="h-8 w-8 text-purple-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {Math.round(analytics.avg_confidence_score * 100)}%
            </p>
            <p className="text-gray-600">Avg Confidence</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center">
          <Zap className="h-8 w-8 text-amber-600" />
          <div className="ml-4">
            <p className="text-2xl font-semibold text-gray-900">
              {Math.round(analytics.avg_analog_count)}
            </p>
            <p className="text-gray-600">Avg Analogs</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Calendar View Component
// ============================================================================

interface CalendarViewProps {
  calendarState: CalendarState;
  versionsByDate: Map<string, ForecastDayData>;
  onDateSelect: (date: Date) => void;
  onNavigateMonth: (direction: 'prev' | 'next') => void;
  isLoading: boolean;
}

function CalendarView({
  calendarState,
  versionsByDate,
  onDateSelect,
  onNavigateMonth,
  isLoading,
}: CalendarViewProps) {
  const calendarDays = useMemo(() => {
    const start = startOfMonth(calendarState.currentMonth);
    const end = endOfMonth(calendarState.currentMonth);
    return eachDayOfInterval({ start, end });
  }, [calendarState.currentMonth]);

  const getDayIntensity = (date: Date) => {
    const dateKey = format(date, 'yyyy-MM-dd');
    const dayData = versionsByDate.get(dateKey);
    if (!dayData) return 0;
    
    // Normalize intensity based on version count (0-4 scale)
    return Math.min(4, Math.floor(dayData.count / 5));
  };

  const getDayRiskLevel = (date: Date) => {
    const dateKey = format(date, 'yyyy-MM-dd');
    const dayData = versionsByDate.get(dateKey);
    if (!dayData) return null;

    // Find the most common risk level
    const risks = Object.entries(dayData.riskDistribution);
    if (risks.length === 0) return null;

    return risks.reduce((a, b) => a[1] > b[1] ? a : b)[0];
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-7 gap-4">
            {[...Array(35)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Calendar Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          {format(calendarState.currentMonth, 'MMMM yyyy')}
        </h2>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onNavigateMonth('prev')}
            className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={() => onNavigateMonth('next')}
            className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1 mb-4">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div key={day} className="p-2 text-center text-sm font-medium text-gray-500">
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map(date => {
          const dateKey = format(date, 'yyyy-MM-dd');
          const dayData = versionsByDate.get(dateKey);
          const intensity = getDayIntensity(date);
          const riskLevel = getDayRiskLevel(date);
          const isSelected = calendarState.selectedDate && isSameDay(date, calendarState.selectedDate);
          const isCurrentMonth = isSameMonth(date, calendarState.currentMonth);

          return (
            <CalendarDay
              key={dateKey}
              date={date}
              dayData={dayData}
              intensity={intensity}
              riskLevel={riskLevel}
              isSelected={isSelected}
              isCurrentMonth={isCurrentMonth}
              onClick={() => onDateSelect(date)}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-6 flex items-center justify-between text-sm text-gray-600">
        <div className="flex items-center space-x-4">
          <span>Activity:</span>
          <div className="flex items-center space-x-1">
            {[0, 1, 2, 3, 4].map(level => (
              <div
                key={level}
                className={`w-3 h-3 rounded ${
                  level === 0 ? 'bg-gray-100' :
                  level === 1 ? 'bg-blue-200' :
                  level === 2 ? 'bg-blue-400' :
                  level === 3 ? 'bg-blue-600' :
                  'bg-blue-800'
                }`}
              />
            ))}
          </div>
          <span>High</span>
        </div>
        
        <div className="text-xs">
          Click on a date to view forecast details
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Calendar Day Component
// ============================================================================

interface CalendarDayProps {
  date: Date;
  dayData?: ForecastDayData;
  intensity: number;
  riskLevel: string | null;
  isSelected: boolean;
  isCurrentMonth: boolean;
  onClick: () => void;
}

function CalendarDay({
  date,
  dayData,
  intensity,
  riskLevel,
  isSelected,
  isCurrentMonth,
  onClick,
}: CalendarDayProps) {
  const getIntensityColor = (intensity: number) => {
    switch (intensity) {
      case 0: return 'bg-gray-100 hover:bg-gray-200';
      case 1: return 'bg-blue-200 hover:bg-blue-300';
      case 2: return 'bg-blue-400 hover:bg-blue-500';
      case 3: return 'bg-blue-600 hover:bg-blue-700 text-white';
      case 4: return 'bg-blue-800 hover:bg-blue-900 text-white';
      default: return 'bg-gray-100 hover:bg-gray-200';
    }
  };

  const getRiskIndicator = (riskLevel: string | null) => {
    if (!riskLevel) return null;
    
    const color = riskLevel === 'extreme' ? 'bg-red-500' :
                 riskLevel === 'high' ? 'bg-orange-500' :
                 riskLevel === 'moderate' ? 'bg-yellow-500' :
                 riskLevel === 'low' ? 'bg-blue-500' :
                 'bg-green-500';
    
    return <div className={`absolute top-1 right-1 w-2 h-2 rounded-full ${color}`} />;
  };

  return (
    <button
      onClick={onClick}
      className={`
        relative p-3 min-h-[80px] text-left transition-colors rounded-md border
        ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-transparent'}
        ${isCurrentMonth ? getIntensityColor(intensity) : 'bg-gray-50 text-gray-400'}
        ${isCurrentMonth ? 'cursor-pointer' : 'cursor-default'}
      `}
      disabled={!isCurrentMonth}
    >
      <div className="flex items-start justify-between">
        <span className={`text-sm font-medium ${
          isCurrentMonth ? (intensity >= 3 ? 'text-white' : 'text-gray-900') : 'text-gray-400'
        }`}>
          {format(date, 'd')}
        </span>
        {getRiskIndicator(riskLevel)}
      </div>
      
      {dayData && dayData.count > 0 && (
        <div className="mt-1">
          <div className={`text-xs ${intensity >= 3 ? 'text-blue-100' : 'text-gray-600'}`}>
            {dayData.count} version{dayData.count !== 1 ? 's' : ''}
          </div>
          {dayData.avgConfidence > 0 && (
            <div className={`text-xs ${intensity >= 3 ? 'text-blue-200' : 'text-gray-500'}`}>
              {Math.round(dayData.avgConfidence * 100)}% conf
            </div>
          )}
        </div>
      )}
    </button>
  );
}

// ============================================================================
// Timeline View Component
// ============================================================================

interface TimelineViewProps {
  versions: ForecastVersionSummary[];
  analytics?: VersionAnalytics;
  isLoading: boolean;
}

function TimelineView({ versions, analytics, isLoading }: TimelineViewProps) {
  const timelineData = useMemo(() => {
    if (!versions) return [];

    // Group versions by date and calculate metrics
    const grouped = versions.reduce((acc, version) => {
      const date = format(parseISO(version.forecast_time), 'yyyy-MM-dd');
      
      if (!acc[date]) {
        acc[date] = {
          date,
          count: 0,
          avgConfidence: 0,
          avgLatency: 0,
          versions: [],
        };
      }

      acc[date].versions.push(version);
      acc[date].count++;
      
      if (version.confidence_score) {
        acc[date].avgConfidence += version.confidence_score;
      }
      
      if (version.latency_ms) {
        acc[date].avgLatency += version.latency_ms;
      }

      return acc;
    }, {} as Record<string, any>);

    // Calculate averages and sort by date
    return Object.values(grouped)
      .map((item: any) => ({
        ...item,
        avgConfidence: item.avgConfidence / item.count,
        avgLatency: item.avgLatency / item.count,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [versions]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="animate-pulse">
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Forecast Timeline</h3>
      
      <div className="h-64 mb-6">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(value) => format(parseISO(value), 'MMM d')}
            />
            <YAxis />
            <Tooltip 
              labelFormatter={(value) => format(parseISO(value), 'MMM d, yyyy')}
              formatter={(value: number, name: string) => [
                name === 'count' ? value.toString() : 
                name === 'avgConfidence' ? `${Math.round(value * 100)}%` :
                `${Math.round(value)}ms`,
                name === 'count' ? 'Forecast Count' :
                name === 'avgConfidence' ? 'Avg Confidence' :
                'Avg Latency'
              ]}
            />
            <Area 
              type="monotone" 
              dataKey="count" 
              stackId="1"
              stroke="#3B82F6" 
              fill="#93C5FD"
              name="count"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Confidence Trend</h4>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.confidence_trend}>
                  <XAxis dataKey="date" hide />
                  <YAxis domain={[0, 1]} />
                  <Tooltip 
                    formatter={(value: number) => [`${Math.round(value * 100)}%`, 'Confidence']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Usage Trend</h4>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.usage_trend}>
                  <XAxis dataKey="date" hide />
                  <YAxis />
                  <Tooltip 
                    formatter={(value: number) => [value.toString(), 'Versions']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="versions" 
                    stroke="#F59E0B" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// List View Component
// ============================================================================

interface ListViewProps {
  versions: ForecastVersionSummary[];
  selectedVersions: string[];
  onVersionSelect: (versions: string[]) => void;
  isLoading: boolean;
}

function ListView({ versions, selectedVersions, onVersionSelect, isLoading }: ListViewProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">
          {versions.length} Forecast Versions
        </h3>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {versions.map(version => (
          <div
            key={version.version_id}
            className="px-6 py-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
            onClick={() => {
              const isSelected = selectedVersions.includes(version.version_id);
              if (isSelected) {
                onVersionSelect(selectedVersions.filter(id => id !== version.version_id));
              } else {
                onVersionSelect([...selectedVersions, version.version_id]);
              }
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <input
                  type="checkbox"
                  checked={selectedVersions.includes(version.version_id)}
                  onChange={() => {}} // Handled by parent click
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {format(parseISO(version.forecast_time), 'MMM d, yyyy HH:mm')}
                  </div>
                  <div className="text-sm text-gray-500">
                    {version.horizon} • {version.model_version}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-6">
                {version.confidence_score && (
                  <div className="text-sm">
                    <span className="text-gray-500">Confidence:</span>
                    <span className="ml-1 font-medium">
                      {Math.round(version.confidence_score * 100)}%
                    </span>
                  </div>
                )}

                {version.risk_level && (
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${versioningUtils.getRiskLevelColor(version.risk_level)}`}>
                    {version.risk_level}
                  </span>
                )}

                <button className="text-blue-600 hover:text-blue-900">
                  <Eye className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Date Details Panel Component
// ============================================================================

interface DateDetailsPanelProps {
  date: Date;
  dayData?: ForecastDayData;
}

function DateDetailsPanel({ date, dayData }: DateDetailsPanelProps) {
  if (!dayData || dayData.count === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          {format(date, 'EEEE, MMMM d, yyyy')}
        </h3>
        <p className="text-gray-600">No forecast versions found for this date.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        {format(date, 'EEEE, MMMM d, yyyy')}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="text-center">
          <div className="text-2xl font-semibold text-blue-600">{dayData.count}</div>
          <div className="text-sm text-gray-600">Forecast Versions</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-semibold text-green-600">
            {Math.round(dayData.avgConfidence * 100)}%
          </div>
          <div className="text-sm text-gray-600">Avg Confidence</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-semibold text-purple-600">
            {Object.keys(dayData.riskDistribution).length}
          </div>
          <div className="text-sm text-gray-600">Risk Levels</div>
        </div>
      </div>

      <div className="space-y-4">
        <h4 className="font-medium text-gray-900">Versions</h4>
        {dayData.versions.slice(0, 5).map(version => (
          <div key={version.version_id} className="flex items-center justify-between py-2 border-b border-gray-100">
            <div>
              <div className="text-sm font-medium">
                {format(parseISO(version.forecast_time), 'HH:mm')} - {version.horizon}
              </div>
              <div className="text-sm text-gray-500">{version.model_version}</div>
            </div>
            
            <div className="flex items-center space-x-3">
              {version.confidence_score && (
                <span className="text-sm text-gray-600">
                  {Math.round(version.confidence_score * 100)}%
                </span>
              )}
              
              {version.risk_level && (
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium capitalize ${versioningUtils.getRiskLevelColor(version.risk_level)}`}>
                  {version.risk_level}
                </span>
              )}
              
              <button className="text-blue-600 hover:text-blue-900">
                <ArrowUpRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
        
        {dayData.versions.length > 5 && (
          <div className="text-sm text-gray-500 text-center py-2">
            And {dayData.versions.length - 5} more versions...
          </div>
        )}
      </div>
    </div>
  );
}