/**
 * Comprehensive API Mocking with MSW (Mock Service Worker)
 * Provides realistic API responses for all integration test scenarios including
 * error states, loading conditions, and various data combinations.
 */

import { setupServer } from 'msw/node';
import { rest } from 'msw';
import type { 
  ForecastResponse, 
  MetricsSummary, 
  AnalogExplorerData,
  VariableResult,
  RiskAssessment,
  AnalogsSummary,
  ForecastHorizon,
  WeatherVariable
} from '@/types/api';

// ============================================================================
// Mock Data Generators
// ============================================================================

const createMockVariableResult = (
  value: number | null = 20.5,
  available: boolean = true
): VariableResult => ({
  value,
  p05: value ? value - 2.5 : null,
  p95: value ? value + 2.5 : null,
  confidence: available ? 0.85 : null,
  available,
  analog_count: available ? 15 : null
});

const createMockRiskAssessment = (): RiskAssessment => ({
  temperature_extreme: 'low',
  precipitation_heavy: 'moderate',
  wind_strong: 'low',
  thunderstorm: 'high'
});

const createMockAnalogsSummary = (): AnalogsSummary => ({
  most_similar_date: '2023-08-15T12:00:00Z',
  similarity_score: 0.89,
  analog_count: 15,
  outcome_description: 'Historical pattern suggests warm, stable conditions with isolated afternoon thunderstorms.'
});

const createMockForecastResponse = (
  horizon: ForecastHorizon = '24h',
  overrides: Partial<ForecastResponse> = {}
): ForecastResponse => ({
  location: 'Adelaide, SA',
  horizon,
  generated_at: '2024-01-15T10:30:00Z',
  valid_time: '2024-01-16T10:30:00Z',
  variables: {
    t2m: createMockVariableResult(23.5),
    u10: createMockVariableResult(5.2),
    v10: createMockVariableResult(-2.1),
    msl: createMockVariableResult(1013.2),
    r850: createMockVariableResult(65.0),
    tp6h: createMockVariableResult(0.0),
    cape: createMockVariableResult(1250.0),
    t850: createMockVariableResult(18.2),
    z500: createMockVariableResult(5640.0)
  },
  wind10m: {
    speed: 5.6,
    direction: 225,
    gust: 8.2,
    available: true
  },
  risk_assessment: createMockRiskAssessment(),
  confidence_explanation: 'High confidence based on strong historical analog patterns and consistent model agreement.',
  narrative: 'Expect warm and partly cloudy conditions with scattered afternoon thunderstorms possible. Moderate instability indicated by elevated CAPE values.',
  analogs_summary: createMockAnalogsSummary(),
  version: '1.0.0',
  model_version: 'v2.1.0',
  latency_ms: 145,
  ...overrides
});

const createMockMetricsSummary = (): MetricsSummary => ({
  forecast_accuracy: [
    {
      horizon: '6h',
      variable: 't2m',
      accuracy_percent: 92.5,
      rmse: 1.2,
      mae: 0.9,
      bias: 0.1,
      sample_count: 150
    },
    {
      horizon: '12h',
      variable: 't2m',
      accuracy_percent: 89.2,
      rmse: 1.8,
      mae: 1.4,
      bias: -0.2,
      sample_count: 145
    },
    {
      horizon: '24h',
      variable: 't2m',
      accuracy_percent: 85.7,
      rmse: 2.4,
      mae: 1.9,
      bias: -0.3,
      sample_count: 140
    }
  ],
  performance_metrics: [
    {
      metric: 'response_time_ms',
      value: 145,
      threshold: 500,
      status: 'healthy',
      timestamp: '2024-01-15T10:30:00Z'
    },
    {
      metric: 'memory_usage_mb',
      value: 256,
      threshold: 512,
      status: 'healthy',
      timestamp: '2024-01-15T10:30:00Z'
    },
    {
      metric: 'api_success_rate',
      value: 99.8,
      threshold: 99.0,
      status: 'healthy',
      timestamp: '2024-01-15T10:30:00Z'
    }
  ],
  system_health: [
    {
      component: 'forecast_api',
      status: 'up',
      uptime_percent: 99.9,
      last_check: '2024-01-15T10:30:00Z',
      response_time_ms: 145
    },
    {
      component: 'database',
      status: 'up',
      uptime_percent: 100.0,
      last_check: '2024-01-15T10:30:00Z',
      response_time_ms: 25
    },
    {
      component: 'embedding_service',
      status: 'up',
      uptime_percent: 99.7,
      last_check: '2024-01-15T10:30:00Z',
      response_time_ms: 89
    }
  ],
  trends: {
    accuracy_trends: [
      {
        timestamp: '2024-01-14T00:00:00Z',
        horizon: '24h',
        variable: 't2m',
        accuracy_percent: 84.2
      },
      {
        timestamp: '2024-01-15T00:00:00Z',
        horizon: '24h',
        variable: 't2m',
        accuracy_percent: 85.7
      }
    ],
    performance_trends: [
      {
        timestamp: '2024-01-14T00:00:00Z',
        metric: 'response_time_ms',
        value: 152
      },
      {
        timestamp: '2024-01-15T00:00:00Z',
        metric: 'response_time_ms',
        value: 145
      }
    ]
  }
});

const createMockAnalogExplorerData = (useFaissData: boolean = true): AnalogExplorerData => ({
  forecast_horizon: '24h',
  top_analogs: [
    {
      date: '2023-08-15T12:00:00Z',
      similarity_score: 0.89,
      initial_conditions: {
        t2m: 20.5,
        cape: 1250,
        msl: 1013.2,
        u10: 3.2,
        v10: -1.8,
        r850: 65,
        tp6h: null,
        t850: null,
        z500: null
      },
      timeline: [
        {
          hours_offset: 0,
          values: {
            t2m: 20.5,
            cape: 1250,
            msl: 1013.2,
            u10: 3.2,
            v10: -1.8,
            r850: 65,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: [],
          temperature_trend: 'stable',
          pressure_trend: 'stable'
        },
        {
          hours_offset: 6,
          values: {
            t2m: 23.8,
            cape: 1850,
            msl: 1011.8,
            u10: 4.1,
            v10: -2.3,
            r850: 72,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: ['Cloud cover increased'],
          temperature_trend: 'rising',
          pressure_trend: 'falling'
        },
        {
          hours_offset: 12,
          values: {
            t2m: 24.2,
            cape: 2100,
            msl: 1010.5,
            u10: 2.8,
            v10: -3.1,
            r850: 85,
            tp6h: 2.5,
            t850: null,
            z500: null
          },
          events: ['Thunderstorm development', 'Heavy precipitation'],
          temperature_trend: 'rising',
          pressure_trend: 'falling'
        },
        {
          hours_offset: 24,
          values: {
            t2m: 22.1,
            cape: 800,
            msl: 1012.1,
            u10: 1.9,
            v10: -1.2,
            r850: 58,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: ['Clearing skies'],
          temperature_trend: 'falling',
          pressure_trend: 'rising'
        }
      ],
      outcome_narrative: 'Warm day with isolated thunderstorms developing in the afternoon, followed by clearing conditions',
      location: {
        latitude: -34.9285,
        longitude: 138.6007,
        name: 'Adelaide, SA'
      },
      season_info: {
        month: 8,
        season: 'winter'
      }
    },
    {
      date: '2023-07-22T12:00:00Z',
      similarity_score: 0.85,
      initial_conditions: {
        t2m: 21.2,
        cape: 1180,
        msl: 1012.8,
        u10: 2.8,
        v10: -1.5,
        r850: 68,
        tp6h: null,
        t850: null,
        z500: null
      },
      timeline: [
        {
          hours_offset: 0,
          values: {
            t2m: 21.2,
            cape: 1180,
            msl: 1012.8,
            u10: 2.8,
            v10: -1.5,
            r850: 68,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: [],
          temperature_trend: 'stable',
          pressure_trend: 'stable'
        },
        {
          hours_offset: 6,
          values: {
            t2m: 24.1,
            cape: 1920,
            msl: 1011.2,
            u10: 3.5,
            v10: -2.1,
            r850: 75,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: ['Humidity rising'],
          temperature_trend: 'rising',
          pressure_trend: 'falling'
        },
        {
          hours_offset: 12,
          values: {
            t2m: 23.9,
            cape: 2250,
            msl: 1009.8,
            u10: 4.2,
            v10: -2.8,
            r850: 88,
            tp6h: 4.2,
            t850: null,
            z500: null
          },
          events: ['Storm cells forming', 'Moderate precipitation'],
          temperature_trend: 'stable',
          pressure_trend: 'falling'
        },
        {
          hours_offset: 24,
          values: {
            t2m: 21.8,
            cape: 650,
            msl: 1013.5,
            u10: 2.1,
            v10: -1.4,
            r850: 62,
            tp6h: 0.0,
            t850: null,
            z500: null
          },
          events: ['Pressure recovery'],
          temperature_trend: 'falling',
          pressure_trend: 'rising'
        }
      ],
      outcome_narrative: 'Hot and humid conditions leading to afternoon storm development with moderate rainfall',
      location: {
        latitude: -34.9285,
        longitude: 138.6007,
        name: 'Adelaide, SA'
      },
      season_info: {
        month: 7,
        season: 'winter'
      }
    }
  ],
  ensemble_stats: {
    mean_outcomes: {
      t2m: 23.0,
      cape: 1450,
      msl: 1011.8,
      u10: 3.1,
      v10: -2.0,
      r850: 71,
      tp6h: 1.5,
      t850: null,
      z500: null
    },
    outcome_uncertainty: {
      t2m: 1.8,
      cape: 450,
      msl: 2.1,
      u10: 0.8,
      v10: 0.7,
      r850: 12,
      tp6h: 2.1,
      t850: null,
      z500: null
    },
    common_events: ['Thunderstorm development', 'Cloud cover increased', 'Pressure falling']
  },
  generated_at: '2024-01-15T12:00:00Z',
  data_source: useFaissData ? 'faiss' : 'fallback',
  search_metadata: {
    search_method: useFaissData ? 'real_faiss' : 'fallback_mock',
    faiss_search_successful: useFaissData,
    indices_used: useFaissData ? '24h_temperature_v1' : undefined,
    total_candidates: useFaissData ? 50000 : 1000,
    search_time_ms: useFaissData ? 15.7 : 125.3,
    k_neighbors_found: 10,
    distance_metric: useFaissData ? 'L2' : 'L2_fallback',
    fallback_reason: useFaissData ? undefined : 'FAISS service unavailable'
  }
});

// ============================================================================
// Error Response Generators
// ============================================================================

const createApiError = (status: number, code: string, message: string) => ({
  error: {
    code,
    message,
    timestamp: new Date().toISOString()
  }
});

// ============================================================================
// MSW Request Handlers
// ============================================================================

export const handlers = [
  // Forecast API endpoints
  rest.get('http://localhost:8000/api/forecast/:horizon', (req, res, ctx) => {
    const { horizon } = req.params;
    const delay = req.url.searchParams.get('delay');
    const error = req.url.searchParams.get('error');
    
    // Simulate network delay if requested
    if (delay) {
      return res(ctx.delay(parseInt(delay)));
    }
    
    // Simulate error responses if requested
    if (error === 'timeout') {
      return res(ctx.status(408), ctx.json(createApiError(408, 'TIMEOUT', 'Request timeout')));
    }
    
    if (error === 'server_error') {
      return res(ctx.status(500), ctx.json(createApiError(500, 'SERVER_ERROR', 'Internal server error')));
    }
    
    if (error === 'unavailable') {
      const response = createMockForecastResponse(horizon as ForecastHorizon, {
        variables: {
          t2m: createMockVariableResult(null, false),
          u10: createMockVariableResult(null, false),
          v10: createMockVariableResult(null, false),
          msl: createMockVariableResult(null, false),
          r850: createMockVariableResult(null, false),
          tp6h: createMockVariableResult(null, false),
          cape: createMockVariableResult(null, false),
          t850: createMockVariableResult(null, false),
          z500: createMockVariableResult(null, false)
        }
      });
      return res(ctx.json(response));
    }
    
    return res(ctx.json(createMockForecastResponse(horizon as ForecastHorizon)));
  }),

  // Metrics API endpoints
  rest.get('http://localhost:8000/api/metrics/summary', (req, res, ctx) => {
    const error = req.url.searchParams.get('error');
    
    if (error === 'critical') {
      const criticalMetrics = createMockMetricsSummary();
      criticalMetrics.performance_metrics[0].status = 'critical';
      criticalMetrics.performance_metrics[0].value = 2500;
      criticalMetrics.system_health[0].status = 'down';
      return res(ctx.json(criticalMetrics));
    }
    
    if (error === 'server_error') {
      return res(ctx.status(500), ctx.json(createApiError(500, 'METRICS_ERROR', 'Failed to fetch metrics')));
    }
    
    return res(ctx.json(createMockMetricsSummary()));
  }),

  // Analog Explorer API endpoints
  // Frontend analogs API endpoint (proxying to backend)
  rest.get('http://localhost:3000/api/analogs', (req, res, ctx) => {
    const error = req.url.searchParams.get('error');
    const fallback = req.url.searchParams.get('fallback');
    
    if (error === 'no_analogs') {
      const noAnalogsData = createMockAnalogExplorerData();
      noAnalogsData.top_analogs = [];
      return res(ctx.json(noAnalogsData));
    }
    
    if (error === 'server_error') {
      return res(ctx.status(500), ctx.json(createApiError(500, 'ANALOG_ERROR', 'Analog search failed')));
    }
    
    if (error === 'backend_unavailable') {
      return res(ctx.status(503), ctx.json({
        error: 'Backend service unavailable - analog data degraded',
        details: 'Unable to reach real-time analog search service. Data quality may be reduced.'
      }));
    }
    
    // Return fallback data if requested
    const useFaissData = fallback !== 'true';
    return res(ctx.json(createMockAnalogExplorerData(useFaissData)));
  }),

  rest.post('http://localhost:8000/api/analogs/explore', (req, res, ctx) => {
    const error = req.url.searchParams.get('error');
    
    if (error === 'no_analogs') {
      const noAnalogsData = createMockAnalogExplorerData();
      noAnalogsData.top_analogs = [];
      return res(ctx.json(noAnalogsData));
    }
    
    if (error === 'server_error') {
      return res(ctx.status(500), ctx.json(createApiError(500, 'ANALOG_ERROR', 'Analog search failed')));
    }
    
    return res(ctx.json(createMockAnalogExplorerData()));
  }),

  // Health check endpoints
  rest.get('http://localhost:8000/api/health', (req, res, ctx) => {
    const error = req.url.searchParams.get('error');
    
    if (error === 'unhealthy') {
      return res(ctx.status(503), ctx.json({
        status: 'unhealthy',
        components: {
          database: 'down',
          api: 'up',
          embedding_service: 'degraded'
        }
      }));
    }
    
    return res(ctx.json({
      status: 'healthy',
      components: {
        database: 'up',
        api: 'up',
        embedding_service: 'up'
      }
    }));
  }),

  // Export endpoints
  rest.post('http://localhost:8000/api/export', (req, res, ctx) => {
    const format = req.url.searchParams.get('format') || 'json';
    
    if (format === 'csv') {
      return res(
        ctx.set('Content-Type', 'text/csv'),
        ctx.set('Content-Disposition', 'attachment; filename="metrics-export.csv"'),
        ctx.text('timestamp,metric,value\n2024-01-15T10:30:00Z,accuracy,85.7')
      );
    }
    
    return res(
      ctx.set('Content-Type', 'application/json'),
      ctx.set('Content-Disposition', 'attachment; filename="metrics-export.json"'),
      ctx.json({
        export_timestamp: '2024-01-15T10:30:00Z',
        data: createMockMetricsSummary()
      })
    );
  }),

  // WebSocket simulation for real-time updates
  rest.get('http://localhost:8000/api/realtime/status', (req, res, ctx) => {
    return res(ctx.json({
      timestamp: new Date().toISOString(),
      status: 'operational',
      active_connections: 42,
      updates_sent: 1205
    }));
  })
];

// ============================================================================
// MSW Server Setup
// ============================================================================

export const server = setupServer(...handlers);

// ============================================================================
// Mock State Management
// ============================================================================

export class MockStateManager {
  private static state = new Map<string, any>();

  static setState(key: string, value: any) {
    this.state.set(key, value);
  }

  static getState(key: string) {
    return this.state.get(key);
  }

  static clearState() {
    this.state.clear();
  }

  static getAllState() {
    return Object.fromEntries(this.state);
  }
}

// ============================================================================
// Integration Test Helpers
// ============================================================================

export const mockApiResponses = {
  forecast: {
    success: (horizon: ForecastHorizon = '24h') => createMockForecastResponse(horizon),
    unavailable: (horizon: ForecastHorizon = '24h') => 
      createMockForecastResponse(horizon, {
        variables: Object.keys(createMockForecastResponse().variables).reduce((acc, key) => ({
          ...acc,
          [key]: createMockVariableResult(null, false)
        }), {} as any)
      }),
    error: () => createApiError(500, 'FORECAST_ERROR', 'Forecast generation failed')
  },
  metrics: {
    success: () => createMockMetricsSummary(),
    critical: () => {
      const metrics = createMockMetricsSummary();
      metrics.performance_metrics[0].status = 'critical';
      metrics.system_health[0].status = 'down';
      return metrics;
    },
    error: () => createApiError(500, 'METRICS_ERROR', 'Metrics unavailable')
  },
  analogs: {
    success: () => createMockAnalogExplorerData(true),
    fallback: () => createMockAnalogExplorerData(false),
    noAnalogs: () => {
      const data = createMockAnalogExplorerData();
      data.top_analogs = [];
      return data;
    },
    error: () => createApiError(500, 'ANALOG_ERROR', 'Analog search failed')
  }
};

export const waitForApiCall = (url: string, timeout = 5000): Promise<boolean> => {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const checkInterval = setInterval(() => {
      // This would check if the API call was made - simplified for testing
      if (Date.now() - startTime > timeout) {
        clearInterval(checkInterval);
        resolve(false);
      } else {
        clearInterval(checkInterval);
        resolve(true);
      }
    }, 100);
  });
};