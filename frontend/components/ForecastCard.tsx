/**
 * Enhanced Forecast Card Component with Risk Assessment and Analogs
 * Uses strict TypeScript types from the enhanced API schema
 */

import React, { useState } from 'react';
import { AlertTriangle, TrendingUp, Clock, Info } from 'lucide-react';
import type { ForecastResponse, RiskAssessment } from '@/types';
import { useMetrics } from '@/lib/MetricsProvider';

interface ForecastCardProps {
  forecast: ForecastResponse;
  className?: string;
}

export function ForecastCard({ forecast, className = '' }: ForecastCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [showAnalogs, setShowAnalogs] = useState(false);
  const metrics = useMetrics();

  // Extract temperature data with strict typing
  const t2m = forecast.variables.t2m;
  const wind = forecast.wind10m;

  if (!t2m?.available) {
    return (
      <div
        className={`bg-[#0E1116]/40 border border-[#1C1F26] rounded-lg p-6 opacity-60 ${className}`}
        style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}
      >
        <div className='flex items-start justify-between'>
          <span className='text-slate-500 text-base font-medium tracking-wide'>
            {forecast.horizon}
          </span>
          <span className='px-2.5 py-1 rounded-full text-xs font-semibold border bg-slate-800/50 border-slate-700 text-slate-500'>
            N/A
          </span>
        </div>

        <div className='flex-1 flex flex-col items-center justify-center py-8'>
          <div className='text-slate-600 text-sm text-center'>
            <div className='mb-2'>Unavailable</div>
            <div className='text-xs text-slate-700'>
              Not enough valid analogs
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Calculate confidence percentage
  const confidencePct = t2m.confidence
    ? Math.round(Math.max(0, Math.min(100, t2m.confidence * 100)))
    : 0;

  // Risk level styling
  const getRiskStyling = (level: string) => {
    switch (level) {
      case 'extreme':
        return {
          bg: 'bg-red-950/50',
          border: 'border-red-700',
          text: 'text-red-400'
        };
      case 'high':
        return {
          bg: 'bg-orange-950/50',
          border: 'border-orange-700',
          text: 'text-orange-400'
        };
      case 'moderate':
        return {
          bg: 'bg-yellow-950/50',
          border: 'border-yellow-700',
          text: 'text-yellow-400'
        };
      case 'low':
        return {
          bg: 'bg-blue-950/50',
          border: 'border-blue-700',
          text: 'text-blue-400'
        };
      default:
        return {
          bg: 'bg-slate-950/50',
          border: 'border-slate-700',
          text: 'text-slate-400'
        };
    }
  };

  // Get highest risk level for card accent
  const getHighestRisk = (risks: RiskAssessment): string => {
    const levels = ['minimal', 'low', 'moderate', 'high', 'extreme'];
    const riskValues = Object.values(risks);
    return riskValues.reduce((highest, current) => {
      const currentIndex = levels.indexOf(current);
      const highestIndex = levels.indexOf(highest);
      return currentIndex > highestIndex ? current : highest;
    }, 'minimal');
  };

  const highestRisk = getHighestRisk(forecast.risk_assessment);
  const cardStyling = getRiskStyling(highestRisk);

  // Card border and glow based on risk level
  const isHighRisk = ['high', 'extreme'].includes(highestRisk);
  const cardBorderClass = isHighRisk ? cardStyling.border : 'border-[#2A2F3A]';
  const cardGlow = isHighRisk
    ? {
        boxShadow:
          '0 0 16px rgba(239, 68, 68, 0.15), 0 4px 12px rgba(0,0,0,0.4)'
      }
    : { boxShadow: '0 4px 12px rgba(0,0,0,0.4)' };

  return (
    <div
      className={`bg-[#0E1116] border ${cardBorderClass} rounded-lg p-6 flex flex-col gap-4 hover:border-[#3A3F4A] transition-all focus-within:ring-2 focus-within:ring-cyan-500 focus-within:ring-offset-2 focus-within:ring-offset-[#0A0D12] relative group ${className}`}
      style={cardGlow}
      tabIndex={0}
      role='article'
      aria-label={`Forecast for ${forecast.horizon}: ${t2m.value?.toFixed(1) || 'N/A'} degrees Celsius with ${confidencePct}% confidence`}
    >
      {/* Header with horizon and confidence */}
      <div className='flex items-start justify-between'>
        <div className='flex items-center gap-2'>
          <span className='text-slate-300 text-base font-medium tracking-wide'>
            +{forecast.horizon}
          </span>
          {isHighRisk && (
            <AlertTriangle size={14} className={cardStyling.text} />
          )}
        </div>
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${cardStyling.bg} ${cardStyling.border} ${cardStyling.text}`}
          title={`Confidence: ${confidencePct}%`}
        >
          {confidencePct}%
        </span>
      </div>

      {/* Temperature display */}
      <div className='flex items-baseline gap-2'>
        <span className='text-6xl font-light text-slate-50 tracking-tight text-tabular'>
          {t2m.value?.toFixed(1) || '--'}
        </span>
        <span className='text-2xl font-light text-slate-400'>°C</span>
      </div>

      {/* Uncertainty range */}
      {t2m.p05 !== null && t2m.p95 !== null && (
        <div className='text-sm text-slate-400 font-mono -mt-1'>
          <div>
            ±{(Math.abs((t2m.p95 || 0) - (t2m.p05 || 0)) / 2).toFixed(1)}°C
          </div>
          <div className='text-xs text-slate-500'>
            p05–p95: {t2m.p05.toFixed(1)}–{t2m.p95.toFixed(1)}°C
          </div>
        </div>
      )}

      {/* CAPE indicator */}
      {forecast.variables.cape?.available &&
        forecast.variables.cape.value !== null && (
          <div className='flex items-center justify-between'>
            <span className='text-xs text-slate-400'>CAPE</span>
            <button
              onClick={() => {
                metrics.trackCapeModal(forecast.horizon);
                metrics.trackInteraction(
                  'cape_modal_open',
                  'forecast_card',
                  forecast.horizon
                );
                // Could open a detailed CAPE modal here
              }}
              className='text-sm font-mono text-amber-400 hover:text-amber-300 transition-colors'
            >
              {forecast.variables.cape.value.toFixed(0)} J/kg
            </button>
          </div>
        )}

      {/* Wind information */}
      {wind?.available && wind.speed !== null && wind.direction !== null && (
        <div className='flex items-center gap-3'>
          <div className='relative' style={{ width: 32, height: 32 }}>
            {/* Compass background */}
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
                stroke='#64748b'
                strokeWidth='0.5'
                fill='none'
              />
              <text
                x='16'
                y='5'
                textAnchor='middle'
                fontSize='4'
                fill='#64748b'
                fontWeight='bold'
              >
                N
              </text>
              <text
                x='27'
                y='18'
                textAnchor='middle'
                fontSize='4'
                fill='#64748b'
              >
                E
              </text>
              <text
                x='16'
                y='30'
                textAnchor='middle'
                fontSize='4'
                fill='#64748b'
              >
                S
              </text>
              <text
                x='5'
                y='18'
                textAnchor='middle'
                fontSize='4'
                fill='#64748b'
              >
                W
              </text>
            </svg>
            {/* Wind arrow */}
            <svg
              width='32'
              height='32'
              viewBox='0 0 32 32'
              className='absolute inset-0'
              style={{
                transform: `rotate(${wind.direction}deg)`,
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
            <span className='text-cyan-400 text-sm font-mono leading-tight'>
              {wind.speed.toFixed(1)} m/s
            </span>
            {wind.gust && (
              <span className='text-cyan-600 text-[10px] font-mono leading-tight'>
                gust {wind.gust.toFixed(1)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Risk Assessment */}
      <div className='space-y-2'>
        <div className='flex items-center gap-2'>
          <AlertTriangle size={14} className='text-slate-400' />
          <span className='text-xs font-medium text-slate-300 uppercase tracking-wide'>
            Risk Assessment
          </span>
        </div>
        <div className='grid grid-cols-2 gap-2 text-xs'>
          {Object.entries(forecast.risk_assessment).map(([risk, level]) => {
            const styling = getRiskStyling(level);
            return (
              <div
                key={risk}
                className={`px-2 py-1 rounded border ${styling.bg} ${styling.border} ${styling.text}`}
              >
                <div className='font-medium capitalize'>
                  {risk.replace('_', ' ')}
                </div>
                <div className='text-[10px] opacity-80 capitalize'>{level}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Analogs Summary */}
      <div className='space-y-2'>
        <button
          onClick={() => {
            metrics.trackInteraction(
              'analogs_toggle',
              'forecast_card',
              forecast.horizon
            );
            setShowAnalogs(!showAnalogs);
          }}
          className='flex items-center gap-2 text-xs font-medium text-slate-300 uppercase tracking-wide hover:text-slate-100 transition-colors'
        >
          <TrendingUp size={14} className='text-slate-400' />
          Historical Analogs
        </button>

        {showAnalogs && (
          <div className='space-y-2 text-xs bg-slate-900/50 rounded p-3 border border-slate-700'>
            <div>
              <span className='text-slate-400'>Most similar:</span>{' '}
              <span className='text-slate-200 font-mono'>
                {forecast.analogs_summary.most_similar_date}
              </span>
            </div>
            <div>
              <span className='text-slate-400'>Similarity:</span>{' '}
              <span className='text-slate-200'>
                {(forecast.analogs_summary.similarity_score * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className='text-slate-400'>Analogs used:</span>{' '}
              <span className='text-slate-200'>
                {forecast.analogs_summary.analog_count}
              </span>
            </div>
            <div className='text-slate-300 text-[11px] leading-relaxed mt-2'>
              {forecast.analogs_summary.outcome_description}
            </div>
          </div>
        )}
      </div>

      {/* Narrative and metadata */}
      <div className='space-y-2'>
        <button
          onClick={() => {
            metrics.trackInteraction(
              'details_toggle',
              'forecast_card',
              forecast.horizon
            );
            setShowDetails(!showDetails);
          }}
          className='flex items-center gap-2 text-xs font-medium text-slate-300 uppercase tracking-wide hover:text-slate-100 transition-colors'
        >
          <Info size={14} className='text-slate-400' />
          Forecast Details
        </button>

        {showDetails && (
          <div className='space-y-3 text-xs bg-slate-900/50 rounded p-3 border border-slate-700'>
            <div className='text-slate-300 text-[11px] leading-relaxed'>
              {forecast.narrative}
            </div>

            <div className='text-slate-300 text-[11px] leading-relaxed'>
              <strong>Confidence:</strong> {forecast.confidence_explanation}
            </div>

            <div className='flex items-center gap-2 pt-2 border-t border-slate-600'>
              <Clock size={12} className='text-slate-500' />
              <span className='text-slate-500 font-mono'>
                Generated: {new Date(forecast.generated_at).toLocaleString()}
              </span>
            </div>

            <div className='flex items-center gap-2'>
              <span className='text-slate-500 font-mono'>
                Latency: {forecast.latency_ms}ms
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
