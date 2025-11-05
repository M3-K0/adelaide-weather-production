/**
 * Analog Explorer Demo Page
 * Demonstrates the AnalogExplorer component with interactive features
 */

'use client';

import React, { useState } from 'react';
import { AnalogExplorer } from '@/components';
import { useAnalogData } from '@/lib/useAnalogData';
import type { ForecastHorizon, AnalogPattern } from '@/types';
import { FORECAST_HORIZONS } from '@/types';
import { 
  TrendingUp, 
  RefreshCw, 
  AlertCircle, 
  Clock, 
  Info,
  BarChart3 
} from 'lucide-react';

export default function AnalogDemoPage() {
  const [selectedHorizon, setSelectedHorizon] = useState<ForecastHorizon>('24h');
  const [selectedAnalog, setSelectedAnalog] = useState<AnalogPattern | null>(null);
  
  const { data, loading, error, refetch, lastFetch } = useAnalogData(selectedHorizon, {
    autoFetch: true,
    cacheDuration: 5 * 60 * 1000, // 5 minutes for demo
    retryOnError: true,
    maxRetries: 2
  });

  const handleAnalogSelect = (analog: AnalogPattern) => {
    setSelectedAnalog(analog);
  };

  const handleRefresh = async () => {
    setSelectedAnalog(null);
    await refetch();
  };

  return (
    <div className="min-h-screen bg-[#0A0D12] text-slate-100">
      {/* Header */}
      <div className="border-b border-[#1C1F26] bg-[#0E1116]/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingUp size={24} className="text-cyan-400" />
              <h1 className="text-2xl font-bold text-slate-100">
                Analog Pattern Explorer
              </h1>
              <span className="px-2 py-1 rounded text-xs font-medium bg-cyan-950/50 border border-cyan-700 text-cyan-400">
                Demo
              </span>
            </div>
            
            {/* Controls */}
            <div className="flex items-center gap-4">
              {/* Horizon Selector */}
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-slate-400" />
                <select
                  value={selectedHorizon}
                  onChange={(e) => setSelectedHorizon(e.target.value as ForecastHorizon)}
                  className="px-3 py-1.5 rounded bg-slate-800 border border-slate-600 text-slate-200 text-sm focus:border-cyan-500 focus:outline-none"
                >
                  {FORECAST_HORIZONS.map(horizon => (
                    <option key={horizon} value={horizon}>
                      +{horizon}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-200 text-sm transition-colors"
                title="Refresh data"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
          </div>
          
          {/* Status Bar */}
          <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
            {lastFetch && (
              <div className="flex items-center gap-1">
                <Clock size={12} />
                <span>Last updated: {lastFetch.toLocaleTimeString()}</span>
              </div>
            )}
            
            {data && (
              <div className="flex items-center gap-1">
                <BarChart3 size={12} />
                <span>{data.top_analogs.length} patterns loaded</span>
              </div>
            )}
            
            {error && (
              <div className="flex items-center gap-1 text-red-400">
                <AlertCircle size={12} />
                <span>Error: {error}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Introduction */}
        <div className="mb-8 bg-[#0E1116] border border-[#1C1F26] rounded-lg p-6">
          <div className="flex items-start gap-3">
            <Info size={20} className="text-cyan-400 mt-0.5" />
            <div>
              <h2 className="text-lg font-semibold text-slate-100 mb-2">
                About Analog Pattern Explorer
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed mb-3">
                The Analog Pattern Explorer finds the top 5 most similar historical weather patterns 
                to current conditions and shows you what happened next. Use the interactive timeline 
                to scrub through each analog's progression and explore different outcomes.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                  <h4 className="font-medium text-slate-200 mb-1">Interactive Timeline</h4>
                  <p className="text-slate-400">
                    Play, pause, and scrub through historical patterns to see how weather evolved
                  </p>
                </div>
                <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                  <h4 className="font-medium text-slate-200 mb-1">Similarity Matching</h4>
                  <p className="text-slate-400">
                    Patterns ranked by similarity score showing most relevant historical cases
                  </p>
                </div>
                <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                  <h4 className="font-medium text-slate-200 mb-1">Export Data</h4>
                  <p className="text-slate-400">
                    Download analog data as CSV or JSON for further analysis
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Analog Explorer Component */}
        {data || loading || error ? (
          <AnalogExplorer
            data={data!}
            horizon={selectedHorizon}
            loading={loading}
            error={error}
            onAnalogSelect={handleAnalogSelect}
            className="mb-8"
          />
        ) : null}

        {/* Selected Analog Details */}
        {selectedAnalog && (
          <div className="bg-[#0E1116] border border-[#1C1F26] rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <BarChart3 size={20} className="text-cyan-400" />
              <h3 className="text-lg font-semibold text-slate-100">
                Selected Analog Details
              </h3>
              <span className="px-2 py-1 rounded text-xs font-medium bg-cyan-950/50 border border-cyan-700 text-cyan-400">
                {new Date(selectedAnalog.date).toLocaleDateString()}
              </span>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Analog Information */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-slate-300 mb-2">Pattern Overview</h4>
                  <div className="bg-slate-900/50 rounded p-3 border border-slate-700 space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Date:</span>
                      <span className="text-slate-200 font-mono">
                        {new Date(selectedAnalog.date).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Similarity:</span>
                      <span className="text-slate-200">
                        {(selectedAnalog.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Season:</span>
                      <span className="text-slate-200 capitalize">
                        {selectedAnalog.season_info.season}
                      </span>
                    </div>
                    {selectedAnalog.location && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Location:</span>
                        <span className="text-slate-200 text-right">
                          {selectedAnalog.location.name || 
                           `${selectedAnalog.location.latitude.toFixed(2)}, ${selectedAnalog.location.longitude.toFixed(2)}`}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Timeline Summary */}
                <div>
                  <h4 className="text-sm font-medium text-slate-300 mb-2">Timeline Summary</h4>
                  <div className="bg-slate-900/50 rounded p-3 border border-slate-700 text-sm">
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      <div className="text-center">
                        <div className="text-slate-400 text-xs">Duration</div>
                        <div className="text-slate-200 font-mono">
                          {Math.max(...selectedAnalog.timeline.map(p => p.hours_offset))}h
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-slate-400 text-xs">Data Points</div>
                        <div className="text-slate-200 font-mono">
                          {selectedAnalog.timeline.length}
                        </div>
                      </div>
                    </div>
                    
                    {/* Events Summary */}
                    {selectedAnalog.timeline.some(p => p.events && p.events.length > 0) && (
                      <div>
                        <div className="text-slate-400 text-xs mb-1">Notable Events:</div>
                        <ul className="space-y-1">
                          {selectedAnalog.timeline
                            .filter(p => p.events && p.events.length > 0)
                            .slice(0, 3)
                            .map((point, index) => (
                              <li key={index} className="flex items-start gap-1 text-xs">
                                <span className="text-cyan-400 mt-0.5">+{point.hours_offset}h:</span>
                                <span className="text-slate-300">
                                  {point.events![0]}
                                </span>
                              </li>
                            ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Outcome Description */}
              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-2">What Happened Next</h4>
                <div className="bg-slate-900/50 rounded p-4 border border-slate-700">
                  <p className="text-slate-200 text-sm leading-relaxed">
                    {selectedAnalog.outcome_narrative}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-[#1C1F26] text-center text-xs text-slate-500">
          <p>
            Analog Pattern Explorer • Adelaide Weather Forecasting System
          </p>
          <p className="mt-1">
            This demo uses simulated data. In production, data would come from the 
            historical weather pattern matching service.
          </p>
        </div>
      </div>
    </div>
  );
}