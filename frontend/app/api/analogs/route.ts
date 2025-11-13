import { NextRequest, NextResponse } from 'next/server';
import type {
  AnalogExplorerData,
  ForecastHorizon,
  ApiError
} from '@/types';
import { FORECAST_HORIZONS, WEATHER_VARIABLES } from '@/types';

/**
 * Real API endpoint for Analog Explorer data
 * Direct integration with the backend `/api/analogs` endpoint
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const API_TOKEN = process.env.API_TOKEN;

/**
 * Call the real backend `/api/analogs` endpoint
 */
async function searchAnalogs(
  horizon: ForecastHorizon,
  variables?: string,
  k: number = 10,
  queryTime?: string
): Promise<AnalogExplorerData> {
  if (!API_TOKEN) {
    throw new Error('API authentication token not configured');
  }

  // Build the real API URL with parameters
  const backendUrl = new URL('/api/analogs', API_BASE_URL);
  backendUrl.searchParams.set('horizon', horizon);
  backendUrl.searchParams.set('k', k.toString());
  
  // Use provided variables or default set
  if (variables) {
    backendUrl.searchParams.set('variables', variables);
  } else {
    backendUrl.searchParams.set('variables', WEATHER_VARIABLES.join(','));
  }
  
  // Add query_time if provided
  if (queryTime) {
    backendUrl.searchParams.set('query_time', queryTime);
  }

  const response = await fetch(backendUrl.toString(), {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${API_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'Adelaide-Weather-Frontend/1.0.0'
    },
    signal: AbortSignal.timeout(15000) // 15 second timeout
  });

  if (!response.ok) {
    throw new Error(`Backend API request failed: ${response.status} ${response.statusText}`);
  }

  // Return the real API response directly - no synthetic generation
  const analogData = await response.json() as AnalogExplorerData;
  return analogData;
}

export async function GET(
  request: NextRequest
): Promise<NextResponse<AnalogExplorerData | ApiError>> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const horizon = (searchParams.get('horizon') || '24h') as ForecastHorizon;
    const variables = searchParams.get('variables') || undefined;
    const k = parseInt(searchParams.get('k') || '10');
    const queryTime = searchParams.get('query_time') || undefined;

    // Validate horizon parameter
    if (!FORECAST_HORIZONS.includes(horizon)) {
      const error: ApiError = {
        error: `Invalid horizon. Must be one of: ${FORECAST_HORIZONS.join(', ')}`
      };
      return NextResponse.json(error, { status: 400 });
    }

    // Validate k parameter
    if (isNaN(k) || k < 1 || k > 200) {
      const error: ApiError = {
        error: 'Parameter k must be an integer between 1 and 200'
      };
      return NextResponse.json(error, { status: 400 });
    }

    // Call the real backend `/api/analogs` endpoint
    const analogData = await searchAnalogs(horizon, variables, k, queryTime);

    // Add CORS headers for development
    const headers = new Headers();
    headers.set('Cache-Control', 'public, max-age=600'); // 10 minute cache for analog data
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');

    return NextResponse.json(analogData, { headers });
  } catch (error) {
    console.error('Analogs API integration error:', error);

    // Handle timeout errors
    if (error instanceof Error && error.name === 'AbortError') {
      const apiError: ApiError = {
        error: 'Backend request timeout. Please try again.'
      };
      return NextResponse.json(apiError, { status: 504 });
    }

    // Handle authentication errors
    if (error instanceof Error && error.message.includes('authentication')) {
      const apiError: ApiError = {
        error: 'Authentication failed with backend service'
      };
      return NextResponse.json(apiError, { status: 500 });
    }

    // Handle backend API errors
    if (error instanceof Error && error.message.includes('Backend API request failed')) {
      const status = error.message.includes('401') ? 500 : 
                    error.message.includes('429') ? 429 : 
                    error.message.includes('5') ? 503 : 400;
      
      const errorMessages = {
        401: 'Backend authentication failed',
        429: 'Rate limit exceeded. Please try again later.',
        503: 'Backend analog service temporarily unavailable',
        400: 'Invalid request parameters'
      };
      
      const apiError: ApiError = { 
        error: errorMessages[status as keyof typeof errorMessages] || 'Backend service error' 
      };
      return NextResponse.json(apiError, { status });
    }

    // Handle network errors
    if (error instanceof Error && error.message.includes('fetch')) {
      const apiError: ApiError = { error: 'Backend service unavailable' };
      return NextResponse.json(apiError, { status: 503 });
    }

    // Generic error handler
    const apiError: ApiError = { 
      error: error instanceof Error ? error.message : 'Internal server error' 
    };
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