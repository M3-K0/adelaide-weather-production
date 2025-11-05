/**
 * Type definitions index for Adelaide Weather Forecasting API
 *
 * This file exports all TypeScript types for the enhanced API schema
 * enabling strict type checking throughout the frontend application.
 */

// Re-export all API types
export * from './api';

// Re-export specific commonly used types for convenience
export type {
  ForecastResponse,
  RiskAssessment,
  AnalogsSummary,
  VariableResult,
  WindResult,
  WeatherVariable,
  ForecastHorizon,
  RiskLevel,
  ApiError,
  ApiResponse
} from './api';
