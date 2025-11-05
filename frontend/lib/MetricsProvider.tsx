'use client';

import React, {
  createContext,
  useContext,
  useCallback,
  useRef,
  useEffect
} from 'react';
import {
  trackUIInteraction,
  trackVariableToggle,
  trackHorizonChange,
  trackCapeModalOpen,
  trackPageLoad,
  trackForecastRender,
  trackAPIResponse,
  trackUIError,
  trackForecastError,
  processForecastForMetrics
} from './metrics';

/**
 * Metrics Context for UI Interaction Tracking
 *
 * Provides a centralized way to track user interactions and system metrics
 * throughout the weather forecasting frontend application.
 */

interface MetricsContextType {
  // UI Interaction Tracking
  trackInteraction: (type: string, component: string, horizon?: string) => void;
  trackVariableToggle: (variable: string, action: 'show' | 'hide') => void;
  trackHorizonChange: (from: string, to: string) => void;
  trackCapeModal: (horizon: string) => void;

  // Performance Tracking
  trackPageLoad: (duration: number) => void;
  trackForecastRender: (
    duration: number,
    horizon: string,
    varCount: number
  ) => void;
  trackAPICall: (
    endpoint: string,
    statusCode: number,
    duration: number
  ) => void;

  // Error Tracking
  trackError: (errorType: string, component: string) => void;
  trackForecastError: (horizon: string, errorType: string) => void;

  // Forecast Data Processing
  processForecastData: (forecasts: Record<string, any>) => void;

  // Timer utilities
  startTimer: () => () => number; // Returns a function that returns elapsed time in seconds
}

const MetricsContext = createContext<MetricsContextType | null>(null);

export const useMetrics = () => {
  const context = useContext(MetricsContext);
  if (!context) {
    throw new Error('useMetrics must be used within a MetricsProvider');
  }
  return context;
};

interface MetricsProviderProps {
  children: React.ReactNode;
}

export const MetricsProvider: React.FC<MetricsProviderProps> = ({
  children
}) => {
  const pageLoadStartTime = useRef<number>(Date.now());

  // Track page load on mount
  useEffect(() => {
    const loadDuration = (Date.now() - pageLoadStartTime.current) / 1000;
    trackPageLoad(loadDuration);
  }, []);

  const trackInteraction = useCallback(
    (type: string, component: string, horizon?: string) => {
      try {
        trackUIInteraction(type, component, horizon);
      } catch (error) {
        console.error('Error tracking UI interaction:', error);
      }
    },
    []
  );

  const handleVariableToggle = useCallback(
    (variable: string, action: 'show' | 'hide') => {
      try {
        trackVariableToggle(variable, action);
      } catch (error) {
        console.error('Error tracking variable toggle:', error);
      }
    },
    []
  );

  const handleHorizonChange = useCallback((from: string, to: string) => {
    try {
      trackHorizonChange(from, to);
    } catch (error) {
      console.error('Error tracking horizon change:', error);
    }
  }, []);

  const trackCapeModal = useCallback((horizon: string) => {
    try {
      trackCapeModalOpen(horizon);
    } catch (error) {
      console.error('Error tracking CAPE modal:', error);
    }
  }, []);

  const handlePageLoad = useCallback((duration: number) => {
    try {
      trackPageLoad(duration);
    } catch (error) {
      console.error('Error tracking page load:', error);
    }
  }, []);

  const handleForecastRender = useCallback(
    (duration: number, horizon: string, varCount: number) => {
      try {
        trackForecastRender(duration, horizon, varCount);
      } catch (error) {
        console.error('Error tracking forecast render:', error);
      }
    },
    []
  );

  const trackAPICall = useCallback(
    (endpoint: string, statusCode: number, duration: number) => {
      try {
        trackAPIResponse(endpoint, statusCode, duration);
      } catch (error) {
        console.error('Error tracking API response:', error);
      }
    },
    []
  );

  const trackError = useCallback((errorType: string, component: string) => {
    try {
      trackUIError(errorType, component);
    } catch (error) {
      console.error('Error tracking UI error:', error);
    }
  }, []);

  const handleForecastError = useCallback(
    (horizon: string, errorType: string) => {
      try {
        trackForecastError(horizon, errorType);
      } catch (error) {
        console.error('Error tracking forecast error:', error);
      }
    },
    []
  );

  const processForecastData = useCallback((forecasts: Record<string, any>) => {
    try {
      processForecastForMetrics(forecasts);
    } catch (error) {
      console.error('Error processing forecast metrics:', error);
    }
  }, []);

  const startTimer = useCallback(() => {
    const startTime = Date.now();
    return () => (Date.now() - startTime) / 1000;
  }, []);

  const contextValue: MetricsContextType = {
    trackInteraction,
    trackVariableToggle: handleVariableToggle,
    trackHorizonChange: handleHorizonChange,
    trackCapeModal,
    trackPageLoad: handlePageLoad,
    trackForecastRender: handleForecastRender,
    trackAPICall,
    trackError,
    trackForecastError: handleForecastError,
    processForecastData,
    startTimer
  };

  return (
    <MetricsContext.Provider value={contextValue}>
      {children}
    </MetricsContext.Provider>
  );
};
