/**
 * React hook for fetching analog explorer data
 * Provides data fetching, caching, and error handling for analog patterns
 */

import { useState, useEffect, useCallback } from 'react';
import type { AnalogExplorerData, ForecastHorizon, ApiError } from '@/types';
import { isApiError } from '@/types';

interface UseAnalogDataResult {
  /** Analog explorer data */
  data: AnalogExplorerData | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: string | null;
  /** Detailed error information */
  errorDetails?: {
    code?: string;
    type: 'network' | 'timeout' | 'server' | 'validation' | 'unknown';
    retryable: boolean;
    retryCount: number;
    maxRetries: number;
  };
  /** Refetch function */
  refetch: () => Promise<void>;
  /** Last fetch timestamp */
  lastFetch: Date | null;
  /** Whether data is from cache */
  isFromCache: boolean;
  /** Data source information */
  dataSource?: 'api' | 'cache' | 'fallback';
}

interface UseAnalogDataOptions {
  /** Auto-fetch on mount */
  autoFetch?: boolean;
  /** Cache duration in milliseconds (default: 10 minutes) */
  cacheDuration?: number;
  /** Retry on error */
  retryOnError?: boolean;
  /** Maximum retry attempts */
  maxRetries?: number;
  /** Request timeout in milliseconds (default: 20 seconds) */
  timeout?: number;
  /** Enable detailed error reporting */
  detailedErrors?: boolean;
  /** Fallback to empty data instead of error state */
  enableFallback?: boolean;
}

// In-memory cache for analog data
const analogCache = new Map<string, {
  data: AnalogExplorerData;
  timestamp: number;
}>();

export function useAnalogData(
  horizon: ForecastHorizon,
  options: UseAnalogDataOptions = {}
): UseAnalogDataResult {
  const {
    autoFetch = true,
    cacheDuration = 10 * 60 * 1000, // 10 minutes
    retryOnError = true,
    maxRetries = 3,
    timeout = 20000, // 20 seconds
    detailedErrors = false,
    enableFallback = false
  } = options;

  const [data, setData] = useState<AnalogExplorerData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<UseAnalogDataResult['errorDetails']>();
  const [lastFetch, setLastFetch] = useState<Date | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);
  const [isFromCache, setIsFromCache] = useState<boolean>(false);
  const [dataSource, setDataSource] = useState<UseAnalogDataResult['dataSource']>();

  const cacheKey = `analog-${horizon}`;

  // Helper function to create error details
  const createErrorDetails = useCallback((
    error: Error | unknown,
    type: UseAnalogDataResult['errorDetails']['type'] = 'unknown'
  ): UseAnalogDataResult['errorDetails'] => {
    if (!detailedErrors) return undefined;

    const isRetryable = type === 'network' || type === 'timeout' || type === 'server';
    
    return {
      code: error instanceof Error ? (error as any).code : undefined,
      type,
      retryable: isRetryable && retryCount < maxRetries,
      retryCount,
      maxRetries
    };
  }, [detailedErrors, retryCount, maxRetries]);

  // Helper function to create fallback data
  const createFallbackData = useCallback((): AnalogExplorerData | null => {
    if (!enableFallback) return null;
    
    return {
      forecast_horizon: horizon,
      analogs: [],
      total_analogs: 0,
      data_source: 'fallback',
      generated_at: new Date().toISOString(),
      faiss_search_time_ms: null,
      query_embedding: null
    };
  }, [enableFallback, horizon]);

  // Check cache for existing data
  const getCachedData = useCallback((): AnalogExplorerData | null => {
    const cached = analogCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < cacheDuration) {
      return cached.data;
    }
    return null;
  }, [cacheKey, cacheDuration]);

  // Fetch analog data from API
  const fetchAnalogData = useCallback(async (): Promise<void> => {
    // Check cache first
    const cachedData = getCachedData();
    if (cachedData) {
      setData(cachedData);
      setError(null);
      setErrorDetails(undefined);
      setIsFromCache(true);
      setDataSource('cache');
      return;
    }

    setLoading(true);
    setError(null);
    setErrorDetails(undefined);
    setIsFromCache(false);

    try {
      const url = new URL('/api/analogs', window.location.origin);
      url.searchParams.set('horizon', horizon);

      const abortController = new AbortController();
      const timeoutId = setTimeout(() => abortController.abort(), timeout);

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: abortController.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorType = response.status >= 500 ? 'server' : 'network';
        const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
        (error as any).code = response.status.toString();
        throw { error, type: errorType };
      }

      const result = await response.json();

      if (isApiError(result)) {
        const error = new Error(result.error);
        throw { error, type: 'validation' };
      }

      // Validate that we have proper analog data
      if (!result || typeof result !== 'object') {
        const error = new Error('Invalid response format');
        throw { error, type: 'validation' };
      }

      // Enhance result with data source info if not present
      if (!result.data_source) {
        result.data_source = 'api';
      }

      // Cache the successful result
      analogCache.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      });

      setData(result);
      setError(null);
      setErrorDetails(undefined);
      setLastFetch(new Date());
      setRetryCount(0); // Reset retry count on success
      setDataSource('api');
    } catch (err) {
      console.error('Error fetching analog data:', err);
      
      let errorType: UseAnalogDataResult['errorDetails']['type'] = 'unknown';
      let actualError: Error;

      // Handle structured error with type
      if (err && typeof err === 'object' && 'error' in err && 'type' in err) {
        actualError = err.error as Error;
        errorType = err.type as UseAnalogDataResult['errorDetails']['type'];
      } else if (err instanceof Error) {
        actualError = err;
        // Determine error type from error properties
        if (err.name === 'AbortError' || err.message.includes('timeout')) {
          errorType = 'timeout';
        } else if (err.message.includes('fetch') || err.message.includes('network')) {
          errorType = 'network';
        }
      } else {
        actualError = new Error('Unknown error occurred');
      }
      
      const errorMessage = actualError.message;
      const details = createErrorDetails(actualError, errorType);
      
      setError(errorMessage);
      setErrorDetails(details);

      // Try fallback before retry
      if (enableFallback && retryCount >= maxRetries) {
        const fallbackData = createFallbackData();
        if (fallbackData) {
          setData(fallbackData);
          setDataSource('fallback');
          setError(null);
          setErrorDetails(undefined);
          return;
        }
      }

      // Retry logic
      if (retryOnError && retryCount < maxRetries && (details?.retryable ?? true)) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Exponential backoff, max 10s
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchAnalogData();
        }, delay);
      } else if (enableFallback) {
        // Final fallback if all retries failed
        const fallbackData = createFallbackData();
        if (fallbackData) {
          setData(fallbackData);
          setDataSource('fallback');
          setError(null);
          setErrorDetails(undefined);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [horizon, cacheKey, getCachedData, retryOnError, retryCount, maxRetries, timeout, createErrorDetails, enableFallback, createFallbackData]);

  // Refetch function for manual refresh
  const refetch = useCallback(async (): Promise<void> => {
    // Clear cache for this horizon
    analogCache.delete(cacheKey);
    setRetryCount(0);
    setError(null);
    setErrorDetails(undefined);
    setIsFromCache(false);
    setDataSource(undefined);
    await fetchAnalogData();
  }, [cacheKey, fetchAnalogData]);

  // Auto-fetch on mount and horizon change
  useEffect(() => {
    if (autoFetch) {
      fetchAnalogData();
    }
  }, [horizon, autoFetch, fetchAnalogData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cancel any pending requests by clearing the component state
      setLoading(false);
      setError(null);
      setErrorDetails(undefined);
    };
  }, []);

  return {
    data,
    loading,
    error,
    errorDetails,
    refetch,
    lastFetch,
    isFromCache,
    dataSource
  };
}

// Utility function to preload analog data
export function preloadAnalogData(horizon: ForecastHorizon): Promise<void> {
  const url = new URL('/api/analogs', window.location.origin);
  url.searchParams.set('horizon', horizon);

  return fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })
    .then(response => response.json())
    .then(result => {
      if (!isApiError(result)) {
        // Cache the preloaded data
        analogCache.set(`analog-${horizon}`, {
          data: result,
          timestamp: Date.now()
        });
      }
    })
    .catch(error => {
      console.warn('Failed to preload analog data:', error);
    });
}

// Utility function to clear analog cache
export function clearAnalogCache(horizon?: ForecastHorizon): void {
  if (horizon) {
    analogCache.delete(`analog-${horizon}`);
  } else {
    analogCache.clear();
  }
}