/**
 * TypeScript Type Validation Tests
 * Tests for T-023: Enhanced API Types and Strict Mode
 */

import {
  ForecastResponse,
  RiskAssessment,
  AnalogsSummary,
  VariableResult,
  WindResult,
  WeatherVariable,
  ForecastHorizon,
  RiskLevel,
  ApiError,
  isApiError,
  isForecastResponse,
  isHealthResponse,
  WEATHER_VARIABLES,
  FORECAST_HORIZONS,
  RISK_LEVELS,
  VARIABLE_NAMES,
  VARIABLE_UNITS
} from '@/types';

describe('TypeScript API Types - T-023', () => {
  describe('Core Types', () => {
    test('WeatherVariable type includes all expected variables', () => {
      const expectedVariables: WeatherVariable[] = [
        't2m',
        'u10',
        'v10',
        'msl',
        'r850',
        'tp6h',
        'cape',
        't850',
        'z500'
      ];

      expectedVariables.forEach(variable => {
        expect(WEATHER_VARIABLES).toContain(variable);
      });
    });

    test('ForecastHorizon type includes all expected horizons', () => {
      const expectedHorizons: ForecastHorizon[] = ['6h', '12h', '24h', '48h'];

      expectedHorizons.forEach(horizon => {
        expect(FORECAST_HORIZONS).toContain(horizon);
      });
    });

    test('RiskLevel type includes all expected levels', () => {
      const expectedLevels: RiskLevel[] = [
        'minimal',
        'low',
        'moderate',
        'high',
        'extreme'
      ];

      expectedLevels.forEach(level => {
        expect(RISK_LEVELS).toContain(level);
      });
    });
  });

  describe('Enhanced T-001 Features', () => {
    test('RiskAssessment has all required risk categories', () => {
      const riskAssessment: RiskAssessment = {
        thunderstorm: 'moderate',
        heat_stress: 'low',
        wind_damage: 'minimal',
        precipitation: 'high'
      };

      expect(riskAssessment.thunderstorm).toBe('moderate');
      expect(riskAssessment.heat_stress).toBe('low');
      expect(riskAssessment.wind_damage).toBe('minimal');
      expect(riskAssessment.precipitation).toBe('high');
    });

    test('AnalogsSummary has all required fields', () => {
      const analogsSummary: AnalogsSummary = {
        most_similar_date: '2023-03-15',
        similarity_score: 0.85,
        analog_count: 42,
        outcome_description: 'Similar conditions led to moderate rainfall',
        confidence_explanation: 'High confidence due to strong historical match'
      };

      expect(analogsSummary.similarity_score).toBeGreaterThanOrEqual(0);
      expect(analogsSummary.similarity_score).toBeLessThanOrEqual(1);
      expect(analogsSummary.analog_count).toBeGreaterThan(0);
    });

    test('ForecastResponse includes all enhanced T-001 features', () => {
      const forecast: ForecastResponse = {
        horizon: '24h',
        generated_at: '2023-11-15T10:30:00Z',
        variables: {
          t2m: {
            value: 22.5,
            p05: 19.8,
            p95: 25.2,
            confidence: 0.75,
            available: true,
            analog_count: 45
          }
        },
        wind10m: {
          speed: 5.2,
          direction: 180,
          gust: 7.8,
          available: true
        },
        narrative:
          'Pleasant conditions expected with moderate temperatures and light winds.',
        risk_assessment: {
          thunderstorm: 'low',
          heat_stress: 'minimal',
          wind_damage: 'minimal',
          precipitation: 'moderate'
        },
        analogs_summary: {
          most_similar_date: '2022-11-12',
          similarity_score: 0.82,
          analog_count: 38,
          outcome_description: 'Similar patterns resulted in clear skies',
          confidence_explanation: 'Strong analog match increases confidence'
        },
        confidence_explanation:
          'High confidence based on strong historical patterns',
        versions: {
          model: 'v2.1.0',
          index: 'v1.8.3',
          datasets: 'v3.2.1',
          api_schema: 'v1.0.0'
        },
        hashes: {
          model: 'a7c3f92d',
          index: '2e8b4d1f',
          datasets: '9k2m5n8p'
        },
        latency_ms: 45.2
      };

      // Test enhanced features exist
      expect(forecast.narrative).toBeDefined();
      expect(forecast.risk_assessment).toBeDefined();
      expect(forecast.analogs_summary).toBeDefined();
      expect(forecast.confidence_explanation).toBeDefined();

      // Test risk assessment structure
      expect(forecast.risk_assessment.thunderstorm).toBe('low');
      expect(forecast.risk_assessment.heat_stress).toBe('minimal');

      // Test analogs summary structure
      expect(forecast.analogs_summary.similarity_score).toBe(0.82);
      expect(forecast.analogs_summary.analog_count).toBe(38);
    });
  });

  describe('Type Guards', () => {
    test('isApiError correctly identifies API errors', () => {
      const apiError: ApiError = { error: 'Something went wrong' };
      const notError = { data: 'some data' };

      expect(isApiError(apiError)).toBe(true);
      expect(isApiError(notError)).toBe(false);
      expect(isApiError(null)).toBe(false);
      expect(isApiError(undefined)).toBe(false);
    });

    test('isForecastResponse correctly identifies forecast responses', () => {
      const forecast: Partial<ForecastResponse> = {
        horizon: '24h',
        variables: {},
        narrative: 'Test forecast',
        risk_assessment: {
          thunderstorm: 'low',
          heat_stress: 'minimal',
          wind_damage: 'minimal',
          precipitation: 'low'
        },
        analogs_summary: {
          most_similar_date: '2023-01-01',
          similarity_score: 0.8,
          analog_count: 50,
          outcome_description: 'Test outcome',
          confidence_explanation: 'Test confidence'
        }
      };

      const notForecast = { error: 'Not a forecast' };

      expect(isForecastResponse(forecast)).toBe(true);
      expect(isForecastResponse(notForecast)).toBe(false);
    });
  });

  describe('Constants and Metadata', () => {
    test('VARIABLE_NAMES provides names for all variables', () => {
      WEATHER_VARIABLES.forEach(variable => {
        expect(VARIABLE_NAMES[variable]).toBeDefined();
        expect(typeof VARIABLE_NAMES[variable]).toBe('string');
      });
    });

    test('VARIABLE_UNITS provides units for all variables', () => {
      WEATHER_VARIABLES.forEach(variable => {
        expect(VARIABLE_UNITS[variable]).toBeDefined();
        expect(typeof VARIABLE_UNITS[variable]).toBe('string');
      });
    });

    test('Constants are readonly arrays', () => {
      // These should not compile if types are wrong
      expect(Array.isArray(WEATHER_VARIABLES)).toBe(true);
      expect(Array.isArray(FORECAST_HORIZONS)).toBe(true);
      expect(Array.isArray(RISK_LEVELS)).toBe(true);
    });
  });

  describe('Variable Result Types', () => {
    test('VariableResult supports null values for missing data', () => {
      const unavailableResult: VariableResult = {
        value: null,
        p05: null,
        p95: null,
        confidence: null,
        available: false,
        analog_count: null
      };

      expect(unavailableResult.available).toBe(false);
      expect(unavailableResult.value).toBeNull();
    });

    test('WindResult supports all wind components', () => {
      const windResult: WindResult = {
        speed: 5.2,
        direction: 180,
        gust: 7.8,
        available: true
      };

      expect(windResult.speed).toBe(5.2);
      expect(windResult.direction).toBe(180);
      expect(windResult.gust).toBe(7.8);
      expect(windResult.available).toBe(true);
    });
  });

  describe('Strict Mode Compatibility', () => {
    test('Types work with exactOptionalPropertyTypes', () => {
      // This test ensures our types work with strict TypeScript settings
      const partialVariable: Partial<VariableResult> = {
        value: 22.5,
        available: true
      };

      // Should not have type errors with strict mode
      expect(partialVariable.value).toBe(22.5);
      expect(partialVariable.available).toBe(true);
    });

    test('Risk levels are strictly typed', () => {
      // This should only accept valid risk levels
      const validRisks: RiskLevel[] = [
        'minimal',
        'low',
        'moderate',
        'high',
        'extreme'
      ];

      validRisks.forEach(risk => {
        const assessment: RiskAssessment = {
          thunderstorm: risk,
          heat_stress: risk,
          wind_damage: risk,
          precipitation: risk
        };

        expect(RISK_LEVELS).toContain(assessment.thunderstorm);
      });
    });
  });
});
