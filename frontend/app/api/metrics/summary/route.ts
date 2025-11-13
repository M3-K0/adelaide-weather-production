import { NextRequest, NextResponse } from 'next/server';
import { ForecastHorizon, WeatherVariable } from '@/types/api';
import { AccuracyMetric, PerformanceMetric, SystemHealthMetric, MetricsSummary, TimeRange } from '@/lib/metricsApi';

/**
 * Metrics Summary API Endpoint
 * 
 * Provides aggregated metrics data for the dashboard including
 * accuracy metrics, performance indicators, and system health status.
 */

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // Parse and validate query parameters with null safety
    const timeRange = (searchParams.get('timeRange') || '24h') as TimeRange;
    const horizonsParam = searchParams.get('horizons');
    const variablesParam = searchParams.get('variables');
    const includeConfidence = searchParams.get('includeConfidence') === 'true';

    // Validate and parse horizons parameter
    const horizons: ForecastHorizon[] = horizonsParam 
      ? horizonsParam.split(',').map(h => h.trim()).filter(h => h) as ForecastHorizon[]
      : ['6h', '12h', '24h', '48h'];

    // Validate and parse variables parameter  
    const variables: WeatherVariable[] = variablesParam
      ? variablesParam.split(',').map(v => v.trim()).filter(v => v) as WeatherVariable[]
      : ['t2m', 'u10', 'v10', 'msl', 'cape'];

    // Validate timeRange parameter
    const validTimeRanges: TimeRange[] = ['1h', '6h', '24h', '7d', '30d'];
    if (!validTimeRanges.includes(timeRange)) {
      return NextResponse.json(
        { error: `Invalid timeRange. Must be one of: ${validTimeRanges.join(', ')}` },
        { status: 400 }
      );
    }

    // Validate that we have at least one horizon and variable
    if (horizons.length === 0) {
      return NextResponse.json(
        { error: 'At least one forecast horizon must be specified' },
        { status: 400 }
      );
    }

    if (variables.length === 0) {
      return NextResponse.json(
        { error: 'At least one weather variable must be specified' },
        { status: 400 }
      );
    }

    // Generate metrics data with proper error handling
    const metricsData = await generateMetricsData(timeRange, horizons, variables, includeConfidence);

    // Validate that we have meaningful data
    if (!metricsData || (!metricsData.forecast_accuracy?.length && !metricsData.performance_metrics?.length)) {
      return NextResponse.json(
        { 
          error: 'No metrics data available for the selected parameters',
          details: 'The requested time range or parameters may not have available data'
        },
        { status: 404 }
      );
    }

    return NextResponse.json(metricsData, {
      status: 200,
      headers: {
        'Cache-Control': 'public, max-age=30', // Short cache for metrics data
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    });
  } catch (error) {
    console.error('Error generating metrics summary:', error);
    
    // Detailed error handling
    const errorMessage = error instanceof Error ? error.message : 'Failed to generate metrics summary';
    
    // Check if it's a validation error
    if (errorMessage.includes('Invalid') || errorMessage.includes('validation')) {
      return NextResponse.json(
        { 
          error: 'Parameter validation failed',
          details: errorMessage 
        },
        { status: 400 }
      );
    }

    // Check if it's a timeout or network error
    if (errorMessage.includes('timeout') || errorMessage.includes('network')) {
      return NextResponse.json(
        { 
          error: 'Metrics service temporarily unavailable',
          details: 'Unable to fetch metrics data. Please try again later.'
        },
        { status: 503 }
      );
    }
    
    // Generic server error
    return NextResponse.json(
      { 
        error: 'Internal server error',
        details: 'An unexpected error occurred while generating metrics'
      },
      { status: 500 }
    );
  }
}

/**
 * Generate mock metrics data for demonstration
 * In production, this would integrate with Prometheus queries
 * 
 * Enhanced with null safety and fallback indicators
 */
async function generateMetricsData(
  timeRange: TimeRange,
  horizons: ForecastHorizon[],
  variables: WeatherVariable[],
  includeConfidence: boolean
): Promise<MetricsSummary> {
  const now = new Date();
  const nowISO = now.toISOString();

  // Validate input parameters
  if (!horizons || horizons.length === 0) {
    throw new Error('Invalid input: horizons array is empty');
  }
  if (!variables || variables.length === 0) {
    throw new Error('Invalid input: variables array is empty');
  }

  // Generate forecast accuracy metrics with null safety
  const forecast_accuracy: AccuracyMetric[] = [];
  
  try {
    horizons.forEach(horizon => {
      if (!horizon) return; // Skip null/undefined horizons
      
      variables.forEach(variable => {
        if (!variable) return; // Skip null/undefined variables
        
        try {
          // Simulate realistic accuracy based on horizon and variable
          const baseAccuracy = getBaseAccuracy(variable);
          const horizonMultiplier = getHorizonMultiplier(horizon);
          
          if (baseAccuracy == null || horizonMultiplier == null) {
            console.warn(`Skipping invalid accuracy calculation for ${variable}@${horizon}`);
            return;
          }
          
          const accuracy = baseAccuracy * horizonMultiplier;
          
          forecast_accuracy.push({
            horizon,
            variable,
            mae: generateMAE(variable, horizon) ?? 0,
            bias: generateBias(variable) ?? 0,
            accuracy_percent: Math.max(0, Math.min(100, accuracy + (Math.random() - 0.5) * 5)), // Clamp to 0-100
            confidence_interval: generateConfidenceInterval(variable, horizon) ?? 0,
            last_updated: nowISO,
          });
        } catch (err) {
          console.warn(`Error generating accuracy metric for ${variable}@${horizon}:`, err);
        }
      });
    });
  } catch (error) {
    console.error('Error generating forecast accuracy metrics:', error);
    // Continue with empty array rather than failing completely
  }

  // Generate performance metrics
  const performance_metrics: PerformanceMetric[] = [
    {
      metric_name: 'API Response Time',
      value: 120 + Math.random() * 80, // 120-200ms
      unit: 'ms',
      status: 'good',
      threshold_warning: 500,
      threshold_critical: 1000,
      last_updated: nowISO,
    },
    {
      metric_name: 'Model Inference Time',
      value: 45 + Math.random() * 25, // 45-70ms
      unit: 'ms',
      status: 'good',
      threshold_warning: 200,
      threshold_critical: 500,
      last_updated: nowISO,
    },
    {
      metric_name: 'Data Freshness',
      value: 2 + Math.random() * 8, // 2-10 minutes
      unit: 'minutes',
      status: 'good',
      threshold_warning: 30,
      threshold_critical: 60,
      last_updated: nowISO,
    },
    {
      metric_name: 'Cache Hit Rate',
      value: 85 + Math.random() * 12, // 85-97%
      unit: '%',
      status: 'good',
      threshold_warning: 70,
      threshold_critical: 50,
      last_updated: nowISO,
    },
    {
      metric_name: 'Request Rate',
      value: 25 + Math.random() * 15, // 25-40 req/s
      unit: 'req/s',
      status: 'good',
      threshold_warning: 100,
      threshold_critical: 200,
      last_updated: nowISO,
    },
    {
      metric_name: 'Error Rate',
      value: Math.random() * 2, // 0-2%
      unit: '%',
      status: 'good',
      threshold_warning: 5,
      threshold_critical: 10,
      last_updated: nowISO,
    },
  ];

  // Update status based on thresholds
  performance_metrics.forEach(metric => {
    const isInverted = metric.unit === 'ms' || metric.unit === 'minutes';
    if (isInverted) {
      if (metric.value >= metric.threshold_critical) metric.status = 'critical';
      else if (metric.value >= metric.threshold_warning) metric.status = 'warning';
      else metric.status = 'good';
    } else {
      if (metric.value <= metric.threshold_critical) metric.status = 'critical';
      else if (metric.value <= metric.threshold_warning) metric.status = 'warning';
      else metric.status = 'good';
    }
  });

  // Generate system health metrics
  const system_health: SystemHealthMetric[] = [
    {
      component: 'API Server',
      status: 'up',
      uptime_percent: 99.5 + Math.random() * 0.5,
      last_check: nowISO,
      response_time_ms: 35 + Math.random() * 20,
    },
    {
      component: 'Database',
      status: 'up',
      uptime_percent: 99.8 + Math.random() * 0.2,
      last_check: nowISO,
      response_time_ms: 12 + Math.random() * 8,
    },
    {
      component: 'Redis Cache',
      status: 'up',
      uptime_percent: 99.9 + Math.random() * 0.1,
      last_check: nowISO,
      response_time_ms: 1 + Math.random() * 3,
    },
    {
      component: 'ML Model',
      status: 'up',
      uptime_percent: 99.2 + Math.random() * 0.8,
      last_check: nowISO,
      response_time_ms: 65 + Math.random() * 30,
    },
  ];

  // Generate trend data with error handling
  let trends;
  try {
    trends = generateTrendData(timeRange);
  } catch (error) {
    console.warn('Error generating trend data:', error);
    // Provide empty trends as fallback
    trends = {
      accuracy_trends: [],
      performance_trends: [],
      confidence_trends: [],
    };
  }

  // Prepare final metrics summary with data source indication
  const result: MetricsSummary = {
    forecast_accuracy: forecast_accuracy || [],
    performance_metrics: performance_metrics || [],
    system_health: system_health || [],
    trends: trends || { accuracy_trends: [], performance_trends: [], confidence_trends: [] },
    generated_at: nowISO,
    time_range: timeRange,
    data_source: 'fallback' as any, // Indicate this is mock/fallback data
  };

  // Validate result has meaningful data
  const hasData = result.forecast_accuracy.length > 0 || 
                  result.performance_metrics.length > 0 || 
                  result.system_health.length > 0;
  
  if (!hasData) {
    console.warn('Generated metrics summary contains no data');
  }

  return result;
}

/**
 * Helper functions for generating realistic mock data
 * Enhanced with null safety checks
 */
function getBaseAccuracy(variable: WeatherVariable): number | null {
  if (!variable) return null;
  
  const accuracyMap: Record<WeatherVariable, number> = {
    't2m': 92,    // Temperature is usually quite accurate
    'u10': 85,    // Wind components have more uncertainty
    'v10': 85,
    'msl': 95,    // Pressure is very predictable
    'r850': 88,   // Humidity moderate accuracy
    'tp6h': 75,   // Precipitation is hardest to predict
    'cape': 78,   // CAPE has high uncertainty
    't850': 90,   // Upper air temperature
    'z500': 93,   // Geopotential height
  };
  return accuracyMap[variable] ?? 85; // Provide fallback value
}

function getHorizonMultiplier(horizon: ForecastHorizon): number | null {
  if (!horizon) return null;
  
  const multiplierMap: Record<ForecastHorizon, number> = {
    '6h': 1.0,
    '12h': 0.96,
    '24h': 0.91,
    '48h': 0.85,
  };
  return multiplierMap[horizon] ?? 0.8; // Provide fallback value
}

function generateMAE(variable: WeatherVariable, horizon: ForecastHorizon): number | null {
  if (!variable || !horizon) return null;
  
  const baseMAE: Record<WeatherVariable, number> = {
    't2m': 1.2,
    'u10': 2.1,
    'v10': 2.1,
    'msl': 0.8,
    'r850': 8.5,
    'tp6h': 1.5,
    'cape': 250,
    't850': 1.5,
    'z500': 15,
  };
  
  const horizonMultiplier = horizon === '6h' ? 0.8 : horizon === '12h' ? 1.0 : horizon === '24h' ? 1.3 : 1.8;
  const baseValue = baseMAE[variable] ?? 1.0; // Provide fallback
  return baseValue * horizonMultiplier * (0.8 + Math.random() * 0.4);
}

function generateBias(variable: WeatherVariable): number | null {
  if (!variable) return null;
  
  // Bias should be close to zero for good models
  return (Math.random() - 0.5) * 0.6; // -0.3 to 0.3
}

function generateConfidenceInterval(variable: WeatherVariable, horizon: ForecastHorizon): number | null {
  if (!variable || !horizon) return null;
  
  const baseCI: Record<WeatherVariable, number> = {
    't2m': 3.5,
    'u10': 5.2,
    'v10': 5.2,
    'msl': 2.1,
    'r850': 15,
    'tp6h': 8.5,
    'cape': 350,
    't850': 4.0,
    'z500': 25,
  };
  
  const horizonMultiplier = horizon === '6h' ? 0.9 : horizon === '12h' ? 1.1 : horizon === '24h' ? 1.4 : 1.9;
  const baseValue = baseCI[variable] ?? 3.0; // Provide fallback
  return baseValue * horizonMultiplier * (0.9 + Math.random() * 0.2);
}

function generateTrendData(timeRange: TimeRange) {
  const intervals = getTimeRangeIntervals(timeRange);
  const now = new Date();
  
  const accuracy_trends = [];
  const performance_trends = [];
  const confidence_trends = [];
  
  for (let i = 0; i < intervals.count; i++) {
    const timestamp = new Date(now.getTime() - (intervals.count - i - 1) * intervals.intervalMs);
    
    accuracy_trends.push({
      timestamp: timestamp.toISOString(),
      value: 88 + Math.sin(i / 5) * 4 + Math.random() * 3, // Oscillating around 88-95%
    });
    
    performance_trends.push({
      timestamp: timestamp.toISOString(),
      value: 140 + Math.sin(i / 3) * 25 + Math.random() * 20, // Response time 115-185ms
    });
    
    confidence_trends.push({
      timestamp: timestamp.toISOString(),
      value: 82 + Math.sin(i / 4) * 8 + Math.random() * 5, // Confidence 75-95%
    });
  }
  
  return {
    accuracy_trends,
    performance_trends,
    confidence_trends,
  };
}

function getTimeRangeIntervals(timeRange: TimeRange): { count: number; intervalMs: number } {
  switch (timeRange) {
    case '1h':
      return { count: 12, intervalMs: 5 * 60 * 1000 }; // 5-minute intervals
    case '6h':
      return { count: 24, intervalMs: 15 * 60 * 1000 }; // 15-minute intervals
    case '24h':
      return { count: 24, intervalMs: 60 * 60 * 1000 }; // 1-hour intervals
    case '7d':
      return { count: 28, intervalMs: 6 * 60 * 60 * 1000 }; // 6-hour intervals
    case '30d':
      return { count: 30, intervalMs: 24 * 60 * 60 * 1000 }; // 1-day intervals
    default:
      return { count: 24, intervalMs: 60 * 60 * 1000 };
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}