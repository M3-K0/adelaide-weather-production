import { NextRequest, NextResponse } from 'next/server';
import type {
  AnalogExplorerData,
  AnalogPattern,
  ForecastHorizon,
  WeatherVariable,
  ApiError
} from '@/types';
import { FORECAST_HORIZONS, WEATHER_VARIABLES } from '@/types';

/**
 * Mock API endpoint for Analog Explorer data
 * In production, this would proxy to the actual backend service
 * 
 * TODO: Replace with actual backend integration when available
 */

// const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
// const API_TOKEN = process.env.API_TOKEN;

// Mock data generator for development
function generateMockAnalogData(horizon: ForecastHorizon): AnalogExplorerData {
  const baseDate = new Date();
  baseDate.setFullYear(baseDate.getFullYear() - 1); // One year ago

  const seasons = ['summer', 'autumn', 'winter', 'spring'] as const;
  const months = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]; // December to November
  
  const generateAnalogPattern = (index: number): AnalogPattern => {
    const patternDate = new Date(baseDate);
    patternDate.setDate(patternDate.getDate() - (index * 30 + Math.random() * 100));
    
    const month = patternDate.getMonth() + 1;
    const season = seasons[Math.floor(month / 3) % 4];
    
    // Generate initial conditions
    const initialConditions: Record<WeatherVariable, number | null> = {
      't2m': 15 + (Math.random() - 0.5) * 20,
      'u10': (Math.random() - 0.5) * 20,
      'v10': (Math.random() - 0.5) * 20,
      'msl': 1013 + (Math.random() - 0.5) * 40,
      'r850': 50 + Math.random() * 50,
      'tp6h': Math.random() * 10,
      'cape': Math.random() * 3000,
      't850': 12 + (Math.random() - 0.5) * 18,
      'z500': 5800 + (Math.random() - 0.5) * 400
    };

    // Generate timeline points
    const timelineHours = [0, 6, 12, 18, 24, 30, 36, 42, 48];
    const timeline = timelineHours.map(hours => {
      const tempTrend = Math.random() < 0.33 ? 'rising' : Math.random() < 0.5 ? 'falling' : 'stable';
      const pressureTrend = Math.random() < 0.33 ? 'rising' : Math.random() < 0.5 ? 'falling' : 'stable';
      
      const events: string[] = [];
      if (Math.random() < 0.2) events.push('Light rain began');
      if (Math.random() < 0.15) events.push('Wind speed increased');
      if (Math.random() < 0.1) events.push('Temperature spike');
      if (Math.random() < 0.05) events.push('Thunderstorm activity');

      const values: Record<WeatherVariable, number | null> = {};
      Object.keys(initialConditions).forEach(variable => {
        const initial = initialConditions[variable as WeatherVariable];
        if (initial !== null) {
          // Add some variation over time
          const variation = (Math.random() - 0.5) * 0.2 * initial;
          values[variable as WeatherVariable] = initial + variation;
        } else {
          values[variable as WeatherVariable] = null;
        }
      });

      return {
        hours_offset: hours,
        values,
        events: events.length > 0 ? events : undefined,
        temperature_trend: tempTrend as 'rising' | 'falling' | 'stable',
        pressure_trend: pressureTrend as 'rising' | 'falling' | 'stable'
      };
    });

    // Generate outcome narrative
    const outcomes = [
      'Temperature gradually increased with clear skies developing. Wind remained light throughout the period.',
      'Steady cooling trend with increasing cloud cover. Light precipitation developed after 24 hours.',
      'Stable conditions with minor temperature fluctuations. High pressure system dominated the region.',
      'Rapid temperature rise followed by thunderstorm development. Strong winds accompanied the storm.',
      'Gradual pressure fall with increasing humidity. Overcast conditions persisted for 48 hours.'
    ];

    return {
      date: patternDate.toISOString(),
      similarity_score: 0.95 - (index * 0.1) - Math.random() * 0.1,
      initial_conditions: initialConditions,
      timeline,
      outcome_narrative: outcomes[index % outcomes.length],
      location: {
        latitude: -34.9285 + (Math.random() - 0.5) * 2, // Around Adelaide
        longitude: 138.6007 + (Math.random() - 0.5) * 2,
        name: `Station ${index + 1}`
      },
      season_info: {
        month,
        season
      }
    };
  };

  const topAnalogs = Array.from({ length: 5 }, (_, i) => generateAnalogPattern(i));

  // Generate ensemble statistics
  const ensembleStats = {
    mean_outcomes: {} as Record<WeatherVariable, number | null>,
    outcome_uncertainty: {} as Record<WeatherVariable, number | null>,
    common_events: [
      'Temperature increase',
      'Wind speed variation',
      'Pressure changes',
      'Cloud development'
    ]
  };

  WEATHER_VARIABLES.forEach(variable => {
    const values = topAnalogs
      .map(analog => analog.timeline[analog.timeline.length - 1]?.values[variable])
      .filter(v => v !== null) as number[];
    
    if (values.length > 0) {
      ensembleStats.mean_outcomes[variable] = values.reduce((a, b) => a + b, 0) / values.length;
      const variance = values.reduce((sum, val) => sum + Math.pow(val - ensembleStats.mean_outcomes[variable]!, 2), 0) / values.length;
      ensembleStats.outcome_uncertainty[variable] = Math.sqrt(variance);
    } else {
      ensembleStats.mean_outcomes[variable] = null;
      ensembleStats.outcome_uncertainty[variable] = null;
    }
  });

  return {
    forecast_horizon: horizon,
    top_analogs: topAnalogs,
    ensemble_stats: ensembleStats,
    generated_at: new Date().toISOString()
  };
}

export async function GET(
  request: NextRequest
): Promise<NextResponse<AnalogExplorerData | ApiError>> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const horizon = (searchParams.get('horizon') || '24h') as ForecastHorizon;

    // Validate horizon parameter
    if (!FORECAST_HORIZONS.includes(horizon)) {
      const error: ApiError = {
        error: `Invalid horizon. Must be one of: ${FORECAST_HORIZONS.join(', ')}`
      };
      return NextResponse.json(error, { status: 400 });
    }

    // In production, this would make a request to the actual backend
    // For now, return mock data
    const mockData = generateMockAnalogData(horizon);

    // TODO: Replace with actual API call when backend is available
    /*
    const apiUrl = new URL('/analogs', API_BASE_URL);
    apiUrl.searchParams.set('horizon', horizon);

    const response = await fetch(apiUrl.toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Adelaide-Weather-Frontend/1.0.0'
      },
      signal: AbortSignal.timeout(15000) // 15 second timeout for analog data
    });

    if (!response.ok) {
      console.error(
        `Analogs API request failed: ${response.status} ${response.statusText}`
      );

      if (response.status === 401) {
        const error: ApiError = { error: 'Authentication failed' };
        return NextResponse.json(error, { status: 500 });
      } else if (response.status === 429) {
        const error: ApiError = {
          error: 'Rate limit exceeded. Please try again later.'
        };
        return NextResponse.json(error, { status: 429 });
      } else if (response.status >= 500) {
        const error: ApiError = {
          error: 'Analog service temporarily unavailable'
        };
        return NextResponse.json(error, { status: 503 });
      } else {
        const error: ApiError = { error: 'Invalid request parameters' };
        return NextResponse.json(error, { status: 400 });
      }
    }

    const data: AnalogExplorerData = await response.json();
    */

    // Add CORS headers for development
    const headers = new Headers();
    headers.set('Cache-Control', 'public, max-age=600'); // 10 minute cache for analog data
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');

    return NextResponse.json(mockData, { headers });
  } catch (error) {
    console.error('Analogs proxy error:', error);

    // Handle timeout errors
    if (error instanceof Error && error.name === 'AbortError') {
      const apiError: ApiError = {
        error: 'Request timeout. Please try again.'
      };
      return NextResponse.json(apiError, { status: 504 });
    }

    // Handle network errors
    if (error instanceof Error && error.message.includes('fetch')) {
      const apiError: ApiError = { error: 'Analog service unavailable' };
      return NextResponse.json(apiError, { status: 503 });
    }

    // Generic error handler
    const apiError: ApiError = { error: 'Internal server error' };
    return NextResponse.json(apiError, { status: 500 });
  }
}

// Handle preflight requests for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}