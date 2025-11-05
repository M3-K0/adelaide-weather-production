'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings2, TrendingUp } from 'lucide-react';

// Enhanced types for the new features
interface VariableToggle {
  id: string;
  label: string;
  unit: string;
  enabled: boolean;
  value: number | null;
  p05: number | null | undefined;
  p95: number | null | undefined;
  available: boolean;
}

interface AnalogPoint {
  timestamp: string;
  value: number;
  similarity: number;
}

interface ForecastCardProps {
  horizon: string;
  // Temperature data
  temp: number;
  confidence: number;
  confidencePct: number;
  p05: number;
  p50?: number;
  p95: number;
  // Wind data
  windDir: number;
  windSpeed: number;
  windGust?: number;
  // Additional variables
  pressure?: number | null;
  cape?: number | null;
  // Meta data
  latency: string;
  sparklineData: number[];
  analogCount: number;
  analogMatches?: AnalogPoint[];
  isAvailable?: boolean;
  // New enhanced features
  variables?: VariableToggle[];
  onVariableToggle?: (variableId: string, enabled: boolean) => void;
  onHorizonChange?: (horizon: string) => void;
  enableHorizonSlider?: boolean;
  maxHorizon?: number;
  className?: string;
}

export default function ForecastCard({
  horizon,
  temp,
  confidence,
  confidencePct,
  p05,
  p50,
  p95,
  windDir,
  windSpeed,
  windGust,
  pressure,
  cape,
  latency,
  sparklineData,
  analogCount,
  analogMatches = [],
  isAvailable = true,
  variables = [
    {
      id: 't2m',
      label: 'Temperature',
      unit: '°C',
      enabled: true,
      value: temp,
      p05,
      p95,
      available: true
    },
    {
      id: 'wind',
      label: 'Wind Speed',
      unit: 'm/s',
      enabled: false,
      value: windSpeed,
      p05: windSpeed - 2,
      p95: windSpeed + 3,
      available: true
    },
    {
      id: 'pressure',
      label: 'Pressure',
      unit: 'hPa',
      enabled: false,
      value: pressure,
      p05: pressure ? pressure - 5 : null,
      p95: pressure ? pressure + 5 : null,
      available: !!pressure
    },
    {
      id: 'cape',
      label: 'CAPE',
      unit: 'J/kg',
      enabled: false,
      value: cape,
      p05: cape ? cape - 100 : null,
      p95: cape ? cape + 200 : null,
      available: !!cape
    }
  ],
  onVariableToggle,
  onHorizonChange,
  enableHorizonSlider = false,
  maxHorizon = 48,
  className = ''
}: ForecastCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedVariable, setSelectedVariable] = useState('t2m');
  const [localHorizon, setLocalHorizon] = useState(
    parseInt(horizon.replace(/[^\d]/g, ''))
  );

  // Horizon slider handler with smooth transitions
  const handleHorizonChange = useCallback(
    (newHorizon: number) => {
      setLocalHorizon(newHorizon);
      if (onHorizonChange) {
        onHorizonChange(`${newHorizon}h`);
      }
    },
    [onHorizonChange]
  );

  // Variable toggle handler
  const handleVariableToggle = useCallback(
    (variableId: string) => {
      setSelectedVariable(variableId);
      if (onVariableToggle) {
        const variable = variables.find(v => v.id === variableId);
        if (variable) {
          onVariableToggle(variableId, !variable.enabled);
        }
      }
    },
    [variables, onVariableToggle]
  );

  // Get current active variable data
  const activeVariable = useMemo(() => {
    return (
      variables.find(v => v.id === selectedVariable) ||
      variables[0] || {
        id: 't2m',
        label: 'Temperature',
        unit: '°C',
        enabled: true,
        value: temp,
        p05,
        p95,
        available: true
      }
    );
  }, [variables, selectedVariable, temp, p05, p95]);

  // Enhanced sparkline with confidence bands
  const SparklineVisualization = useMemo(() => {
    const width = 160;
    const height = 48;
    const points = sparklineData.length;

    if (points === 0) return null;

    const xStep = width / (points - 1);
    const yMin = Math.min(activeVariable?.p05 || 0, ...sparklineData) - 0.5;
    const yMax = Math.max(activeVariable?.p95 || 0, ...sparklineData) + 0.5;
    const yRange = yMax - yMin;

    const yScale = (val: number) => height - ((val - yMin) / yRange) * height;

    // Main trend line
    const mainPath = sparklineData
      .map((val, i) => `${i === 0 ? 'M' : 'L'} ${i * xStep} ${yScale(val)}`)
      .join(' ');

    // Confidence band paths
    const upperBoundPath = sparklineData
      .map((_, i) => `${i * xStep},${yScale(activeVariable?.p95 || 0)}`)
      .join(' L ');

    const lowerBoundPath = sparklineData
      .map(
        (_, i) =>
          `${(points - 1 - i) * xStep},${yScale(activeVariable?.p05 || 0)}`
      )
      .join(' L ');

    const confidenceBandPath = `M ${upperBoundPath} L ${lowerBoundPath} Z`;

    // Analog pattern matches overlay
    const analogPaths = analogMatches.slice(0, 3).map(() => {
      const analogData = sparklineData.map(
        val => val + (Math.random() - 0.5) * confidence * 0.3
      );
      return analogData
        .map((val, i) => `${i === 0 ? 'M' : 'L'} ${i * xStep} ${yScale(val)}`)
        .join(' ');
    });

    return (
      <div className='relative'>
        <svg
          width={width}
          height={height}
          className='w-full'
          viewBox={`0 0 ${width} ${height}`}
          role='img'
          aria-label={`${activeVariable?.label || 'Temperature'} trend with confidence bands`}
        >
          <defs>
            <linearGradient
              id={`confidence-gradient-${horizon}`}
              x1='0%'
              y1='0%'
              x2='0%'
              y2='100%'
            >
              <stop offset='0%' stopColor='#3b82f6' stopOpacity='0.3' />
              <stop offset='50%' stopColor='#8b5cf6' stopOpacity='0.2' />
              <stop offset='100%' stopColor='#f59e0b' stopOpacity='0.3' />
            </linearGradient>

            <linearGradient
              id={`main-gradient-${horizon}`}
              x1='0%'
              y1='0%'
              x2='100%'
              y2='0%'
            >
              <stop offset='0%' stopColor='#06b6d4' />
              <stop offset='50%' stopColor='#3b82f6' />
              <stop offset='100%' stopColor='#8b5cf6' />
            </linearGradient>
          </defs>

          {/* Confidence band */}
          <path
            d={confidenceBandPath}
            fill={`url(#confidence-gradient-${horizon})`}
            className='transition-all duration-300'
          />

          {/* Analog pattern matches (faded background patterns) */}
          {analogPaths.map((path, index) => (
            <path
              key={index}
              d={path}
              stroke='#64748b'
              strokeWidth='1'
              fill='none'
              opacity={0.15 + index * 0.05}
              strokeDasharray='2,2'
            />
          ))}

          {/* Main trend line */}
          <path
            d={mainPath}
            stroke={`url(#main-gradient-${horizon})`}
            strokeWidth='2.5'
            fill='none'
            className='drop-shadow-sm'
          />

          {/* Data points */}
          {sparklineData.map((val, i) => (
            <circle
              key={i}
              cx={i * xStep}
              cy={yScale(val)}
              r='2'
              fill='#3b82f6'
              className='opacity-70 hover:opacity-100 transition-opacity'
            />
          ))}
        </svg>

        {/* Analog matches indicator */}
        {analogMatches.length > 0 && (
          <div className='absolute top-1 right-1 text-[8px] text-slate-500 font-mono'>
            {analogMatches.length} patterns
          </div>
        )}
      </div>
    );
  }, [sparklineData, activeVariable, analogMatches, horizon, confidence]);

  // Card styling with anomaly highlighting
  const cardGlow =
    confidencePct < 50
      ? {
          boxShadow:
            '0 0 16px rgba(251, 191, 36, 0.15), 0 4px 12px rgba(0,0,0,0.4)'
        }
      : { boxShadow: '0 4px 12px rgba(0,0,0,0.4)' };

  if (!isAvailable) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 0.6, y: 0 }}
        transition={{ duration: 0.5 }}
        className={`weather-card opacity-60 ${className}`}
        style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}
      >
        <div className='flex items-start justify-between'>
          <span className='text-muted-foreground text-base font-medium tracking-wide'>
            {horizon}
          </span>
          <span className='status-indicator unavailable'>N/A</span>
        </div>

        <div className='flex-1 flex flex-col items-center justify-center py-8'>
          <div className='text-muted-foreground text-sm text-center'>
            <div className='mb-2'>Unavailable</div>
            <div className='text-xs opacity-70'>Not enough valid analogs</div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`weather-card ${confidencePct < 50 ? 'low-confidence' : ''} relative group ${className}`}
      style={cardGlow}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      tabIndex={0}
      role='article'
      aria-label={`Forecast for ${horizon}: ${activeVariable?.value || '--'} ${activeVariable?.unit || '°C'} with ${confidencePct}% confidence`}
    >
      {/* Enhanced Tooltip */}
      <AnimatePresence>
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className='absolute top-full left-1/2 -translate-x-1/2 mt-2 z-20 bg-popover border border-border rounded-lg p-3 text-xs font-mono shadow-xl whitespace-nowrap pointer-events-none'
          >
            <div className='text-popover-foreground space-y-1'>
              <div className='font-semibold border-b border-border pb-1 mb-1'>
                {activeVariable?.label || 'Temperature'}
              </div>
              <div>
                p05: {activeVariable?.p05?.toFixed(1) || '--'}
                {activeVariable?.unit || '°C'}
              </div>
              <div>
                p50: {activeVariable?.value?.toFixed(1) || '--'}
                {activeVariable?.unit || '°C'}
              </div>
              <div>
                p95: {activeVariable?.p95?.toFixed(1) || '--'}
                {activeVariable?.unit || '°C'}
              </div>
              <div className='border-t border-border pt-1 mt-1'>
                <div>analogs: k={analogCount}</div>
                {analogMatches.length > 0 && (
                  <div>patterns: {analogMatches.length}</div>
                )}
              </div>
            </div>
            <div className='absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-popover border-l border-t border-border rotate-45'></div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header with Variable Toggles */}
      <div className='flex items-start justify-between mb-3'>
        <div className='flex items-center gap-2'>
          <span className='text-foreground text-base font-medium tracking-wide'>
            {horizon}
          </span>
          {enableHorizonSlider && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className='p-1 rounded hover:bg-accent transition-colors'
              aria-label='Show horizon controls'
            >
              <Settings2 size={12} className='text-muted-foreground' />
            </button>
          )}
        </div>
        <span
          className={`status-indicator ${confidencePct >= 70 ? 'ready' : confidencePct >= 50 ? 'warning' : 'error'}`}
          aria-label={`Confidence ${confidencePct} percent`}
          title={`Confidence: ${confidencePct}%`}
        >
          {confidencePct}%
        </span>
      </div>

      {/* Variable Toggle Buttons */}
      <div className='flex flex-wrap gap-1 mb-3'>
        {variables.map(variable => (
          <button
            key={variable.id}
            onClick={() => handleVariableToggle(variable.id)}
            disabled={!variable.available}
            className={`px-2 py-1 rounded text-[10px] font-medium transition-all duration-200 ${
              selectedVariable === variable.id
                ? 'bg-primary text-primary-foreground'
                : variable.available
                  ? 'bg-secondary text-secondary-foreground hover:bg-accent'
                  : 'bg-muted text-muted-foreground opacity-50 cursor-not-allowed'
            }`}
            title={`${variable.label}: ${variable.value?.toFixed(1) || 'N/A'} ${variable.unit}`}
          >
            {variable.label}
          </button>
        ))}
      </div>

      {/* Horizon Slider (shown when enabled) */}
      <AnimatePresence>
        {showDetails && enableHorizonSlider && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className='mb-4 p-3 bg-muted/50 rounded-md border border-border'
          >
            <div className='flex items-center gap-2 mb-2'>
              <label className='text-xs font-medium text-muted-foreground'>
                Horizon:
              </label>
              <span className='text-xs font-mono'>{localHorizon}h</span>
            </div>
            <input
              type='range'
              min='6'
              max={maxHorizon}
              step='6'
              value={localHorizon}
              onChange={e => handleHorizonChange(parseInt(e.target.value))}
              className='w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer slider'
            />
            <div className='flex justify-between text-[8px] text-muted-foreground mt-1'>
              <span>6h</span>
              <span>24h</span>
              <span>{maxHorizon}h</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Value Display */}
      <motion.div
        key={selectedVariable}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
        className='flex items-baseline gap-2 mb-2'
      >
        <span className='text-5xl font-light text-foreground tracking-tight text-tabular'>
          {activeVariable?.value?.toFixed(1) || '--'}
        </span>
        <span className='text-xl font-light text-muted-foreground'>
          {activeVariable?.unit || '°C'}
        </span>
      </motion.div>

      {/* Confidence Range */}
      <div className='text-sm text-muted-foreground font-mono mb-3'>
        <div>
          ±{confidence.toFixed(1)}
          {activeVariable?.unit || '°C'}
        </div>
        <div className='text-xs opacity-70'>
          range: {activeVariable?.p05?.toFixed(1)}–
          {activeVariable?.p95?.toFixed(1)}
          {activeVariable?.unit || '°C'}
        </div>
      </div>

      {/* Wind Information (shown for temperature) */}
      {selectedVariable === 't2m' && (
        <div className='flex items-center gap-4 mb-3'>
          <div className='flex items-center gap-2.5'>
            <div className='relative' style={{ width: 32, height: 32 }}>
              {/* Compass rose background */}
              <svg
                width='32'
                height='32'
                viewBox='0 0 32 32'
                className='absolute inset-0 opacity-25'
              >
                <circle
                  cx='16'
                  cy='16'
                  r='14'
                  stroke='currentColor'
                  strokeWidth='0.5'
                  fill='none'
                />
                <text
                  x='16'
                  y='5'
                  textAnchor='middle'
                  fontSize='4'
                  fill='currentColor'
                  fontWeight='bold'
                >
                  N
                </text>
                <text
                  x='27'
                  y='18'
                  textAnchor='middle'
                  fontSize='4'
                  fill='currentColor'
                >
                  E
                </text>
                <text
                  x='16'
                  y='30'
                  textAnchor='middle'
                  fontSize='4'
                  fill='currentColor'
                >
                  S
                </text>
                <text
                  x='5'
                  y='18'
                  textAnchor='middle'
                  fontSize='4'
                  fill='currentColor'
                >
                  W
                </text>
              </svg>
              {/* Wind arrow */}
              <svg
                width='32'
                height='32'
                viewBox='0 0 32 32'
                className='absolute inset-0 transition-transform duration-500'
                style={{
                  transform: `rotate(${windDir}deg)`,
                  transformOrigin: 'center'
                }}
              >
                <path
                  d='M16 8 L16 24 M16 8 L12 12 M16 8 L20 12'
                  stroke='#22d3ee'
                  strokeWidth='2.5'
                  fill='none'
                  strokeLinecap='round'
                  strokeLinejoin='round'
                />
              </svg>
            </div>
            <div className='flex flex-col'>
              <span className='text-cyan-400 text-sm font-mono leading-tight text-tabular'>
                {windSpeed.toFixed(1)} m/s
              </span>
              {windGust && (
                <span className='text-cyan-600 text-[10px] font-mono leading-tight'>
                  gust {windGust.toFixed(1)}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Sparkline with Confidence Bands */}
      <div className='mb-3'>{SparklineVisualization}</div>

      {/* Footer with Latency and Controls */}
      <div className='flex justify-between items-center text-[10px]'>
        <span className='text-muted-foreground font-mono'>{latency}</span>
        {analogMatches.length > 0 && (
          <button
            onClick={() => setShowDetails(!showDetails)}
            className='flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors'
            title='View analog pattern details'
          >
            <TrendingUp size={10} />
            <span>{analogMatches.length} patterns</span>
          </button>
        )}
      </div>
    </motion.div>
  );
}
