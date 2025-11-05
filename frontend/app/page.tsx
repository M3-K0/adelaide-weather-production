'use client';

import React, { useState, useEffect } from 'react';
import { Activity, Settings, Info, BarChart3, MapPin } from 'lucide-react';
import useSWR from 'swr';
import { useMetrics } from '@/lib/ClientMetricsProvider';
import { ForecastCard } from '@/components/ForecastCard';
import { StatusBar } from '@/components/StatusBar';
import type { ForecastResponse } from '@/types';

// Note: Using enhanced types from @/types

// API fetcher using secure server-side proxy
const fetcher = async (url: string) => {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `API Error: ${response.status}`);
  }

  return response.json();
};

export default function Dashboard() {
  const [activeNav, setActiveNav] = useState('dashboard');
  const [lastUpdated, setLastUpdated] = useState(0);
  const metrics = useMetrics();
  const [selectedVariables, setSelectedVariables] = useState([
    't2m',
    'u10',
    'v10'
  ]);
  const [selectedHorizons, setSelectedHorizons] = useState([
    '6h',
    '12h',
    '24h',
    '48h'
  ]);
  const [enabledVariables, setEnabledVariables] = useState<
    Record<string, string[]>
  >({
    '6h': ['t2m'],
    '12h': ['t2m'],
    '24h': ['t2m'],
    '48h': ['t2m']
  });

  // Fetch forecast data for all horizons with enhanced variables
  const {
    data: forecasts,
    error,
    isLoading,
    mutate
  } = useSWR<Record<string, ForecastResponse>>(
    '/api/forecasts-all',
    async () => {
      const horizons = selectedHorizons;
      const results: Record<string, ForecastResponse> = {};
      const timer = metrics.startTimer();

      for (const horizon of horizons) {
        try {
          // Include additional variables for enhanced features
          const vars = 't2m,u10,v10,msl,cape';
          const apiTimer = metrics.startTimer();
          const data = await fetcher(
            `/api/forecast?horizon=${horizon}&vars=${vars}`
          );
          const duration = apiTimer();

          // Track API response time
          metrics.trackAPICall(`/api/forecast`, 200, duration);

          results[horizon] = data;
        } catch (err) {
          console.error(`Failed to fetch ${horizon} forecast:`, err);
          metrics.trackForecastError(horizon, 'fetch_failed');
        }
      }

      // Process forecast data for metrics
      if (Object.keys(results).length > 0) {
        metrics.processForecastData(results);
      }

      // Track overall fetch duration
      const totalDuration = timer();
      metrics.trackForecastRender(
        totalDuration,
        'all',
        selectedVariables.length
      );

      return results;
    },
    {
      refreshInterval: 60000, // Refresh every minute
      revalidateOnFocus: false
    }
  );

  // Handle variable toggle for forecast cards
  const handleVariableToggle = (
    horizon: string,
    variableId: string,
    enabled: boolean
  ) => {
    // Track variable toggle metrics
    metrics.trackVariableToggle(variableId, enabled ? 'show' : 'hide');
    metrics.trackInteraction('variable_toggle', 'forecast_card', horizon);

    setEnabledVariables(prev => ({
      ...prev,
      [horizon]: enabled
        ? [...(prev[horizon] || []), variableId]
        : (prev[horizon] || []).filter(id => id !== variableId)
    }));
  };

  // Handle horizon change from slider
  const handleHorizonChange = (oldHorizon: string, newHorizon: string) => {
    // Track horizon change metrics
    metrics.trackHorizonChange(oldHorizon, newHorizon);
    metrics.trackInteraction('horizon_change', 'horizon_selector', newHorizon);

    setSelectedHorizons(prev =>
      prev.map(h => (h === oldHorizon ? newHorizon : h))
    );
    // Trigger refresh of forecast data
    mutate();
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdated(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fallback data when API is unavailable or during initial load
  const fallbackForecasts = [
    {
      horizon: '+6h',
      temp: 15.8,
      confidence: 1.1,
      confidencePct: 78,
      p05: 14.2,
      p50: 15.7,
      p95: 17.4,
      windDir: 185,
      windSpeed: 3.2,
      windGust: 4.8,
      latency: '42ms',
      analogCount: 50,
      sparklineData: [15.0, 15.3, 15.6, 15.8, 15.9, 16.0, 15.7],
      isAvailable: true
    },
    {
      horizon: '+12h',
      temp: 18.3,
      confidence: 1.6,
      confidencePct: 71,
      p05: 16.2,
      p50: 18.1,
      p95: 20.4,
      windDir: 210,
      windSpeed: 4.7,
      windGust: 6.2,
      latency: '38ms',
      analogCount: 48,
      sparklineData: [16.5, 17.2, 17.8, 18.1, 18.3, 18.4, 18.2],
      isAvailable: true
    },
    {
      horizon: '+24h',
      temp: 21.4,
      confidence: 2.3,
      confidencePct: 56,
      p05: 18.6,
      p50: 21.2,
      p95: 24.2,
      windDir: 245,
      windSpeed: 5.9,
      windGust: 7.8,
      latency: '71ms',
      analogCount: 42,
      sparklineData: [19.2, 20.1, 20.8, 21.2, 21.4, 21.6, 21.3],
      isAvailable: true
    },
    {
      horizon: '+48h',
      temp: 16.7,
      confidence: 3.4,
      confidencePct: 48,
      p05: 12.8,
      p50: 16.5,
      p95: 20.6,
      windDir: 270,
      windSpeed: 4.3,
      windGust: 5.9,
      latency: '89ms',
      analogCount: 35,
      sparklineData: [18.5, 17.8, 17.2, 16.9, 16.7, 16.5, 16.8],
      isAvailable: true
    }
  ];

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'details', label: 'Details', icon: Activity },
    { id: 'status', label: 'System Status', icon: Settings },
    { id: 'about', label: 'About', icon: Info }
  ];

  const now = new Date();
  const currentTime = now.toLocaleString('en-AU', {
    timeZone: 'Australia/Adelaide',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  const utcTime = now.toLocaleString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  return (
    <div
      className='min-h-screen bg-[#0A0D12] text-slate-100 flex flex-col md:flex-row'
      style={{
        background:
          'radial-gradient(ellipse at center, #0E1116 0%, #0A0D12 100%)'
      }}
    >
      {/* Sidebar */}
      <aside className='w-full md:w-52 bg-[#0E1116] border-b md:border-b-0 md:border-r border-[#2A2F3A] flex flex-col py-4 md:py-6'>
        <div className='px-4 mb-4 md:mb-8'>
          <div className='w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center'>
            <Activity size={20} className='text-white' />
          </div>
        </div>

        <nav className='flex md:flex-col flex-row overflow-x-auto md:overflow-visible flex-1 px-3 gap-1'>
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activeNav === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  metrics.trackInteraction(
                    'navigation_click',
                    'sidebar',
                    item.id
                  );
                  setActiveNav(item.id);
                }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-[#0A0D12] ${
                  isActive
                    ? 'bg-slate-800/50 text-slate-50 font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
                }`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className='flex-1 flex flex-col'>
        {/* Top Bar */}
        <header className='h-auto md:h-16 border-b border-[#2A2F3A] px-4 md:px-8 py-3 md:py-0 flex flex-col md:flex-row md:items-center justify-between gap-3 md:gap-0 bg-[#0E1116]/80'>
          <div className='flex flex-col md:flex-row md:items-center gap-2 md:gap-3'>
            <h1 className='text-lg md:text-xl font-light tracking-tight text-slate-50'>
              Adelaide Analog Forecasts
            </h1>
            <div className='flex items-center gap-1.5'>
              <MapPin size={12} className='text-slate-500' />
              <span className='text-xs text-slate-400 font-mono'>
                Adelaide, AU
              </span>
              <span className='text-[10px] text-slate-600 ml-1'>
                -34.93°S 138.60°E
              </span>
            </div>
          </div>

          <div className='flex flex-wrap items-center gap-2 text-xs'>
            <span className='px-2 py-1 bg-[#1C1F26] border border-[#2A2F3A] rounded text-[10px] text-slate-600 font-mono opacity-70'>
              model: a7c3f92
            </span>
            <span className='px-2 py-1 bg-[#1C1F26] border border-[#2A2F3A] rounded text-[10px] text-slate-600 font-mono opacity-70'>
              index: 2e8b4d1
            </span>
            <span className='px-2 py-1 bg-[#1C1F26] border border-[#2A2F3A] rounded text-[10px] text-slate-600 font-mono opacity-70'>
              dataset: v3.2.1
            </span>
            <span className='px-2 py-1 bg-[#1C1F26] border border-[#2A2F3A] rounded text-[10px] text-slate-300 font-mono'>
              {currentTime} ACDT
            </span>
            <span className='text-[10px] text-slate-500 font-mono'>
              as of {utcTime} UTC · updated {lastUpdated}s ago
            </span>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className='flex-1 p-4 md:p-8'>
          {isLoading && (
            <div className='grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 max-w-7xl mx-auto'>
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className='weather-card loading-pulse h-64 rounded-lg'
                />
              ))}
            </div>
          )}

          {error && (
            <div className='max-w-7xl mx-auto'>
              <div className='bg-red-950/50 border border-red-700 rounded-lg p-6 text-center'>
                <p className='text-red-400'>Failed to load forecast data</p>
                <p className='text-red-600 text-sm mt-1'>{error.message}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && forecasts && (
            <div className='grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 max-w-7xl mx-auto'>
              {Object.entries(forecasts).map(([horizon, forecast]) => {
                // Extract all available variables
                const t2m = forecast.variables.t2m;
                const u10 = forecast.variables.u10;
                const v10 = forecast.variables.v10;
                const msl = forecast.variables.msl;
                const cape = forecast.variables.cape;
                const wind = forecast.wind10m;

                if (!t2m) {
                  return null; // Skip if missing temperature data
                }

                // Calculate wind speed from u10 and v10 components
                const windSpeed =
                  u10?.value && v10?.value
                    ? Math.sqrt(Math.pow(u10.value, 2) + Math.pow(v10.value, 2))
                    : wind?.speed || 0;

                // Calculate wind direction from u10 and v10 components
                const windDirection =
                  u10?.value && v10?.value
                    ? ((Math.atan2(v10.value, u10.value) * 180) / Math.PI +
                        270) %
                      360
                    : wind?.direction || 0;

                // Generate mock analog matches for demonstration
                const analogCount = t2m.analog_count || 0;
                const analogMatches = Array.from(
                  { length: Math.min(analogCount, 5) },
                  (_, i) => ({
                    timestamp: new Date(
                      Date.now() - (i + 1) * 24 * 60 * 60 * 1000
                    ).toISOString(),
                    value: (t2m.value || 0) + (Math.random() - 0.5) * 2,
                    similarity: 0.95 - i * 0.02
                  })
                );

                // Prepare variables for the enhanced card
                const variables = [
                  {
                    id: 't2m',
                    label: 'Temperature',
                    unit: '°C',
                    enabled: enabledVariables[horizon]?.includes('t2m') ?? true,
                    value: t2m.value,
                    p05: t2m.p05,
                    p95: t2m.p95,
                    available: t2m.available
                  },
                  {
                    id: 'wind',
                    label: 'Wind Speed',
                    unit: 'm/s',
                    enabled:
                      enabledVariables[horizon]?.includes('wind') ?? false,
                    value: windSpeed,
                    p05: windSpeed - 2,
                    p95: windSpeed + 3,
                    available: !!(u10?.available && v10?.available)
                  },
                  {
                    id: 'pressure',
                    label: 'Pressure',
                    unit: 'hPa',
                    enabled:
                      enabledVariables[horizon]?.includes('pressure') ?? false,
                    value: msl?.value,
                    p05: msl?.p05,
                    p95: msl?.p95,
                    available: msl?.available ?? false
                  },
                  {
                    id: 'cape',
                    label: 'CAPE',
                    unit: 'J/kg',
                    enabled:
                      enabledVariables[horizon]?.includes('cape') ?? false,
                    value: cape?.value,
                    p05: cape?.p05,
                    p95: cape?.p95,
                    available: cape?.available ?? false
                  }
                ];

                const cardData = {
                  horizon: `+${horizon}`,
                  temp: t2m.value || 0,
                  confidence:
                    t2m.p95 && t2m.p05 ? Math.abs(t2m.p95 - t2m.p05) / 2 : 0,
                  confidencePct: Math.round(t2m.confidence || 0),
                  p05: t2m.p05 || 0,
                  p50: t2m.value || 0,
                  p95: t2m.p95 || 0,
                  windDir: windDirection,
                  windSpeed: windSpeed,
                  windGust: wind?.gust,
                  pressure: msl?.value,
                  cape: cape?.value,
                  latency: `${forecast.latency_ms}ms`,
                  analogCount,
                  analogMatches,
                  sparklineData:
                    t2m.p05 !== null && t2m.p95 !== null && t2m.value !== null
                      ? [
                          t2m.p05,
                          t2m.p05 + (t2m.value - t2m.p05) * 0.2,
                          t2m.p05 + (t2m.value - t2m.p05) * 0.4,
                          t2m.p05 + (t2m.value - t2m.p05) * 0.6,
                          t2m.value,
                          t2m.value + (t2m.p95 - t2m.value) * 0.3,
                          t2m.value + (t2m.p95 - t2m.value) * 0.6,
                          t2m.p95
                        ]
                      : [],
                  isAvailable: t2m.available,
                  variables,
                  onVariableToggle: (variableId: string, enabled: boolean) =>
                    handleVariableToggle(horizon, variableId, enabled),
                  onHorizonChange: (newHorizon: string) =>
                    handleHorizonChange(horizon, newHorizon.replace('+', '')),
                  enableHorizonSlider: true,
                  maxHorizon: 48
                };

                return <ForecastCard key={horizon} {...cardData} />;
              })}
            </div>
          )}

          {/* Graceful fallback to demo data when API is unavailable */}
          {!isLoading && !error && !forecasts && (
            <div className='grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 max-w-7xl mx-auto'>
              {fallbackForecasts.map((forecast, i) => {
                // Enhanced fallback data structure for demo purposes
                const enhancedForecast = {
                  ...forecast,
                  variables: [
                    {
                      id: 't2m',
                      label: 'Temperature',
                      unit: '°C',
                      enabled: true,
                      value: forecast.temp,
                      p05: forecast.p05,
                      p95: forecast.p95,
                      available: true
                    },
                    {
                      id: 'wind',
                      label: 'Wind Speed',
                      unit: 'm/s',
                      enabled: false,
                      value: forecast.windSpeed,
                      p05: forecast.windSpeed - 2,
                      p95: forecast.windSpeed + 3,
                      available: true
                    },
                    {
                      id: 'pressure',
                      label: 'Pressure',
                      unit: 'hPa',
                      enabled: false,
                      value: 1013 + i * 2,
                      p05: 1008 + i * 2,
                      p95: 1018 + i * 2,
                      available: true
                    },
                    {
                      id: 'cape',
                      label: 'CAPE',
                      unit: 'J/kg',
                      enabled: false,
                      value: 500 + i * 100,
                      p05: 400 + i * 100,
                      p95: 700 + i * 100,
                      available: true
                    }
                  ],
                  analogMatches: Array.from(
                    { length: Math.min(forecast.analogCount, 4) },
                    (_, j) => ({
                      timestamp: new Date(
                        Date.now() - (j + 1) * 24 * 60 * 60 * 1000
                      ).toISOString(),
                      value: forecast.temp + (Math.random() - 0.5) * 2,
                      similarity: 0.95 - j * 0.03
                    })
                  ),
                  onVariableToggle: (variableId: string, enabled: boolean) =>
                    console.log(
                      `Demo: Toggle ${variableId} to ${enabled} for ${forecast.horizon}`
                    ),
                  onHorizonChange: (newHorizon: string) =>
                    console.log(
                      `Demo: Change horizon from ${forecast.horizon} to ${newHorizon}`
                    ),
                  enableHorizonSlider: true,
                  maxHorizon: 48,
                  pressure: 1013 + i * 2,
                  cape: 500 + i * 100
                };

                return <ForecastCard key={i} {...enhancedForecast} />;
              })}
            </div>
          )}
        </div>
        
        {/* Status Bar */}
        <StatusBar />
      </main>
    </div>
  );
}
