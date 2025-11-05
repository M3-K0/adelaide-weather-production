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
  BarChart3
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
import { format, parseISO } from 'date-fns';

interface AnalogExplorerProps {
  /** Analog explorer data */
  data: AnalogExplorerData;
  /** Current forecast horizon */
  horizon: ForecastHorizon;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string | null;
  /** Optional click handler for analog selection */
  onAnalogSelect?: (analog: AnalogPattern) => void;
  /** Custom className */
  className?: string;
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
  className = '' 
}: AnalogExplorerProps) {
  const [selectedAnalogIndex, setSelectedAnalogIndex] = useState<number>(0);
  const [timelinePosition, setTimelinePosition] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set([0]));
  const [selectedVariable, setSelectedVariable] = useState<WeatherVariable>('t2m');

  // Animation timer for timeline playback
  const [animationTimer, setAnimationTimer] = useState<NodeJS.Timeout | null>(null);

  // Get available variables from the data
  const availableVariables = useMemo(() => {
    if (!data.top_analogs.length) return [];
    const firstAnalog = data.top_analogs[0];
    return Object.keys(firstAnalog.initial_conditions).filter(
      variable => firstAnalog.initial_conditions[variable as WeatherVariable] !== null
    ) as WeatherVariable[];
  }, [data.top_analogs]);

  // Timeline duration in hours (maximum from all analogs)
  const timelineDuration = useMemo(() => {
    if (!data.top_analogs.length) return 48;
    return Math.max(...data.top_analogs.map(analog => 
      Math.max(...analog.timeline.map(point => point.hours_offset))
    ));
  }, [data.top_analogs]);

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

  // Handle analog selection
  const handleAnalogSelect = useCallback((index: number) => {
    setSelectedAnalogIndex(index);
    if (onAnalogSelect) {
      onAnalogSelect(data.top_analogs[index]);
    }
  }, [data.top_analogs, onAnalogSelect]);

  // Export functionality
  const exportToCSV = useCallback(() => {
    const csvContent = generateCSVContent(data);
    downloadFile(csvContent, `analog-patterns-${horizon}.csv`, 'text/csv');
  }, [data, horizon]);

  const exportToJSON = useCallback(() => {
    const jsonContent = JSON.stringify(data, null, 2);
    downloadFile(jsonContent, `analog-patterns-${horizon}.json`, 'application/json');
  }, [data, horizon]);

  // Generate chart data for timeline visualization
  const chartData = useMemo(() => {
    if (!data.top_analogs.length) return [];
    
    const selectedAnalog = data.top_analogs[selectedAnalogIndex];
    const currentPoint = getCurrentTimelineData(selectedAnalog, timelinePosition);
    
    return selectedAnalog.timeline.map(point => ({
      hours: point.hours_offset,
      value: point.values[selectedVariable] || null,
      temperature_trend: point.temperature_trend,
      pressure_trend: point.pressure_trend,
      events: point.events?.join(', ') || '',
      isCurrentPoint: point.hours_offset === currentPoint.hours_offset
    }));
  }, [data.top_analogs, selectedAnalogIndex, selectedVariable, timelinePosition, getCurrentTimelineData]);

  if (loading) {
    return (
      <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-1/3"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-slate-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-[#0E1116] border border-red-700 rounded-lg p-6 ${className}`}>
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <TrendingUp size={16} />
          <span className="font-medium">Analog Explorer Error</span>
        </div>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (!data.top_analogs.length) {
    return (
      <div className={`bg-[#0E1116] border border-[#1C1F26] rounded-lg p-6 ${className}`}>
        <div className="text-center text-slate-400">
          <TrendingUp size={32} className="mx-auto mb-3 opacity-50" />
          <p>No historical analogs found for this forecast</p>
        </div>
      </div>
    );
  }

  return (
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
          </div>
          
          {/* Export buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={exportToCSV}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 transition-colors"
              title="Export as CSV"
            >
              <FileText size={12} />
              CSV
            </button>
            <button
              onClick={exportToJSON}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 transition-colors"
              title="Export as JSON"
            >
              <Database size={12} />
              JSON
            </button>
          </div>
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

        {/* Variable Selector */}
        <div className="flex items-center gap-2 mt-4">
          <span className="text-xs text-slate-400">Variable:</span>
          <select
            value={selectedVariable}
            onChange={(e) => setSelectedVariable(e.target.value as WeatherVariable)}
            className="px-2 py-1 rounded text-xs bg-slate-800 border border-slate-600 text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            {availableVariables.map(variable => (
              <option key={variable} value={variable}>
                {VARIABLE_NAMES[variable]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
        {/* Analog Cards */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wide">
            Top 5 Similar Patterns
          </h3>
          
          {data.top_analogs.map((analog, index) => (
            <AnalogCard
              key={`${analog.date}-${index}`}
              analog={analog}
              index={index}
              timelinePosition={timelinePosition}
              isExpanded={expandedCards.has(index)}
              onToggleExpanded={() => handleToggleExpanded(index)}
              onSelect={() => handleAnalogSelect(index)}
            />
          ))}
        </div>

        {/* Timeline Visualization */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wide">
            Timeline Visualization
          </h3>
          
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
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
                    tickFormatter={(value) => `${value}${VARIABLE_UNITS[selectedVariable]}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '4px',
                      color: '#e2e8f0'
                    }}
                    formatter={(value, name) => [
                      `${value}${VARIABLE_UNITS[selectedVariable]}`,
                      VARIABLE_NAMES[selectedVariable]
                    ]}
                    labelFormatter={(hours) => `+${hours} hours`}
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
            {data.top_analogs[selectedAnalogIndex] && (
              <CurrentPointInfo 
                analog={data.top_analogs[selectedAnalogIndex]}
                timelinePosition={timelinePosition}
                timelineDuration={timelineDuration}
                getCurrentTimelineData={getCurrentTimelineData}
              />
            )}
          </div>
        </div>
      </div>
    </div>
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
  const similarityPct = Math.round(analog.similarity_score * 100);
  
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
              {format(parseISO(analog.date), 'MMM dd, yyyy')}
            </div>
            <div className="text-xs text-slate-400">
              {analog.season_info.season} • {format(parseISO(analog.date), 'HH:mm')}
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
          <span>{analog.location.name || `${analog.location.latitude.toFixed(2)}, ${analog.location.longitude.toFixed(2)}`}</span>
        </div>
      )}

      {/* Quick outcome preview */}
      <div className="text-xs text-slate-300 mb-3 line-clamp-2">
        {analog.outcome_narrative}
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
            <div>
              <h4 className="text-xs font-medium text-slate-300 mb-2">Initial Conditions</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(analog.initial_conditions).map(([variable, value]) => (
                  value !== null && (
                    <div key={variable} className="flex justify-between">
                      <span className="text-slate-400">{VARIABLE_NAMES[variable as WeatherVariable]}:</span>
                      <span className="text-slate-200 font-mono">
                        {value.toFixed(1)}{VARIABLE_UNITS[variable as WeatherVariable]}
                      </span>
                    </div>
                  )
                ))}
              </div>
            </div>

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
  const timelineDuration = Math.max(...analog.timeline.map(point => point.hours_offset));
  const targetHours = timelinePosition * timelineDuration;
  
  // Find closest timeline point
  const currentPoint = analog.timeline.reduce((closest, point) => {
    const closestDiff = Math.abs(closest.hours_offset - targetHours);
    const pointDiff = Math.abs(point.hours_offset - targetHours);
    return pointDiff < closestDiff ? point : closest;
  });

  return (
    <div>
      <h4 className="text-xs font-medium text-slate-300 mb-2">
        At +{currentPoint.hours_offset}h
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
      {currentPoint.events && currentPoint.events.length > 0 && (
        <div>
          <span className="text-xs text-slate-400">Events:</span>
          <ul className="text-xs text-slate-300 mt-1 space-y-1">
            {currentPoint.events.map((event, index) => (
              <li key={index} className="flex items-start gap-1">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>{event}</span>
              </li>
            ))}
          </ul>
        </div>
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
  const currentPoint = getCurrentTimelineData(analog, timelinePosition);
  
  return (
    <div className="mt-4 pt-4 border-t border-slate-700">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 size={14} className="text-cyan-400" />
        <span className="text-sm font-medium text-slate-300">
          Current Position: +{currentPoint.hours_offset}h
        </span>
      </div>
      
      {currentPoint.events && currentPoint.events.length > 0 && (
        <div className="text-xs text-slate-400">
          <strong>Events:</strong> {currentPoint.events.join(', ')}
        </div>
      )}
    </div>
  );
}

// Utility functions for export
function generateCSVContent(data: AnalogExplorerData): string {
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
    analog.date,
    analog.similarity_score.toFixed(4),
    analog.season_info.season,
    `"${analog.outcome_narrative.replace(/"/g, '""')}"`, // Escape quotes
    analog.location?.name || '',
    analog.location?.latitude.toFixed(6) || '',
    analog.location?.longitude.toFixed(6) || ''
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