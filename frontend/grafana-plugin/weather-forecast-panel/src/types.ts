import { DataFrameView, Field, FieldType } from '@grafana/data';

export interface WeatherPanelOptions {
  showObservations: boolean;
  showForecast: boolean;
  showAnalogPatterns: boolean;
  showUncertaintyBands: boolean;
  animationSpeed: number;
  maxAnalogCount: number;
  confidenceThreshold: number;
  defaultHorizon: string;
  enableHistoricalEvents: boolean;
  splitViewRatio: number;
}

export interface ForecastHorizon {
  hours: number;
  label: string;
  active: boolean;
}

export interface WeatherVariable {
  name: string;
  label: string;
  unit: string;
  color: string;
  visible: boolean;
  observationField?: string;
  forecastField?: string;
}

export interface AnalogPattern {
  id: string;
  similarity: number;
  date: Date;
  pattern: number[];
  confidence: number;
  metadata: {
    synopticSituation: string;
    weatherOutcome: string;
    similarity_score: number;
  };
}

export interface UncertaintyBand {
  time: Date;
  variable: string;
  lower: number;
  upper: number;
  confidence: number;
}

export interface HistoricalEvent {
  id: string;
  date: Date;
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'extreme';
  similarity: number;
  analogPatterns: AnalogPattern[];
}

export interface WeatherDataPoint {
  time: Date;
  variable: string;
  value: number;
  type: 'observation' | 'forecast';
  horizon?: number;
  confidence?: number;
  uncertainty?: {
    lower: number;
    upper: number;
  };
}

export interface SynopticOverlay {
  time: Date;
  patterns: {
    pressure: number[][];
    temperature: number[][];
    wind: {
      u: number[][];
      v: number[][];
    };
  };
  analogMatches: AnalogPattern[];
}

export interface AnimationState {
  isPlaying: boolean;
  currentHorizon: number;
  speed: number;
  direction: 'forward' | 'backward';
}

export interface DataSource {
  prometheus: {
    url: string;
    queries: {
      observations: string;
      forecasts: string;
      analogs: string;
      uncertainty: string;
    };
  };
  timescaledb: {
    host: string;
    database: string;
    queries: {
      historical_events: string;
      analog_patterns: string;
      verification_data: string;
    };
  };
}

export interface PanelState {
  selectedHorizon: ForecastHorizon;
  visibleVariables: WeatherVariable[];
  analogPatterns: AnalogPattern[];
  uncertaintyBands: UncertaintyBand[];
  historicalEvents: HistoricalEvent[];
  animationState: AnimationState;
  synopticOverlay: SynopticOverlay | null;
  isLoading: boolean;
  error: string | null;
}

export interface DataQueryResult {
  observations: WeatherDataPoint[];
  forecasts: WeatherDataPoint[];
  analogs: AnalogPattern[];
  uncertainty: UncertaintyBand[];
  historical: HistoricalEvent[];
}

export const DEFAULT_HORIZONS: ForecastHorizon[] = [
  { hours: 6, label: '6h', active: true },
  { hours: 12, label: '12h', active: false },
  { hours: 24, label: '24h', active: false },
  { hours: 48, label: '48h', active: false },
];

export const DEFAULT_VARIABLES: WeatherVariable[] = [
  {
    name: 'temperature',
    label: 'Temperature',
    unit: '°C',
    color: '#ff6b6b',
    visible: true,
    observationField: 'temp_obs',
    forecastField: 'temp_forecast'
  },
  {
    name: 'pressure',
    label: 'Sea Level Pressure',
    unit: 'hPa',
    color: '#4ecdc4',
    visible: true,
    observationField: 'msl_obs',
    forecastField: 'msl_forecast'
  },
  {
    name: 'cape',
    label: 'CAPE',
    unit: 'J/kg',
    color: '#45b7d1',
    visible: true,
    observationField: 'cape_obs',
    forecastField: 'cape_forecast'
  },
  {
    name: 'wind_speed',
    label: 'Wind Speed',
    unit: 'm/s',
    color: '#96ceb4',
    visible: false,
    observationField: 'wind_speed_obs',
    forecastField: 'wind_speed_forecast'
  }
];

export const DEFAULT_OPTIONS: WeatherPanelOptions = {
  showObservations: true,
  showForecast: true,
  showAnalogPatterns: true,
  showUncertaintyBands: true,
  animationSpeed: 1000,
  maxAnalogCount: 5,
  confidenceThreshold: 0.7,
  defaultHorizon: '6h',
  enableHistoricalEvents: true,
  splitViewRatio: 0.5,
};