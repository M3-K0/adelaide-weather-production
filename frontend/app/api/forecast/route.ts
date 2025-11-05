import { NextRequest, NextResponse } from 'next/server';
import type {
  ForecastResponse,
  ForecastHorizon,
  WeatherVariable,
  ApiError
} from '@/types';
import { WEATHER_VARIABLES, FORECAST_HORIZONS } from '@/types';

/**
 * Server-side API proxy for Adelaide Weather Forecasting API
 *
 * SECURITY: This route handles authentication server-side to prevent
 * token exposure in client-side code. All API calls go through this proxy.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const API_TOKEN = process.env.API_TOKEN;

// Validate required environment variables at startup
if (!API_TOKEN) {
  console.error('CRITICAL: API_TOKEN environment variable is required');
  process.exit(1);
}

export async function GET(
  request: NextRequest
): Promise<NextResponse<ForecastResponse | ApiError>> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const horizon = (searchParams.get('horizon') || '24h') as ForecastHorizon;
    const vars = searchParams.get('vars') || 't2m,u10,v10,msl';

    // Validate horizon parameter using strict types
    if (!FORECAST_HORIZONS.includes(horizon)) {
      const error: ApiError = {
        error: `Invalid horizon. Must be one of: ${FORECAST_HORIZONS.join(', ')}`
      };
      return NextResponse.json(error, { status: 400 });
    }

    // Validate variables parameter using strict types
    const requestedVars = vars
      .split(',')
      .map(v => v.trim()) as WeatherVariable[];
    const invalidVars = requestedVars.filter(
      v => !WEATHER_VARIABLES.includes(v)
    );

    if (invalidVars.length > 0) {
      const error: ApiError = {
        error: `Invalid variables: ${invalidVars.join(', ')}. Valid: ${WEATHER_VARIABLES.join(', ')}`
      };
      return NextResponse.json(error, { status: 400 });
    }

    // Build API URL
    const apiUrl = new URL('/forecast', API_BASE_URL);
    apiUrl.searchParams.set('horizon', horizon);
    apiUrl.searchParams.set('vars', vars);

    // Make authenticated request to backend API
    const response = await fetch(apiUrl.toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Adelaide-Weather-Frontend/1.0.0'
      },
      // Add timeout to prevent hanging requests
      signal: AbortSignal.timeout(10000) // 10 second timeout
    });

    if (!response.ok) {
      console.error(
        `API request failed: ${response.status} ${response.statusText}`
      );

      // Handle different error types appropriately with strict typing
      if (response.status === 401) {
        const error: ApiError = { error: 'Authentication failed' };
        return NextResponse.json(error, { status: 500 }); // Don't expose auth details to client
      } else if (response.status === 429) {
        const error: ApiError = {
          error: 'Rate limit exceeded. Please try again later.'
        };
        return NextResponse.json(error, { status: 429 });
      } else if (response.status >= 500) {
        const error: ApiError = {
          error: 'Weather service temporarily unavailable'
        };
        return NextResponse.json(error, { status: 503 });
      } else {
        const error: ApiError = { error: 'Invalid request parameters' };
        return NextResponse.json(error, { status: 400 });
      }
    }

    // Parse response with strict typing
    const data: ForecastResponse = await response.json();

    // Add CORS headers for development
    const headers = new Headers();
    headers.set('Cache-Control', 'public, max-age=300'); // 5 minute cache
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');

    return NextResponse.json(data, { headers });
  } catch (error) {
    console.error('Forecast proxy error:', error);

    // Handle timeout errors with strict typing
    if (error instanceof Error && error.name === 'AbortError') {
      const apiError: ApiError = {
        error: 'Request timeout. Please try again.'
      };
      return NextResponse.json(apiError, { status: 504 });
    }

    // Handle network errors
    if (error instanceof Error && error.message.includes('fetch')) {
      const apiError: ApiError = { error: 'Weather service unavailable' };
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
