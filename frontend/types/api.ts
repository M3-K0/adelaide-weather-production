/**
 * TypeScript types for Adelaide Weather Forecasting API
 * Generated from enhanced OpenAPI schema (T-001)
 * 
 * This file contains strictly typed definitions for all API responses
 * including the new RiskAssessment, AnalogsSummary, and enhanced ForecastResponse
 */

// ============================================================================
// Core Domain Types
// ============================================================================

/** Valid weather variables that can be forecasted */
export type WeatherVariable = 
  | 't2m'    // 2m temperature
  | 'u10'    // 10m U wind component
  | 'v10'    // 10m V wind component  
  | 'msl'    // Mean sea level pressure
  | 'r850'   // 850hPa relative humidity
  | 'tp6h'   // 6-hourly total precipitation
  | 'cape'   // Convective available potential energy
  | 't850'   // 850hPa temperature
  | 'z500';  // 500hPa geopotential height

/** Valid forecast horizons */
export type ForecastHorizon = '6h' | '12h' | '24h' | '48h';

/** Risk level categories for weather hazards */
export type RiskLevel = 'minimal' | 'low' | 'moderate' | 'high' | 'extreme';

// ============================================================================
// Variable Results
// ============================================================================

/** Individual variable forecast result with uncertainty quantification */
export interface VariableResult {
  /** Point estimate value */
  value: number | null;
  /** 5th percentile (lower bound) */
  p05: number | null;
  /** 95th percentile (upper bound) */
  p95: number | null;
  /** Confidence interval width */
  confidence: number | null;
  /** Whether forecast is available for this variable */
  available: boolean;
  /** Number of analog patterns used in forecast */
  analog_count: number | null;
}

/** Wind forecast result with speed/direction components */
export interface WindResult {
  /** Wind speed in m/s */
  speed: number | null;
  /** Wind direction in degrees (0-360) */
  direction: number | null;
  /** Wind gust speed in m/s */
  gust: number | null;
  /** Whether wind forecast is available */
  available: boolean;
}

// ============================================================================
// Risk Assessment (New in T-001)
// ============================================================================

/** Weather risk assessment for various hazards */
export interface RiskAssessment {
  /** Thunderstorm development risk level */
  thunderstorm: RiskLevel;
  /** Heat stress risk for humans/agriculture */
  heat_stress: RiskLevel;
  /** Wind damage potential to structures */
  wind_damage: RiskLevel;
  /** Heavy precipitation/flooding risk */
  precipitation: RiskLevel;
}

// ============================================================================
// Analogs Summary (New in T-001)
// ============================================================================

/** Summary of historical analog pattern matching */
export interface AnalogsSummary {
  /** Date of most similar historical weather pattern */
  most_similar_date: string;
  /** Similarity score between 0 and 1 */
  similarity_score: number;
  /** Number of analog patterns used in ensemble */
  analog_count: number;
  /** Description of what happened in similar historical cases */
  outcome_description: string;
  /** Explanation of confidence level and reasoning */
  confidence_explanation: string;
}

// ============================================================================
// Detailed Analog Data (T-009)
// ============================================================================

/** Individual historical analog pattern with detailed timeline */
export interface AnalogPattern {
  /** Date of the historical pattern */
  date: string;
  /** Similarity score to current conditions (0-1) */
  similarity_score: number;
  /** Initial weather conditions at pattern start */
  initial_conditions: Record<WeatherVariable, number | null>;
  /** Timeline of what happened after this pattern (6h, 12h, 24h, 48h) */
  timeline: AnalogTimelinePoint[];
  /** What actually happened description */
  outcome_narrative: string;
  /** Geographic location of this analog */
  location?: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  /** Season/month when this pattern occurred */
  season_info: {
    month: number;
    season: 'summer' | 'autumn' | 'winter' | 'spring';
  };
}

/** Single point in an analog timeline */
export interface AnalogTimelinePoint {
  /** Hours offset from pattern start */
  hours_offset: number;
  /** Weather variable values at this time */
  values: Record<WeatherVariable, number | null>;
  /** Significant weather events at this time */
  events?: string[];
  /** Temperature trend indicator */
  temperature_trend?: 'rising' | 'falling' | 'stable';
  /** Pressure trend indicator */
  pressure_trend?: 'rising' | 'falling' | 'stable';
}

/** Complete analog explorer data response */
export interface AnalogExplorerData {
  /** Current forecast horizon being analyzed */
  forecast_horizon: ForecastHorizon;
  /** Top 5 most similar historical patterns */
  top_analogs: AnalogPattern[];
  /** Statistical summary across all analogs */
  ensemble_stats: {
    /** Mean outcome for each variable */
    mean_outcomes: Record<WeatherVariable, number | null>;
    /** Standard deviation of outcomes */
    outcome_uncertainty: Record<WeatherVariable, number | null>;
    /** Most common weather events */
    common_events: string[];
  };
  /** Data generation timestamp */
  generated_at: string;
  /** Data source used for analog search - 'faiss' for FAISS vector search, 'fallback' for mock/degraded mode */
  data_source: 'faiss' | 'fallback';
  /** Detailed metadata about the search operation including performance metrics and quality indicators */
  search_metadata: {
    /** Search method used */
    search_method: string;
    /** Whether FAISS search was successful */
    faiss_search_successful: boolean;
    /** Indices used for search */
    indices_used?: string;
    /** Total number of candidates searched */
    total_candidates?: number;
    /** Search time in milliseconds */
    search_time_ms?: number;
    /** Number of neighbors found */
    k_neighbors_found?: number;
    /** Distance metric used */
    distance_metric?: string;
    /** Fallback reason if search failed */
    fallback_reason?: string;
    /** Any additional metadata */
    [key: string]: string | number | boolean | undefined;
  };
}

// ============================================================================
// System Information
// ============================================================================

/** System version information for reproducibility */
export interface VersionInfo {
  /** Model version identifier */
  model: string;
  /** FAISS index version */
  index: string;
  /** Training datasets version */
  datasets: string;
  /** API schema version */
  api_schema: string;
}

/** System hash information for integrity verification */
export interface HashInfo {
  /** Model file hash */
  model: string;
  /** Index file hash */
  index: string;
  /** Dataset hash */
  datasets: string;
}

// ============================================================================
// Enhanced Forecast Response (T-001)
// ============================================================================

/** Complete forecast API response with narrative and risk assessment */
export interface ForecastResponse {
  /** Forecast time horizon */
  horizon: ForecastHorizon;
  /** Timestamp when forecast was generated */
  generated_at: string; // ISO 8601 datetime
  /** Dictionary of variable forecasts keyed by variable name */
  variables: Record<WeatherVariable, VariableResult>;
  /** Combined 10m wind forecast (derived from u10/v10) */
  wind10m: WindResult | null;
  /** Human-readable forecast narrative */
  narrative: string;
  /** Risk assessment for weather hazards */
  risk_assessment: RiskAssessment;
  /** Historical analog pattern analysis */
  analogs_summary: AnalogsSummary;
  /** Explanation of overall forecast confidence */
  confidence_explanation: string;
  /** System version information */
  versions: VersionInfo;
  /** System hash information */
  hashes: HashInfo;
  /** Response generation latency in milliseconds */
  latency_ms: number;
}

// ============================================================================
// Health Check Types
// ============================================================================

/** Individual health check result */
export interface HealthCheck {
  /** Name of the health check */
  name: string;
  /** Status: 'pass' or 'fail' */
  status: 'pass' | 'fail';
  /** Detailed message about the check */
  message: string;
}

/** Model health information */
export interface ModelInfo {
  /** Model version */
  version: string;
  /** Model file hash */
  hash: string;
  /** Parameter matching ratio (0-1) */
  matched_ratio: number;
}

/** FAISS index health information */
export interface IndexInfo {
  /** Total number of vectors in index */
  ntotal: number;
  /** Vector dimension */
  dim: number;
  /** Distance metric used */
  metric: string;
  /** Index file hash */
  hash: string;
  /** Dataset hash this index was built from */
  dataset_hash: string;
}

/** Dataset health information */
export interface DatasetInfo {
  /** Forecast horizon this dataset covers */
  horizon: ForecastHorizon;
  /** Percentage of valid data by variable */
  valid_pct_by_var: Record<WeatherVariable, number>;
  /** Dataset file hash */
  hash: string;
  /** Dataset schema version */
  schema_version: string;
}

/** Complete system health response */
export interface HealthResponse {
  /** Overall system readiness */
  ready: boolean;
  /** List of individual health checks */
  checks: HealthCheck[];
  /** Model health information */
  model: ModelInfo;
  /** Index health information */
  index: IndexInfo;
  /** Dataset health information for each horizon */
  datasets: DatasetInfo[];
  /** Dependency versions */
  deps: Record<string, string>;
  /** Preprocessing pipeline version */
  preprocessing_version: string;
  /** System uptime in seconds */
  uptime_seconds: number;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/** Forecast API request parameters */
export interface ForecastParams {
  /** Forecast horizon (default: '24h') */
  horizon?: ForecastHorizon;
  /** Comma-separated list of variables (default: 't2m,u10,v10,msl') */
  vars?: string;
}

/** API Error response */
export interface ApiError {
  /** Error message */
  error: string;
  /** Optional error details */
  details?: string;
}

/** Generic API response wrapper */
export type ApiResponse<T> = T | ApiError;

// ============================================================================
// Type Guards
// ============================================================================

/** Type guard to check if response is an error */
export function isApiError(response: any): response is ApiError {
  return typeof response === 'object' && response !== null && 'error' in response;
}

/** Type guard to check if response is a forecast */
export function isForecastResponse(response: any): response is ForecastResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'horizon' in response &&
    'variables' in response &&
    'narrative' in response &&
    'risk_assessment' in response &&
    'analogs_summary' in response
  );
}

/** Type guard to check if response is a health check */
export function isHealthResponse(response: any): response is HealthResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'ready' in response &&
    'checks' in response &&
    Array.isArray(response.checks)
  );
}

/** Type guard to check if response is analog explorer data */
export function isAnalogExplorerData(response: any): response is AnalogExplorerData {
  return (
    typeof response === 'object' &&
    response !== null &&
    'forecast_horizon' in response &&
    'top_analogs' in response &&
    'ensemble_stats' in response &&
    'generated_at' in response &&
    'data_source' in response &&
    'search_metadata' in response &&
    Array.isArray(response.top_analogs) &&
    typeof response.data_source === 'string' &&
    (response.data_source === 'faiss' || response.data_source === 'fallback') &&
    typeof response.search_metadata === 'object'
  );
}

// ============================================================================
// Utility Types
// ============================================================================

/** Extract the keys of variables that are available in a forecast */
export type AvailableVariables<T extends ForecastResponse> = {
  [K in WeatherVariable]: T['variables'][K]['available'] extends true ? K : never;
}[WeatherVariable];

/** Get the variable result type for a specific variable */
export type VariableResultFor<T extends WeatherVariable> = VariableResult;

/** Risk assessment with only specified risk types */
export type RiskAssessmentFor<T extends keyof RiskAssessment> = Pick<RiskAssessment, T>;

// ============================================================================
// Constants
// ============================================================================

/** All valid weather variables */
export const WEATHER_VARIABLES: readonly WeatherVariable[] = [
  't2m', 'u10', 'v10', 'msl', 'r850', 'tp6h', 'cape', 't850', 'z500'
] as const;

/** All valid forecast horizons */
export const FORECAST_HORIZONS: readonly ForecastHorizon[] = [
  '6h', '12h', '24h', '48h'
] as const;

/** All valid risk levels */
export const RISK_LEVELS: readonly RiskLevel[] = [
  'minimal', 'low', 'moderate', 'high', 'extreme'
] as const;

/** Default variables for forecast requests */
export const DEFAULT_VARIABLES: readonly WeatherVariable[] = [
  't2m', 'u10', 'v10', 'msl'
] as const;

/** Variable display names */
export const VARIABLE_NAMES: Record<WeatherVariable, string> = {
  't2m': '2m Temperature',
  'u10': '10m U Wind',
  'v10': '10m V Wind',
  'msl': 'Sea Level Pressure',
  'r850': '850hPa Humidity',
  'tp6h': '6h Precipitation',
  'cape': 'CAPE',
  't850': '850hPa Temperature',
  'z500': '500hPa Height'
} as const;

/** Variable units */
export const VARIABLE_UNITS: Record<WeatherVariable, string> = {
  't2m': '°C',
  'u10': 'm/s',
  'v10': 'm/s',
  'msl': 'hPa',
  'r850': '%',
  'tp6h': 'mm',
  'cape': 'J/kg',
  't850': '°C',
  'z500': 'm'
} as const;