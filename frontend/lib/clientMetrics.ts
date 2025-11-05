/**
 * Client-Side Metrics Collection System
 * 
 * Simplified metrics system that works in the browser without Node.js dependencies.
 * Collects UI interaction metrics and forwards them to the server-side metrics endpoint.
 */

interface MetricData {
  name: string;
  type: 'counter' | 'histogram' | 'gauge';
  value: number;
  labels?: Record<string, string>;
  timestamp?: number;
}

class ClientMetrics {
  private metrics: MetricData[] = [];
  private flushInterval: NodeJS.Timeout | null = null;

  constructor() {
    // Flush metrics to server every 30 seconds
    this.flushInterval = setInterval(() => {
      this.flush();
    }, 30000);
  }

  private async flush() {
    if (this.metrics.length === 0) return;

    const metricsToSend = [...this.metrics];
    this.metrics = [];

    try {
      await fetch('/api/client-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ metrics: metricsToSend }),
      });
    } catch (error) {
      console.error('Failed to send metrics:', error);
      // Re-add metrics for retry
      this.metrics.unshift(...metricsToSend);
    }
  }

  increment(name: string, labels?: Record<string, string>, value: number = 1) {
    this.metrics.push({
      name,
      type: 'counter',
      value,
      labels,
      timestamp: Date.now(),
    });
  }

  observe(name: string, value: number, labels?: Record<string, string>) {
    this.metrics.push({
      name,
      type: 'histogram',
      value,
      labels,
      timestamp: Date.now(),
    });
  }

  set(name: string, value: number, labels?: Record<string, string>) {
    this.metrics.push({
      name,
      type: 'gauge',
      value,
      labels,
      timestamp: Date.now(),
    });
  }

  destroy() {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
      this.flushInterval = null;
    }
    this.flush(); // Final flush
  }
}

// Create singleton instance
const clientMetrics = new ClientMetrics();

// Export tracking functions that match the server-side API
export const trackUIInteraction = (
  interactionType: string,
  component: string,
  horizon?: string
) => {
  clientMetrics.increment('ui_interactions_total', {
    interaction_type: interactionType,
    component: component,
    horizon: horizon || 'all'
  });
};

export const trackVariableToggle = (
  variable: string,
  action: 'show' | 'hide'
) => {
  clientMetrics.increment('variable_toggle_total', { variable, action });
};

export const trackHorizonChange = (fromHorizon: string, toHorizon: string) => {
  clientMetrics.increment('horizon_change_total', {
    from_horizon: fromHorizon,
    to_horizon: toHorizon
  });
};

export const trackCapeModalOpen = (horizon: string) => {
  clientMetrics.increment('cape_modal_opens_total', { horizon });
};

export const trackPageLoad = (duration: number) => {
  clientMetrics.observe('page_load_duration_seconds', duration);
};

export const trackForecastRender = (
  duration: number,
  horizon: string,
  variableCount: number
) => {
  clientMetrics.observe('forecast_render_duration_seconds', duration, {
    horizon,
    variable_count: variableCount.toString()
  });
};

export const trackAPIResponse = (
  endpoint: string,
  statusCode: number,
  duration: number
) => {
  clientMetrics.observe('frontend_api_response_time_seconds', duration, {
    endpoint,
    status_code: statusCode.toString()
  });
};

export const trackUIError = (errorType: string, component: string) => {
  clientMetrics.increment('ui_errors_total', { error_type: errorType, component });
};

export const trackForecastError = (horizon: string, errorType: string) => {
  clientMetrics.increment('forecast_errors_total', { horizon, error_type: errorType });
};

export const processForecastForMetrics = (forecasts: Record<string, any>) => {
  // Process forecast data and extract metrics
  Object.entries(forecasts).forEach(([horizon, forecast]) => {
    if (forecast && forecast.variables) {
      Object.entries(forecast.variables).forEach(
        ([variable, data]: [string, any]) => {
          if (data && data.available) {
            // Track forecast confidence
            if (data.confidence !== null) {
              clientMetrics.set('forecast_confidence_current', data.confidence, {
                horizon,
                variable
              });
            }

            // Track ensemble spread
            if (data.p05 !== null && data.p95 !== null) {
              const spread = Math.abs(data.p95 - data.p05);
              clientMetrics.set('ensemble_spread_current', spread, {
                horizon,
                variable
              });
            }

            // Track CAPE distribution specifically
            if (variable === 'cape' && data.value !== null) {
              clientMetrics.observe('cape_distribution_values', data.value, {
                horizon
              });
            }
          }
        }
      );
    }
  });
};

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    clientMetrics.destroy();
  });
}

export default clientMetrics;