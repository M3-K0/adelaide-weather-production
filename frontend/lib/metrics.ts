/**
 * Frontend Metrics Collection System
 *
 * Collects UI interaction metrics, forecast quality metrics, and ensemble spread metrics
 * for comprehensive observability of the weather forecasting frontend.
 */

// Conditional import for server-side only
let register: any, Counter: any, Histogram: any, Gauge: any, Summary: any;

if (typeof window === 'undefined') {
  // Server-side only
  const promClient = require('prom-client');
  register = promClient.register;
  Counter = promClient.Counter;
  Histogram = promClient.Histogram;
  Gauge = promClient.Gauge;
  Summary = promClient.Summary;
  
  // Clear existing metrics on reload to prevent conflicts
  register.clear();
} else {
  // Client-side fallback - no-op implementations
  const noop = () => {};
  const NoOpMetric = class {
    inc() {}
    observe() {}
    set() {}
  };
  
  register = { 
    clear: noop, 
    metrics: () => Promise.resolve(''), 
    resetMetrics: noop 
  };
  Counter = NoOpMetric;
  Histogram = NoOpMetric;
  Gauge = NoOpMetric;
  Summary = NoOpMetric;
}

// UI Interaction Metrics
export const uiInteractionCounter = new Counter({
  name: 'ui_interactions_total',
  help: 'Total number of UI interactions',
  labelNames: ['interaction_type', 'component', 'horizon']
});

export const variableToggleCounter = new Counter({
  name: 'variable_toggle_total',
  help: 'Total number of variable toggles in the UI',
  labelNames: ['variable', 'action'] // action: show/hide
});

export const horizonChangeCounter = new Counter({
  name: 'horizon_change_total',
  help: 'Total number of forecast horizon changes',
  labelNames: ['from_horizon', 'to_horizon']
});

export const capeModalOpenCounter = new Counter({
  name: 'cape_modal_opens_total',
  help: 'Total number of CAPE modal opens',
  labelNames: ['horizon']
});

// Forecast Quality Metrics
export const capeDistributionHistogram = new Histogram({
  name: 'cape_distribution_values',
  help: 'Distribution of CAPE values in forecasts',
  buckets: [0, 100, 250, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000],
  labelNames: ['horizon']
});

export const analogSimilarityScore = new Summary({
  name: 'analog_similarity_score',
  help: 'Similarity scores of analog pattern matching',
  labelNames: ['horizon', 'variable'],
  percentiles: [0.05, 0.5, 0.95]
});

export const forecastConfidenceGauge = new Gauge({
  name: 'forecast_confidence_current',
  help: 'Current forecast confidence levels',
  labelNames: ['horizon', 'variable']
});

// Ensemble Spread Metrics by Variable
export const ensembleSpreadGauge = new Gauge({
  name: 'ensemble_spread_current',
  help: 'Current ensemble spread (p95 - p05) by variable',
  labelNames: ['horizon', 'variable']
});

export const ensembleSpreadHistogram = new Histogram({
  name: 'ensemble_spread_distribution',
  help: 'Distribution of ensemble spread values',
  buckets: [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0],
  labelNames: ['horizon', 'variable']
});

// Forecast Confidence Percentiles
export const confidencePercentilesGauge = new Gauge({
  name: 'forecast_confidence_percentiles',
  help: 'Forecast confidence at different percentiles',
  labelNames: ['horizon', 'variable', 'percentile'] // percentile: p05, p25, p50, p75, p95
});

// Performance Metrics
export const pageLoadDuration = new Histogram({
  name: 'page_load_duration_seconds',
  help: 'Time to load dashboard page',
  buckets: [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
});

export const forecastRenderDuration = new Histogram({
  name: 'forecast_render_duration_seconds',
  help: 'Time to render forecast cards',
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
  labelNames: ['horizon', 'variable_count']
});

export const apiResponseTime = new Histogram({
  name: 'frontend_api_response_time_seconds',
  help: 'API response time as measured by frontend',
  buckets: [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
  labelNames: ['endpoint', 'status_code']
});

// Error Metrics
export const uiErrorCounter = new Counter({
  name: 'ui_errors_total',
  help: 'Total number of UI errors',
  labelNames: ['error_type', 'component']
});

export const forecastErrorCounter = new Counter({
  name: 'forecast_errors_total',
  help: 'Total number of forecast-related errors',
  labelNames: ['horizon', 'error_type']
});

/**
 * UI Interaction Tracking Functions
 */
export const trackUIInteraction = (
  interactionType: string,
  component: string,
  horizon?: string
) => {
  uiInteractionCounter.inc({
    interaction_type: interactionType,
    component: component,
    horizon: horizon || 'all'
  });
};

export const trackVariableToggle = (
  variable: string,
  action: 'show' | 'hide'
) => {
  variableToggleCounter.inc({ variable, action });
};

export const trackHorizonChange = (fromHorizon: string, toHorizon: string) => {
  horizonChangeCounter.inc({
    from_horizon: fromHorizon,
    to_horizon: toHorizon
  });
};

export const trackCapeModalOpen = (horizon: string) => {
  capeModalOpenCounter.inc({ horizon });
};

/**
 * Forecast Quality Tracking Functions
 */
export const trackCapeDistribution = (capeValue: number, horizon: string) => {
  if (capeValue !== null && capeValue !== undefined && !isNaN(capeValue)) {
    capeDistributionHistogram.observe({ horizon }, capeValue);
  }
};

export const trackAnalogSimilarity = (
  score: number,
  horizon: string,
  variable: string
) => {
  if (score !== null && score !== undefined && !isNaN(score)) {
    analogSimilarityScore.observe({ horizon, variable }, score);
  }
};

export const updateForecastConfidence = (
  confidence: number,
  horizon: string,
  variable: string
) => {
  if (confidence !== null && confidence !== undefined && !isNaN(confidence)) {
    forecastConfidenceGauge.set({ horizon, variable }, confidence);
  }
};

/**
 * Ensemble Spread Tracking Functions
 */
export const updateEnsembleSpread = (
  spread: number,
  horizon: string,
  variable: string
) => {
  if (spread !== null && spread !== undefined && !isNaN(spread)) {
    ensembleSpreadGauge.set({ horizon, variable }, spread);
    ensembleSpreadHistogram.observe({ horizon, variable }, spread);
  }
};

export const updateConfidencePercentiles = (
  percentiles: {
    p05: number;
    p25: number;
    p50: number;
    p75: number;
    p95: number;
  },
  horizon: string,
  variable: string
) => {
  Object.entries(percentiles).forEach(([percentile, value]) => {
    if (value !== null && value !== undefined && !isNaN(value)) {
      confidencePercentilesGauge.set({ horizon, variable, percentile }, value);
    }
  });
};

/**
 * Performance Tracking Functions
 */
export const trackPageLoad = (duration: number) => {
  pageLoadDuration.observe(duration);
};

export const trackForecastRender = (
  duration: number,
  horizon: string,
  variableCount: number
) => {
  forecastRenderDuration.observe(
    { horizon, variable_count: variableCount.toString() },
    duration
  );
};

export const trackAPIResponse = (
  endpoint: string,
  statusCode: number,
  duration: number
) => {
  apiResponseTime.observe(
    { endpoint, status_code: statusCode.toString() },
    duration
  );
};

/**
 * Error Tracking Functions
 */
export const trackUIError = (errorType: string, component: string) => {
  uiErrorCounter.inc({ error_type: errorType, component });
};

export const trackForecastError = (horizon: string, errorType: string) => {
  forecastErrorCounter.inc({ horizon, error_type: errorType });
};

/**
 * Enhanced forecast data processing for metrics
 */
export const processForecastForMetrics = (forecasts: Record<string, any>) => {
  Object.entries(forecasts).forEach(([horizon, forecast]) => {
    if (forecast && forecast.variables) {
      Object.entries(forecast.variables).forEach(
        ([variable, data]: [string, any]) => {
          if (data && data.available) {
            // Update confidence metrics
            if (data.confidence !== null) {
              updateForecastConfidence(data.confidence, horizon, variable);
            }

            // Calculate and track ensemble spread
            if (data.p05 !== null && data.p95 !== null) {
              const spread = Math.abs(data.p95 - data.p05);
              updateEnsembleSpread(spread, horizon, variable);
            }

            // Track CAPE distribution specifically
            if (variable === 'cape' && data.value !== null) {
              trackCapeDistribution(data.value, horizon);
            }

            // Track analog similarity if available
            if (
              forecast.analogs_summary &&
              forecast.analogs_summary.similarity_score !== null
            ) {
              trackAnalogSimilarity(
                forecast.analogs_summary.similarity_score,
                horizon,
                variable
              );
            }

            // Update confidence percentiles (synthetic calculation from available data)
            if (data.p05 !== null && data.p95 !== null && data.value !== null) {
              const range = data.p95 - data.p05;
              const centerValue = data.value;

              updateConfidencePercentiles(
                {
                  p05: data.p05,
                  p25: centerValue - range * 0.25,
                  p50: centerValue,
                  p75: centerValue + range * 0.25,
                  p95: data.p95
                },
                horizon,
                variable
              );
            }
          }
        }
      );
    }
  });
};

/**
 * Get all metrics in Prometheus format
 */
export const getMetrics = async (): Promise<string> => {
  return register.metrics();
};

/**
 * Reset all metrics (useful for testing)
 */
export const resetMetrics = () => {
  register.resetMetrics();
};
