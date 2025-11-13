/**
 * Analog Pattern Explorer Component
 * Interactive component showing top 5 similar historical cases with timeline and export functionality
 * 
 * Features:
 * - Interactive timeline scrubbing for each analog
 * - Date/time display, similarity scores, and outcome visualization
 * - "What happened next" narrative for each analog
 * - Export functionality for analog data (CSV/JSON)
 * - Smooth timeline animations and responsive design
 */

import React, { useState, useCallback, useMemo } from 'react';
import { 
  Calendar, 
  Download, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Play, 
  Pause, 
  RotateCcw,
  FileText,
  Database,
  MapPin,
  Clock,
  BarChart3,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine 
} from 'recharts';
import type { 
  AnalogExplorerData, 
  AnalogPattern, 
  AnalogTimelinePoint,
  WeatherVariable,
  ForecastHorizon 
} from '@/types';
import { VARIABLE_NAMES, VARIABLE_UNITS } from '@/types';
import EmptyState from './EmptyState';
import LoadingState from './LoadingState';
import ErrorBoundary from './ErrorBoundary';
import { format, parseISO } from 'date-fns';

interface AnalogExplorerProps {
  /** Analog explorer data */
  data: AnalogExplorerData | null;
  /** Current forecast horizon */
  horizon: ForecastHorizon;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string | null;
  /** Optional click handler for analog selection */
  onAnalogSelect?: (analog: AnalogPattern) => void;
  /** Retry callback for failed requests */
  onRetry?: () => void;
  /** Custom className */
  className?: string;
  /** Show detailed error information */
  showErrorDetails?: boolean;
}

interface TimelineControlsProps {
  /** Current timeline position (0-1) */
  position: number;
  /** Is playing flag */
  isPlaying: boolean;
  /** Timeline duration in hours */
  duration: number;
  /** Position change handler */
  onPositionChange: (position: number) => void;
  /** Play/pause handler */
  onPlayPause: () => void;
  /** Reset handler */
  onReset: () => void;
}

interface AnalogCardProps {
  /** Analog pattern data */
  analog: AnalogPattern;
  /** Index in the list (1-5) */
  index: number;
  /** Current timeline position */
  timelinePosition: number;
  /** Is expanded flag */
  isExpanded: boolean;
  /** Toggle expanded handler */
  onToggleExpanded: () => void;
  /** Select analog handler */
  onSelect: () => void;
}

export function AnalogExplorer({ 
  data, 
  horizon, 
  loading = false, 
  error = null, 
  onAnalogSelect,
  onRetry,
  className = '',
  showErrorDetails = false
}: AnalogExplorerProps) {
  const [selectedAnalogIndex, setSelectedAnalogIndex] = useState<number>(0);
  const [timelinePosition, setTimelinePosition] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set([0]));
  const [selectedVariable, setSelectedVariable] = useState<WeatherVariable>('t2m');

  // Animation timer for timeline playback
  const [animationTimer, setAnimationTimer] = useState<NodeJS.Timeout | null>(null);

  // Get available variables from the data (with null safety)
  const availableVariables = useMemo(() => {
    if (!data?.top_analogs?.length) return [];
    const firstAnalog = data.top_analogs[0];
    if (!firstAnalog?.initial_conditions) return [];
    
    return Object.keys(firstAnalog.initial_conditions).filter(
      variable => {
        const value = firstAnalog.initial_conditions[variable as WeatherVariable];
        return value !== null && value !== undefined;
      }
    ) as WeatherVariable[];
  }, [data?.top_analogs]);

  // Timeline duration in hours (maximum from all analogs) with null safety
  const timelineDuration = useMemo(() => {
    if (!data?.top_analogs?.length) return 48;
    
    try {
      return Math.max(...data.top_analogs.map(analog => {
        if (!analog?.timeline?.length) return 0;
        return Math.max(...analog.timeline.map(point => point?.hours_offset || 0));
      }));
    } catch {
      return 48; // Fallback to default duration
    }
  }, [data?.top_analogs]);

  // Get current timeline point for each analog
  const getCurrentTimelineData = useCallback((analog: AnalogPattern, position: number) => {
    const targetHours = position * timelineDuration;
    
    // Find the closest timeline point
    const sortedPoints = [...analog.timeline].sort((a, b) => a.hours_offset - b.hours_offset);
    
    if (targetHours <= sortedPoints[0].hours_offset) {
      return sortedPoints[0];
    }
    
    if (targetHours >= sortedPoints[sortedPoints.length - 1].hours_offset) {
      return sortedPoints[sortedPoints.length - 1];
    }
    
    // Interpolate between two points
    for (let i = 0; i < sortedPoints.length - 1; i++) {
      const current = sortedPoints[i];
      const next = sortedPoints[i + 1];
      
      if (targetHours >= current.hours_offset && targetHours <= next.hours_offset) {
        return current; // For simplicity, return the earlier point
      }
    }
    
    return sortedPoints[0];
  }, [timelineDuration]);

  // Timeline animation effect
  React.useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setTimelinePosition(prev => {
          const next = prev + (0.005 * playbackSpeed); // Adjust speed as needed
          if (next >= 1) {
            setIsPlaying(false);
            return 1;
          }
          return next;
        });
      }, 50);
      
      setAnimationTimer(interval);
      return () => clearInterval(interval);
    } else if (animationTimer) {
      clearInterval(animationTimer);
      setAnimationTimer(null);
    }
  }, [isPlaying, playbackSpeed, animationTimer]);

  // Handle play/pause
  const handlePlayPause = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  // Handle reset
  const handleReset = useCallback(() => {
    setIsPlaying(false);
    setTimelinePosition(0);
  }, []);

  // Handle analog card expansion
  const handleToggleExpanded = useCallback((index: number) => {
    setExpandedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  }, []);

  // Handle analog selection (with null safety)
  const handleAnalogSelect = useCallback((index: number) => {
    if (!data?.top_analogs?.[index]) return;
    
    setSelectedAnalogIndex(index);
    if (onAnalogSelect) {
      onAnalogSelect(data.top_analogs[index]);
    }
  }, [data?.top_analogs, onAnalogSelect]);

  // Export functionality (with null safety)
  const exportToCSV = useCallback(() => {
    if (!data) return;
    const csvContent = generateCSVContent(data);
    downloadFile(csvContent, `analog-patterns-${horizon}.csv`, 'text/csv');
  }, [data, horizon]);

  const exportToJSON = useCallback(() => {
    if (!data) return;
    const jsonContent = JSON.stringify(data, null, 2);
    downloadFile(jsonContent, `analog-patterns-${horizon}.json`, 'application/json');
  }, [data, horizon]);

  // Generate chart data for timeline visualization (with null safety)
  const chartData = useMemo(() => {
    if (!data?.top_analogs?.length) return [];
    
    const selectedAnalog = data.top_analogs[selectedAnalogIndex];
    if (!selectedAnalog?.timeline?.length) return [];
    
    const currentPoint = getCurrentTimelineData(selectedAnalog, timelinePosition);
    
    return selectedAnalog.timeline.map(point => ({
      hours: point?.hours_offset || 0,
      value: point?.values?.[selectedVariable] || null,
      temperature_trend: point?.temperature_trend || null,
      pressure_trend: point?.pressure_trend || null,
      events: point?.events?.join(', ') || '',
      isCurrentPoint: point?.hours_offset === currentPoint?.hours_offset
    }));
  }, [data?.top_analogs, selectedAnalogIndex, selectedVariable, timelinePosition, getCurrentTimelineData]);

  // Loading state
  if (loading) {
    return (
      <ErrorBoundary componentName="AnalogExplorer">
        <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg ${className}`}>
          <LoadingState 
            type="analogs"
            size="lg"
            message="Searching Historical Patterns"
            showDetails={true}
          />
        </div>
      </ErrorBoundary>
    );
  }

  // Error state
  if (error) {
    return (
      <ErrorBoundary componentName="AnalogExplorer">
        <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg ${className}`}>
          <EmptyState
            type="error"
            title="Failed to Load Analog Data"
            description={showErrorDetails ? error : "Unable to retrieve historical weather patterns. Please try again."}
            showRetry={!!onRetry}
            onRetry={onRetry}
            size="lg"
          />
        </div>
      </ErrorBoundary>
    );
  }

  // No data available
  if (!data) {
    return (
      <ErrorBoundary componentName="AnalogExplorer">
        <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg ${className}`}>
          <EmptyState
            type="no-data"
            title="No Analog Data Available"
            description="Analog explorer data is not available at this time."
            showRetry={!!onRetry}
            onRetry={onRetry}
            size="lg"
          />
        </div>
      </ErrorBoundary>
    );
  }

  // No analogs found
  if (!data.top_analogs || data.top_analogs.length === 0) {
    return (
      <ErrorBoundary componentName="AnalogExplorer">
        <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg ${className}`}>
          <EmptyState
            type="no-analogs"
            title="No Analogs Available"
            description="No similar historical weather patterns were found for this forecast horizon. This may indicate unique weather conditions."
            dataSource={data.data_source}
            fallbackReason={data.search_metadata?.fallback_reason}
            showRetry={!!onRetry}
            onRetry={onRetry}
            size="lg"
            actions={
              data.search_metadata?.search_method && (
                <div className="text-xs text-slate-500 mt-2">
                  Search method: {data.search_metadata.search_method}
                  {data.search_metadata.total_candidates && (
                    <span className="ml-2">
                      ({data.search_metadata.total_candidates.toLocaleString()} candidates searched)
                    </span>
                  )}
                </div>
              )
            }
          />
        </div>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary componentName="AnalogExplorer">
      <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg ${className}`}>
        {/* Header */}
        <div className="p-6 border-b border-[#1C1F26]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <TrendingUp size={20} className="text-cyan-400" />
              <h2 className="text-lg font-semibold text-slate-100">
                Historical Analog Patterns
              </h2>
              <span className="px-2 py-1 rounded text-xs font-medium bg-cyan-950/50 border border-cyan-700 text-cyan-400">
                +{horizon}
              </span>
              
              {/* Data Source Indicator with null safety */}
              {data?.data_source && (
                <div className={`px-2 py-1 rounded text-xs font-medium border flex items-center gap-1 ${
                  data.data_source === 'faiss' 
                    ? 'bg-emerald-950/50 border-emerald-700 text-emerald-400' 
                    : 'bg-orange-950/50 border-orange-700 text-orange-400'
                }`}>
                  <Database size={10} />
                  {data.data_source === 'faiss' ? 'Real FAISS' : 'Fallback Mode'}
                </div>
              )}
            </div>
          
          {/* Export buttons - only show if data is available */}
          {data && (
            <div className="flex items-center gap-2">
              <button
                onClick={exportToCSV}
                disabled={!data || !data.top_analogs?.length}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Export as CSV"
              >
                <FileText size={12} />
                CSV
              </button>
              <button
                onClick={exportToJSON}
                disabled={!data}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Export as JSON"
              >
                <Database size={12} />
                JSON
              </button>
            </div>
          )}
        </div>

        {/* Timeline Controls */}
        <TimelineControls
          position={timelinePosition}
          isPlaying={isPlaying}
          duration={timelineDuration}
          onPositionChange={setTimelinePosition}
          onPlayPause={handlePlayPause}
          onReset={handleReset}
        />

        {/* Variable Selector - only show if variables are available */}
        {availableVariables.length > 0 && (
          <div className="flex items-center gap-2 mt-4">
            <span className="text-xs text-slate-400">Variable:</span>
            <select
              value={selectedVariable}
              onChange={(e) => setSelectedVariable(e.target.value as WeatherVariable)}
              className="px-2 py-1 rounded text-xs bg-slate-800 border border-slate-600 text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              {availableVariables.map(variable => (
                <option key={variable} value={variable}>
                  {VARIABLE_NAMES[variable] || variable}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Search Metadata (Transparency Information) - only show if metadata exists */}
        {data?.search_metadata && (
          <div className="mt-4 p-3 rounded-lg bg-slate-900/30 border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 size={12} className="text-slate-400" />
              <span className="text-xs font-medium text-slate-300 uppercase tracking-wide">
                Search Transparency
              </span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="space-y-1">
                <span className="text-slate-400">Method:</span>
                <div className={`font-mono px-2 py-1 rounded ${
                  data.search_metadata.search_method?.includes('faiss') 
                    ? 'bg-emerald-950/50 text-emerald-300'
                    : 'bg-orange-950/50 text-orange-300'
                }`}>
                  {data.search_metadata.search_method || 'Unknown'}
                </div>
              </div>
              {data.search_metadata.search_time_ms !== undefined && (
                <div className="space-y-1">
                  <span className="text-slate-400">Search Time:</span>
                  <div className="font-mono text-slate-200">
                    {data.search_metadata.search_time_ms.toFixed(1)}ms
                  </div>
                </div>
              )}
              {data.search_metadata.total_candidates !== undefined && (
                <div className="space-y-1">
                  <span className="text-slate-400">Candidates:</span>
                  <div className="font-mono text-slate-200">
                    {data.search_metadata.total_candidates.toLocaleString()}
                  </div>
                </div>
              )}
              {data.search_metadata.k_neighbors_found !== undefined && (
                <div className="space-y-1">
                  <span className="text-slate-400">Found:</span>
                  <div className="font-mono text-slate-200">
                    {data.search_metadata.k_neighbors_found} analog{data.search_metadata.k_neighbors_found !== 1 ? 's' : ''}
                  </div>
                </div>
              )}
            </div>
            {data.search_metadata.fallback_reason && (
              <div className="mt-2 text-xs text-orange-300">
                <span className="text-slate-400">Fallback Reason:</span> {data.search_metadata.fallback_reason}
              </div>
            )}
          </div>
        )}
      </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
          {/* Analog Cards */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wide">
              Top {data.top_analogs?.length || 0} Similar Patterns
            </h3>
            
            {data.top_analogs && data.top_analogs.length > 0 ? (
              data.top_analogs.map((analog, index) => (
                analog ? (
                  <AnalogCard
                    key={`${analog.date}-${index}`}
                    analog={analog}
                    index={index}
                    timelinePosition={timelinePosition}
                    isExpanded={expandedCards.has(index)}
                    onToggleExpanded={() => handleToggleExpanded(index)}
                    onSelect={() => handleAnalogSelect(index)}
                  />
                ) : (
                  <div key={`empty-${index}`} className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
                    <EmptyState
                      type="no-data"
                      size="sm"
                      title="Invalid Analog Data"
                      description="This analog pattern contains invalid data."
                    />
                  </div>
                )
              ))
            ) : (
              <EmptyState
                type="no-analogs"
                size="md"
                title="No Analog Patterns"
                description="No historical patterns are available for display."
              />
            )}
          </div>

          {/* Timeline Visualization */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wide">
              Timeline Visualization
            </h3>
            
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
              {chartData && chartData.length > 0 ? (
                <>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis 
                          dataKey="hours" 
                          stroke="#94a3b8"
                          fontSize={12}
                          tickFormatter={(hours) => `+${hours}h`}
                        />
                        <YAxis 
                          stroke="#94a3b8"
                          fontSize={12}
                          tickFormatter={(value) => {
                            if (value === null || value === undefined) return 'N/A';
                            return `${value}${VARIABLE_UNITS[selectedVariable] || ''}`;
                          }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1e293b',
                            border: '1px solid #475569',
                            borderRadius: '4px',
                            color: '#e2e8f0'
                          }}
                          formatter={(value, name) => {
                            if (value === null || value === undefined) return ['N/A', VARIABLE_NAMES[selectedVariable] || selectedVariable];
                            return [
                              `${value}${VARIABLE_UNITS[selectedVariable] || ''}`,
                              VARIABLE_NAMES[selectedVariable] || selectedVariable
                            ];
                          }}
                          labelFormatter={(hours) => `+${hours || 0} hours`}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#22d3ee"
                          strokeWidth={2}
                          dot={{ fill: '#22d3ee', strokeWidth: 2, r: 4 }}
                          connectNulls={false}
                        />
                        
                        {/* Current position indicator */}
                        <ReferenceLine 
                          x={timelinePosition * timelineDuration} 
                          stroke="#fbbf24" 
                          strokeWidth={2}
                          strokeDasharray="4 4"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  
                  {/* Current point info */}
                  {data.top_analogs?.[selectedAnalogIndex] && (
                    <CurrentPointInfo 
                      analog={data.top_analogs[selectedAnalogIndex]}
                      timelinePosition={timelinePosition}
                      timelineDuration={timelineDuration}
                      getCurrentTimelineData={getCurrentTimelineData}
                    />
                  )}
                </>
              ) : (
                <div className="h-64 flex items-center justify-center">
                  <EmptyState
                    type="no-data"
                    size="sm"
                    title="No Timeline Data"
                    description="Timeline visualization is not available for the selected analog."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}

// Timeline Controls Component
function TimelineControls({ 
  position, 
  isPlaying, 
  duration, 
  onPositionChange, 
  onPlayPause, 
  onReset 
}: TimelineControlsProps) {
  return (
    <div className="space-y-3">
      {/* Playback controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={onPlayPause}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-600 hover:bg-cyan-500 text-white transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
        </button>
        
        <button
          onClick={onReset}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-600 hover:bg-slate-500 text-white transition-colors"
          title="Reset to start"
        >
          <RotateCcw size={16} />
        </button>
        
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock size={12} />
          <span>+{Math.round(position * duration)}h / +{duration}h</span>
        </div>
      </div>
      
      {/* Timeline scrubber */}
      <div className="relative">
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={position}
          onChange={(e) => onPositionChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer timeline-slider"
          style={{
            background: `linear-gradient(to right, #22d3ee 0%, #22d3ee ${position * 100}%, #475569 ${position * 100}%, #475569 100%)`
          }}
        />
      </div>
    </div>
  );
}

// Individual Analog Card Component
function AnalogCard({ 
  analog, 
  index, 
  timelinePosition, 
  isExpanded, 
  onToggleExpanded, 
  onSelect 
}: AnalogCardProps) {
  // Null safety checks
  if (!analog) {
    return (
      <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
        <EmptyState
          type="no-data"
          size="sm"
          title="Invalid Analog"
          description="This analog pattern contains invalid data."
        />
      </div>
    );
  }

  const similarityPct = analog.similarity_score ? Math.round(analog.similarity_score * 100) : 0;
  
  // Get similarity styling
  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return 'text-emerald-400 bg-emerald-950/50 border-emerald-700';
    if (score >= 0.6) return 'text-cyan-400 bg-cyan-950/50 border-cyan-700';
    if (score >= 0.4) return 'text-yellow-400 bg-yellow-950/50 border-yellow-700';
    return 'text-orange-400 bg-orange-950/50 border-orange-700';
  };

  const similarityClass = getSimilarityColor(analog.similarity_score);

  return (
    <motion.div
      layout
      className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 cursor-pointer hover:border-slate-600 transition-colors"
      onClick={onSelect}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-cyan-600 text-white text-xs font-bold flex items-center justify-center">
            {index + 1}
          </span>
          <div>
            <div className="text-sm font-medium text-slate-200">
              {analog.date ? format(parseISO(analog.date), 'MMM dd, yyyy') : 'Unknown Date'}
            </div>
            <div className="text-xs text-slate-400">
              {analog.season_info?.season || 'Unknown'} • {analog.date ? format(parseISO(analog.date), 'HH:mm') : '--:--'}
            </div>
          </div>
        </div>
        
        <div className={`px-2 py-1 rounded text-xs font-medium border ${similarityClass}`}>
          {similarityPct}% match
        </div>
      </div>

      {/* Location if available */}
      {analog.location && (
        <div className="flex items-center gap-1 mb-2 text-xs text-slate-400">
          <MapPin size={10} />
          <span>
            {analog.location.name || 
             (analog.location.latitude !== undefined && analog.location.longitude !== undefined 
               ? `${analog.location.latitude.toFixed(2)}, ${analog.location.longitude.toFixed(2)}`
               : 'Unknown location'
             )}
          </span>
        </div>
      )}

      {/* Quick outcome preview */}
      <div className="text-xs text-slate-300 mb-3 line-clamp-2">
        {analog.outcome_narrative || 'No outcome narrative available'}
      </div>

      {/* Expand button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggleExpanded();
        }}
        className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
      >
        {isExpanded ? 'Show less' : 'Show details'}
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 pt-4 border-t border-slate-700 space-y-3"
          >
            {/* Initial conditions */}
            {analog.initial_conditions && (
              <div>
                <h4 className="text-xs font-medium text-slate-300 mb-2">Initial Conditions</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(analog.initial_conditions).map(([variable, value]) => {
                    if (value === null || value === undefined) return null;
                    
                    return (
                      <div key={variable} className="flex justify-between">
                        <span className="text-slate-400">
                          {VARIABLE_NAMES[variable as WeatherVariable] || variable}:
                        </span>
                        <span className="text-slate-200 font-mono">
                          {typeof value === 'number' ? value.toFixed(1) : value}
                          {VARIABLE_UNITS[variable as WeatherVariable] || ''}
                        </span>
                      </div>
                    );
                  })}
                  {Object.values(analog.initial_conditions).every(v => v === null || v === undefined) && (
                    <div className="text-slate-500 text-xs col-span-2">
                      No initial conditions data available
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Timeline events at current position */}
            <TimelineEvents 
              analog={analog} 
              timelinePosition={timelinePosition} 
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Timeline Events Component
function TimelineEvents({ analog, timelinePosition }: { analog: AnalogPattern; timelinePosition: number }) {
  // Null safety checks
  if (!analog?.timeline?.length) {
    return (
      <div>
        <h4 className="text-xs font-medium text-slate-300 mb-2">Timeline Events</h4>
        <div className="text-xs text-slate-500">No timeline data available</div>
      </div>
    );
  }

  const timelineDuration = Math.max(...analog.timeline.map(point => point?.hours_offset || 0));
  const targetHours = timelinePosition * timelineDuration;
  
  // Find closest timeline point with null safety
  const currentPoint = analog.timeline.reduce((closest, point) => {
    if (!closest || !point) return closest || point || analog.timeline[0];
    const closestDiff = Math.abs((closest.hours_offset || 0) - targetHours);
    const pointDiff = Math.abs((point.hours_offset || 0) - targetHours);
    return pointDiff < closestDiff ? point : closest;
  });

  if (!currentPoint) {
    return (
      <div>
        <h4 className="text-xs font-medium text-slate-300 mb-2">Timeline Events</h4>
        <div className="text-xs text-slate-500">No timeline point found</div>
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-slate-300 mb-2">
        At +{currentPoint.hours_offset || 0}h
      </h4>
      
      {/* Temperature and pressure trends */}
      <div className="flex items-center gap-4 mb-2">
        {currentPoint.temperature_trend && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-slate-400">Temp:</span>
            {currentPoint.temperature_trend === 'rising' && <TrendingUp size={12} className="text-red-400" />}
            {currentPoint.temperature_trend === 'falling' && <TrendingDown size={12} className="text-blue-400" />}
            {currentPoint.temperature_trend === 'stable' && <Minus size={12} className="text-slate-400" />}
            <span className="text-slate-300 capitalize">{currentPoint.temperature_trend}</span>
          </div>
        )}
        
        {currentPoint.pressure_trend && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-slate-400">Pressure:</span>
            {currentPoint.pressure_trend === 'rising' && <TrendingUp size={12} className="text-emerald-400" />}
            {currentPoint.pressure_trend === 'falling' && <TrendingDown size={12} className="text-amber-400" />}
            {currentPoint.pressure_trend === 'stable' && <Minus size={12} className="text-slate-400" />}
            <span className="text-slate-300 capitalize">{currentPoint.pressure_trend}</span>
          </div>
        )}
      </div>

      {/* Events */}
      {currentPoint.events && currentPoint.events.length > 0 ? (
        <div>
          <span className="text-xs text-slate-400">Events:</span>
          <ul className="text-xs text-slate-300 mt-1 space-y-1">
            {currentPoint.events.map((event, index) => (
              event ? (
                <li key={index} className="flex items-start gap-1">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  <span>{event}</span>
                </li>
              ) : null
            ))}
          </ul>
        </div>
      ) : (
        <div className="text-xs text-slate-500">No events recorded for this time point</div>
      )}
    </div>
  );
}

// Current Point Info Component
function CurrentPointInfo({ 
  analog, 
  timelinePosition, 
  timelineDuration, 
  getCurrentTimelineData 
}: {
  analog: AnalogPattern;
  timelinePosition: number;
  timelineDuration: number;
  getCurrentTimelineData: (analog: AnalogPattern, position: number) => AnalogTimelinePoint;
}) {
  if (!analog) {
    return (
      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">No analog data available</div>
      </div>
    );
  }

  const currentPoint = getCurrentTimelineData(analog, timelinePosition);
  
  if (!currentPoint) {
    return (
      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">No timeline point found</div>
      </div>
    );
  }
  
  return (
    <div className="mt-4 pt-4 border-t border-slate-700">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 size={14} className="text-cyan-400" />
        <span className="text-sm font-medium text-slate-300">
          Current Position: +{currentPoint.hours_offset || 0}h
        </span>
      </div>
      
      {currentPoint.events && currentPoint.events.length > 0 && (
        <div className="text-xs text-slate-400">
          <strong>Events:</strong> {currentPoint.events.filter(event => event).join(', ')}
        </div>
      )}
    </div>
  );
}

// Utility functions for export (with null safety)
function generateCSVContent(data: AnalogExplorerData): string {
  if (!data?.top_analogs?.length) {
    return 'No analog data available for export';
  }

  const headers = [
    'Date',
    'Similarity_Score',
    'Season',
    'Outcome_Narrative',
    'Location_Name',
    'Latitude',
    'Longitude'
  ];
  
  const rows = data.top_analogs.map(analog => [
    analog?.date || 'Unknown',
    analog?.similarity_score ? analog.similarity_score.toFixed(4) : '0.0000',
    analog?.season_info?.season || 'Unknown',
    analog?.outcome_narrative ? `"${analog.outcome_narrative.replace(/"/g, '""')}"` : '""', // Escape quotes
    analog?.location?.name || '',
    analog?.location?.latitude ? analog.location.latitude.toFixed(6) : '',
    analog?.location?.longitude ? analog.location.longitude.toFixed(6) : ''
  ]);
  
  return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default AnalogExplorer;