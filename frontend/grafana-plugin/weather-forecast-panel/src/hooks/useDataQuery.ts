import { useState, useEffect, useCallback } from 'react';
import { 
  WeatherPanelOptions, 
  ForecastHorizon, 
  WeatherVariable,
  DataQueryResult,
  WeatherDataPoint,
  AnalogPattern,
  UncertaintyBand,
  HistoricalEvent
} from '../types';

interface UseDataQueryProps {
  timeRange: any;
  selectedHorizon: ForecastHorizon;
  variables: WeatherVariable[];
  options: WeatherPanelOptions;
}

interface UseDataQueryReturn {
  queryData: DataQueryResult | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useDataQuery = ({
  timeRange,
  selectedHorizon,
  variables,
  options
}: UseDataQueryProps): UseDataQueryReturn => {
  const [queryData, setQueryData] = useState<DataQueryResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prometheus queries for metrics
  const buildPrometheusQueries = useCallback(() => {
    const queries = {
      // Observations from current weather data
      observations: variables.map(variable => ({
        query: `weather_observation{variable="${variable.name}"}[${timeRange.raw.from}:${timeRange.raw.to}]`,
        variable: variable.name
      })),
      
      // Forecast data for selected horizon
      forecasts: variables.map(variable => ({
        query: `weather_forecast{variable="${variable.name}",horizon="${selectedHorizon.hours}h"}[${timeRange.raw.from}:${timeRange.raw.to}]`,
        variable: variable.name
      })),
      
      // Analog similarity scores
      analogs: `analog_similarity_score{horizon="${selectedHorizon.hours}h"}[1h]`,
      
      // Ensemble spread for uncertainty
      uncertainty: `ensemble_spread_current{horizon="${selectedHorizon.hours}h"}[${timeRange.raw.from}:${timeRange.raw.to}]`
    };
    
    return queries;
  }, [timeRange, selectedHorizon, variables]);

  // TimescaleDB queries for historical data
  const buildTimescaleQueries = useCallback(() => {
    return {
      historicalEvents: `
        SELECT 
          event_id,
          event_date,
          event_type,
          description,
          severity,
          similarity_score
        FROM historical_weather_events 
        WHERE 
          event_date >= $1 
          AND event_date <= $2
          AND similarity_score >= $3
        ORDER BY similarity_score DESC
        LIMIT 10
      `,
      
      analogPatterns: `
        SELECT 
          pattern_id,
          reference_date,
          similarity_score,
          confidence,
          synoptic_situation,
          weather_outcome,
          pattern_data
        FROM analog_patterns 
        WHERE 
          reference_date >= $1 
          AND reference_date <= $2
          AND horizon_hours = $3
          AND similarity_score >= $4
        ORDER BY similarity_score DESC
        LIMIT ${options.maxAnalogCount}
      `,
      
      verificationData: `
        SELECT 
          forecast_time,
          valid_time,
          variable_name,
          forecast_value,
          observed_value,
          error_metric
        FROM forecast_verification
        WHERE 
          forecast_time >= $1 
          AND forecast_time <= $2
          AND horizon_hours = $3
      `
    };
  }, [timeRange, selectedHorizon, options.maxAnalogCount]);

  // Mock data generation for development
  const generateMockData = useCallback((): DataQueryResult => {
    const now = new Date();
    const observations: WeatherDataPoint[] = [];
    const forecasts: WeatherDataPoint[] = [];
    const analogs: AnalogPattern[] = [];
    const uncertainty: UncertaintyBand[] = [];
    const historical: HistoricalEvent[] = [];

    // Generate observations for last 24 hours
    for (let i = 24; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000);
      
      variables.filter(v => v.visible).forEach(variable => {
        let baseValue = 20; // Default temperature
        
        switch (variable.name) {
          case 'temperature':
            baseValue = 15 + 10 * Math.sin((24 - i) * Math.PI / 12) + Math.random() * 4 - 2;
            break;
          case 'pressure':
            baseValue = 1013 + Math.random() * 20 - 10;
            break;
          case 'cape':
            baseValue = Math.max(0, 800 + Math.random() * 1200 - 600);
            break;
          case 'wind_speed':
            baseValue = 5 + Math.random() * 15;
            break;
        }

        observations.push({
          time,
          variable: variable.name,
          value: baseValue,
          type: 'observation',
          confidence: 0.8 + Math.random() * 0.2
        });
      });
    }

    // Generate forecast for selected horizon
    for (let i = 0; i <= selectedHorizon.hours; i++) {
      const time = new Date(now.getTime() + i * 60 * 60 * 1000);
      
      variables.filter(v => v.visible).forEach(variable => {
        let baseValue = 20;
        
        switch (variable.name) {
          case 'temperature':
            baseValue = 15 + 10 * Math.sin(i * Math.PI / 12) + Math.random() * 6 - 3;
            break;
          case 'pressure':
            baseValue = 1013 + Math.random() * 30 - 15;
            break;
          case 'cape':
            baseValue = Math.max(0, 800 + Math.random() * 1500 - 750);
            break;
          case 'wind_speed':
            baseValue = 5 + Math.random() * 20;
            break;
        }

        forecasts.push({
          time,
          variable: variable.name,
          value: baseValue,
          type: 'forecast',
          horizon: selectedHorizon.hours,
          confidence: 0.9 - (i / selectedHorizon.hours) * 0.3,
          uncertainty: {
            lower: baseValue - Math.random() * 5,
            upper: baseValue + Math.random() * 5
          }
        });

        // Generate uncertainty bands
        uncertainty.push({
          time,
          variable: variable.name,
          lower: baseValue - Math.random() * 5,
          upper: baseValue + Math.random() * 5,
          confidence: 0.9 - (i / selectedHorizon.hours) * 0.2
        });
      });
    }

    // Generate analog patterns
    for (let i = 0; i < options.maxAnalogCount; i++) {
      const patternDate = new Date(now.getTime() - Math.random() * 365 * 24 * 60 * 60 * 1000);
      
      analogs.push({
        id: `analog_${i}`,
        similarity: 0.9 - i * 0.1 - Math.random() * 0.1,
        date: patternDate,
        pattern: Array.from({ length: selectedHorizon.hours }, () => 
          20 + Math.random() * 20 - 10
        ),
        confidence: 0.8 - i * 0.1,
        metadata: {
          synopticSituation: ['High Pressure', 'Low Pressure', 'Frontal System', 'Trough'][Math.floor(Math.random() * 4)],
          weatherOutcome: ['Clear skies', 'Thunderstorms', 'Rain showers', 'Partly cloudy'][Math.floor(Math.random() * 4)],
          similarity_score: 0.9 - i * 0.1
        }
      });
    }

    // Generate historical events
    for (let i = 0; i < 3; i++) {
      const eventDate = new Date(now.getTime() - Math.random() * 30 * 24 * 60 * 60 * 1000);
      
      historical.push({
        id: `event_${i}`,
        date: eventDate,
        type: ['Severe Storm', 'Heat Wave', 'Cold Front'][i],
        description: `Similar weather pattern observed on ${eventDate.toDateString()}`,
        severity: ['high', 'medium', 'low'][i] as any,
        similarity: 0.8 - i * 0.1,
        analogPatterns: analogs.slice(0, 2)
      });
    }

    return {
      observations,
      forecasts,
      analogs,
      uncertainty,
      historical
    };
  }, [selectedHorizon, variables, options.maxAnalogCount]);

  // Fetch data from APIs
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // In a real implementation, this would make actual API calls
      // For now, we'll use mock data
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const mockData = generateMockData();
      setQueryData(mockData);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setQueryData(null);
    } finally {
      setIsLoading(false);
    }
  }, [generateMockData]);

  // Refetch function
  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  // Effect to fetch data when dependencies change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    queryData,
    isLoading,
    error,
    refetch
  };
};