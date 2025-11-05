/**
 * Mock Data Specifications for Development
 * Adelaide Weather Forecasting System
 *
 * Comprehensive mock data generators and fixtures for component development,
 * testing, and API simulation during parallel development phases.
 *
 * @version 1.0.0
 * @author Design Systems Architect
 */

import type {
  ForecastResponse,
  VariableResult,
  WindResult,
  ForecastCardProps,
  CAPEBadgeProps,
  StatusBarProps,
  ChartDataPoint,
  SystemStatus,
  MockOptions
} from './components';

/**
 * Core Mock Data Generators
 */
export class MockDataGenerator {
  private static instance: MockDataGenerator;

  static getInstance(): MockDataGenerator {
    if (!MockDataGenerator.instance) {
      MockDataGenerator.instance = new MockDataGenerator();
    }
    return MockDataGenerator.instance;
  }

  /**
   * Generate realistic forecast response data
   */
  generateForecast(
    horizon: string,
    options: MockOptions = {}
  ): ForecastResponse {
    const {
      tempRange = [-5, 45],
      confidenceRange = [30, 95],
      includeUnavailable = false,
      latencyRange = [20, 150]
    } = options;

    const isAvailable = includeUnavailable ? Math.random() > 0.1 : true;
    const baseTemp = this.randomInRange(tempRange[0], tempRange[1]);
    const confidence = this.randomInRange(
      confidenceRange[0],
      confidenceRange[1]
    );
    const tempVariation = this.randomInRange(0.5, 3.5);

    return {
      horizon,
      generated_at: new Date().toISOString(),
      variables: {
        t2m: this.generateVariableResult(
          baseTemp,
          tempVariation,
          confidence,
          isAvailable
        ),
        u10: this.generateVariableResult(
          this.randomInRange(-15, 15),
          2,
          confidence,
          isAvailable
        ),
        v10: this.generateVariableResult(
          this.randomInRange(-15, 15),
          2,
          confidence,
          isAvailable
        ),
        msl: this.generateVariableResult(
          this.randomInRange(995, 1025),
          3,
          confidence,
          isAvailable
        ),
        cape: this.generateVariableResult(
          this.randomInRange(0, 3500),
          500,
          confidence * 0.8,
          isAvailable
        ),
        tp6h: this.generateVariableResult(
          this.randomInRange(0, 25),
          5,
          confidence * 0.7,
          isAvailable
        )
      },
      wind10m: this.generateWindResult(confidence, isAvailable),
      versions: {
        model: this.generateHash(7),
        index: this.generateHash(7),
        datasets: `v${this.randomInRange(1, 5)}.${this.randomInRange(0, 9)}.${this.randomInRange(0, 9)}`,
        schema: '2.1.0'
      },
      hashes: {
        model: this.generateHash(40),
        index: this.generateHash(40),
        datasets: this.generateHash(40)
      },
      latency_ms: Math.round(
        this.randomInRange(latencyRange[0], latencyRange[1])
      )
    };
  }

  /**
   * Generate ForecastCard component props
   */
  generateForecastCardProps(
    horizon: string = '+6h',
    overrides: Partial<ForecastCardProps> = {}
  ): ForecastCardProps {
    const forecast = this.generateForecast(horizon.replace('+', ''));
    const t2m = forecast.variables.t2m;
    const wind = forecast.wind10m;

    const baseProps: ForecastCardProps = {
      horizon,
      temp: t2m.value || 20,
      confidence: t2m.p95 && t2m.p05 ? Math.abs(t2m.p95 - t2m.p05) / 2 : 2.5,
      confidencePct: Math.round(t2m.confidence || 75),
      p05: t2m.p05 || 17.5,
      p50: t2m.value || 20,
      p95: t2m.p95 || 22.5,
      windDir: wind?.direction || 180,
      windSpeed: wind?.speed || 5,
      windGust: wind?.gust,
      latency: `${forecast.latency_ms}ms`,
      sparklineData: this.generateSparklineData(t2m.value || 20, 7),
      analogCount: t2m.analog_count || 45,
      isAvailable: t2m.available
    };

    return { ...baseProps, ...overrides };
  }

  /**
   * Generate CAPE badge props
   */
  generateCAPEBadgeProps(
    overrides: Partial<CAPEBadgeProps> = {}
  ): CAPEBadgeProps {
    const cape = this.randomInRange(0, 3500);
    const baseProps: CAPEBadgeProps = {
      value: cape,
      available: Math.random() > 0.1,
      confidence: this.randomInRange(60, 90),
      size: 'md',
      format: 'compact'
    };

    return { ...baseProps, ...overrides };
  }

  /**
   * Generate StatusBar component props
   */
  generateStatusBarProps(
    overrides: Partial<StatusBarProps> = {}
  ): StatusBarProps {
    const statuses: Array<'healthy' | 'degraded' | 'down' | 'maintenance'> = [
      'healthy',
      'degraded',
      'down',
      'maintenance'
    ];
    const weights = [0.7, 0.2, 0.05, 0.05]; // Probability weights

    const baseProps: StatusBarProps = {
      status: this.weightedRandom(statuses, weights),
      lastUpdated: new Date(
        Date.now() - this.randomInRange(0, 300000)
      ).toISOString(),
      metrics: {
        avgLatency: this.randomInRange(25, 120),
        successRate: this.randomInRange(85, 99.9),
        activeForecast: this.randomInRange(150, 500),
        dataAge: this.randomInRange(1, 15)
      },
      versions: {
        model: this.generateHash(7),
        index: this.generateHash(7),
        datasets: `v3.${this.randomInRange(0, 5)}.${this.randomInRange(0, 9)}`
      }
    };

    return { ...baseProps, ...overrides };
  }

  /**
   * Generate chart data points
   */
  generateChartData(
    points: number = 24,
    variables: string[] = ['t2m', 'u10', 'v10']
  ): ChartDataPoint[] {
    const startTime = new Date();
    const data: ChartDataPoint[] = [];

    for (let i = 0; i < points; i++) {
      const timestamp = new Date(startTime.getTime() + i * 3600000); // Hour intervals
      const values: Record<string, number | null> = {};
      const confidence: Record<string, { min: number; max: number }> = {};

      variables.forEach(variable => {
        const baseValue = this.getBaseValueForVariable(variable);
        const variation = this.getVariationForVariable(variable);
        const value =
          baseValue +
          Math.sin(i * 0.2) * variation +
          this.randomInRange(-variation / 2, variation / 2);

        values[variable] = Math.round(value * 100) / 100;
        confidence[variable] = {
          min: value - variation,
          max: value + variation
        };
      });

      data.push({
        timestamp: timestamp.toISOString(),
        values,
        confidence
      });
    }

    return data;
  }

  /**
   * Generate system status data
   */
  generateSystemStatus(): SystemStatus {
    const overallHealthy = Math.random() > 0.2;

    return {
      status: overallHealthy
        ? 'healthy'
        : Math.random() > 0.5
          ? 'degraded'
          : 'down',
      timestamp: new Date().toISOString(),
      services: {
        api: {
          status: this.randomServiceStatus(),
          latency: this.randomInRange(20, 100),
          lastCheck: new Date(
            Date.now() - this.randomInRange(0, 60000)
          ).toISOString()
        },
        database: {
          status: this.randomServiceStatus(),
          latency: this.randomInRange(5, 50),
          lastCheck: new Date(
            Date.now() - this.randomInRange(0, 60000)
          ).toISOString()
        },
        cache: {
          status: this.randomServiceStatus(),
          latency: this.randomInRange(1, 10),
          lastCheck: new Date(
            Date.now() - this.randomInRange(0, 60000)
          ).toISOString()
        },
        model: {
          status: this.randomServiceStatus(),
          lastCheck: new Date(
            Date.now() - this.randomInRange(0, 300000)
          ).toISOString(),
          message: 'Model inference pipeline operational'
        }
      },
      metrics: {
        responseTime: this.randomInRange(25, 120),
        uptime: this.randomInRange(95, 99.99),
        errorRate: this.randomInRange(0.01, 2.5)
      }
    };
  }

  // Private helper methods

  private generateVariableResult(
    baseValue: number,
    variation: number,
    confidence: number,
    available: boolean
  ): VariableResult {
    if (!available) {
      return {
        value: null,
        p05: null,
        p95: null,
        confidence: null,
        available: false,
        analog_count: null
      };
    }

    const value = Math.round(baseValue * 100) / 100;
    const p05 = Math.round((baseValue - variation) * 100) / 100;
    const p95 = Math.round((baseValue + variation) * 100) / 100;

    return {
      value,
      p05,
      p95,
      confidence: Math.round(confidence),
      available: true,
      analog_count: this.randomInRange(15, 75)
    };
  }

  private generateWindResult(
    confidence: number,
    available: boolean
  ): WindResult {
    if (!available) {
      return {
        speed: null,
        direction: null,
        gust: null,
        available: false
      };
    }

    const speed = this.randomInRange(0, 20);
    const direction = this.randomInRange(0, 360);
    const gust = speed > 5 ? speed + this.randomInRange(1, 8) : undefined;

    return {
      speed: Math.round(speed * 10) / 10,
      direction: Math.round(direction),
      gust: gust ? Math.round(gust * 10) / 10 : null,
      available: true
    };
  }

  private generateSparklineData(baseValue: number, points: number): number[] {
    const data: number[] = [];
    const variation = 2;

    for (let i = 0; i < points; i++) {
      const trend = Math.sin(i * 0.5) * variation;
      const noise = this.randomInRange(-0.5, 0.5);
      data.push(Math.round((baseValue + trend + noise) * 10) / 10);
    }

    return data;
  }

  private generateHash(length: number): string {
    const chars = '0123456789abcdef';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  private randomInRange(min: number, max: number): number {
    return Math.random() * (max - min) + min;
  }

  private weightedRandom<T>(items: T[], weights: number[]): T {
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    let random = Math.random() * total;

    for (let i = 0; i < items.length; i++) {
      random -= weights[i];
      if (random <= 0) {
        return items[i];
      }
    }

    return items[items.length - 1];
  }

  private randomServiceStatus(): 'healthy' | 'degraded' | 'down' {
    const rand = Math.random();
    if (rand < 0.8) return 'healthy';
    if (rand < 0.95) return 'degraded';
    return 'down';
  }

  private getBaseValueForVariable(variable: string): number {
    const baselines: Record<string, number> = {
      t2m: 20, // 20°C
      u10: 5, // 5 m/s eastward wind
      v10: 3, // 3 m/s northward wind
      msl: 1013, // 1013 hPa sea level pressure
      cape: 800, // 800 J/kg CAPE
      tp6h: 2, // 2mm precipitation
      r850: 65, // 65% relative humidity
      t850: 15, // 15°C temperature at 850hPa
      z500: 5500 // 5500m geopotential height at 500hPa
    };
    return baselines[variable] || 0;
  }

  private getVariationForVariable(variable: string): number {
    const variations: Record<string, number> = {
      t2m: 3, // ±3°C
      u10: 8, // ±8 m/s
      v10: 8, // ±8 m/s
      msl: 15, // ±15 hPa
      cape: 600, // ±600 J/kg
      tp6h: 5, // ±5mm
      r850: 20, // ±20%
      t850: 4, // ±4°C
      z500: 100 // ±100m
    };
    return variations[variable] || 1;
  }
}

/**
 * Predefined Mock Data Sets
 */
export const MockDataSets = {
  // Forecast scenarios
  PERFECT_CONDITIONS: {
    confidence: [85, 95],
    tempRange: [18, 25] as [number, number],
    windRange: [0, 8],
    available: true
  },

  STORMY_CONDITIONS: {
    confidence: [45, 70],
    tempRange: [8, 18] as [number, number],
    windRange: [15, 35],
    available: true,
    highCAPE: true
  },

  HEATWAVE_CONDITIONS: {
    confidence: [60, 85],
    tempRange: [35, 45] as [number, number],
    windRange: [0, 12],
    available: true
  },

  DEGRADED_DATA: {
    confidence: [25, 50],
    tempRange: [10, 30] as [number, number],
    includeUnavailable: true,
    available: false
  },

  // Component states
  FORECAST_CARD_STATES: {
    available: {
      horizon: '+6h',
      temp: 22.5,
      confidencePct: 85,
      isAvailable: true
    },
    unavailable: {
      horizon: '+48h',
      temp: 0,
      confidencePct: 0,
      isAvailable: false
    },
    lowConfidence: {
      horizon: '+24h',
      temp: 18.5,
      confidencePct: 35,
      isAvailable: true
    },
    extreme: {
      horizon: '+12h',
      temp: -12.5,
      confidencePct: 72,
      isAvailable: true
    }
  },

  CAPE_BADGE_STATES: {
    low: { value: 250, available: true },
    moderate: { value: 1200, available: true },
    high: { value: 2800, available: true },
    extreme: { value: 4500, available: true },
    unavailable: { value: null, available: false }
  },

  STATUS_BAR_STATES: {
    healthy: {
      status: 'healthy' as const,
      metrics: {
        avgLatency: 45,
        successRate: 99.2,
        activeForecast: 324,
        dataAge: 3
      }
    },
    degraded: {
      status: 'degraded' as const,
      metrics: {
        avgLatency: 125,
        successRate: 92.1,
        activeForecast: 189,
        dataAge: 12
      },
      message: 'Some data sources experiencing delays'
    },
    down: {
      status: 'down' as const,
      metrics: {
        avgLatency: 0,
        successRate: 0,
        activeForecast: 0,
        dataAge: 45
      },
      message: 'Weather API unavailable'
    }
  }
};

/**
 * Development Fixtures
 * Ready-to-use data for Storybook, testing, and development
 */
export const DevelopmentFixtures = {
  // Complete forecast responses for all horizons
  ALL_HORIZONS: ['6h', '12h', '24h', '48h'].map(horizon =>
    MockDataGenerator.getInstance().generateForecast(horizon)
  ),

  // Error scenarios
  ERROR_SCENARIOS: {
    networkError: new Error('Network request failed'),
    timeoutError: new Error('Request timeout'),
    validationError: new Error('Invalid parameters'),
    serverError: new Error('Internal server error')
  },

  // Loading states with realistic delays
  LOADING_DELAYS: {
    fast: 200,
    normal: 800,
    slow: 2000,
    timeout: 10000
  },

  // Accessibility test data
  ACCESSIBILITY_SCENARIOS: {
    highContrast: true,
    reducedMotion: true,
    screenReader: true,
    keyboardOnly: true
  },

  // Performance test data
  PERFORMANCE_SCENARIOS: {
    largeForecastSet: Array.from({ length: 100 }, (_, i) =>
      MockDataGenerator.getInstance().generateForecast(`${i}h`)
    ),
    highFrequencyUpdates: Array.from({ length: 50 }, (_, i) => ({
      timestamp: new Date(Date.now() + i * 1000).toISOString(),
      data: MockDataGenerator.getInstance().generateForecast('6h')
    }))
  }
};

/**
 * API Response Simulators
 */
export const APISimulators = {
  /**
   * Simulate realistic API response timing and errors
   */
  simulateAPICall<T>(
    data: T,
    options: {
      delay?: number;
      errorRate?: number;
      errorTypes?: string[];
    } = {}
  ): Promise<T> {
    const {
      delay = 500,
      errorRate = 0.05,
      errorTypes = ['network', 'timeout', 'server']
    } = options;

    return new Promise((resolve, reject) => {
      setTimeout(
        () => {
          if (Math.random() < errorRate) {
            const errorType =
              errorTypes[Math.floor(Math.random() * errorTypes.length)];
            reject(
              DevelopmentFixtures.ERROR_SCENARIOS[
                errorType as keyof typeof DevelopmentFixtures.ERROR_SCENARIOS
              ]
            );
          } else {
            resolve(data);
          }
        },
        delay + Math.random() * 200
      ); // Add some jitter
    });
  },

  /**
   * Simulate real-time data updates
   */
  createRealtimeStream<T>(
    generator: () => T,
    interval: number = 5000
  ): {
    subscribe: (callback: (data: T) => void) => void;
    unsubscribe: () => void;
  } {
    let intervalId: NodeJS.Timeout | null = null;
    let callback: ((data: T) => void) | null = null;

    return {
      subscribe: (cb: (data: T) => void) => {
        callback = cb;
        intervalId = setInterval(() => {
          if (callback) {
            callback(generator());
          }
        }, interval);
      },
      unsubscribe: () => {
        if (intervalId) {
          clearInterval(intervalId);
          intervalId = null;
        }
        callback = null;
      }
    };
  }
};

// Export singleton instance for convenience
export const mockData = MockDataGenerator.getInstance();
