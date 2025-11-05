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
  /** Refetch function */
  refetch: () => Promise<void>;
  /** Last fetch timestamp */
  lastFetch: Date | null;
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
    maxRetries = 3
  } = options;

  const [data, setData] = useState<AnalogExplorerData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);

  const cacheKey = `analog-${horizon}`;

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
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = new URL('/api/analogs', window.location.origin);
      url.searchParams.set('horizon', horizon);

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        // Add timeout for analog requests
        signal: AbortSignal.timeout(20000) // 20 second timeout
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (isApiError(result)) {
        throw new Error(result.error);
      }

      // Cache the successful result
      analogCache.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      });

      setData(result);
      setError(null);
      setLastFetch(new Date());
      setRetryCount(0); // Reset retry count on success
    } catch (err) {
      console.error('Error fetching analog data:', err);
      
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);

      // Retry logic
      if (retryOnError && retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Exponential backoff, max 10s
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchAnalogData();
        }, delay);
      }
    } finally {
      setLoading(false);
    }
  }, [horizon, cacheKey, getCachedData, retryOnError, retryCount, maxRetries]);

  // Refetch function for manual refresh
  const refetch = useCallback(async (): Promise<void> => {
    // Clear cache for this horizon
    analogCache.delete(cacheKey);
    setRetryCount(0);
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
    };
  }, []);

  return {
    data,
    loading,
    error,
    refetch,
    lastFetch
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