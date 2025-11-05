/**
 * Tests for useAnalogData hook
 * Ensures proper data fetching, caching, and error handling
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { useAnalogData, preloadAnalogData, clearAnalogCache } from '@/lib/useAnalogData';
import type { AnalogExplorerData } from '@/types';

// Mock data
const mockAnalogData: AnalogExplorerData = {
  forecast_horizon: '24h',
  top_analogs: [
    {
      date: '2023-01-01T00:00:00Z',
      similarity_score: 0.95,
      initial_conditions: {
        't2m': 20.5,
        'u10': -2.3,
        'v10': 1.8,
        'msl': 1015.2,
        'r850': 65.3,
        'tp6h': 0.0,
        'cape': 850.0,
        't850': 18.2,
        'z500': 5820.0,
      },
      timeline: [
        {
          hours_offset: 0,
          values: {
            't2m': 20.5,
            'u10': -2.3,
            'v10': 1.8,
            'msl': 1015.2,
            'r850': 65.3,
            'tp6h': 0.0,
            'cape': 850.0,
            't850': 18.2,
            'z500': 5820.0,
          },
          temperature_trend: 'stable',
          pressure_trend: 'rising',
        },
      ],
      outcome_narrative: 'Test outcome',
      season_info: {
        month: 1,
        season: 'summer',
      },
    },
  ],
  ensemble_stats: {
    mean_outcomes: {
      't2m': 23.0,
      'u10': -2.0,
      'v10': 2.0,
      'msl': 1017.0,
      'r850': 70.0,
      'tp6h': 0.2,
      'cape': 900.0,
      't850': 20.0,
      'z500': 5825.0,
    },
    outcome_uncertainty: {
      't2m': 1.5,
      'u10': 0.8,
      'v10': 0.6,
      'msl': 2.1,
      'r850': 3.2,
      'tp6h': 0.3,
      'cape': 150.0,
      't850': 1.2,
      'z500': 8.0,
    },
    common_events: ['Temperature increase'],
  },
  generated_at: '2023-12-01T12:00:00Z',
};

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    origin: 'http://localhost:3000',
  },
  writable: true,
});

describe('useAnalogData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    clearAnalogCache(); // Clear cache before each test
    
    // Mock successful fetch response
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockAnalogData,
    });
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  it('fetches analog data successfully', async () => {
    const { result } = renderHook(() => useAnalogData('24h'));

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();

    // Wait for fetch to complete
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockAnalogData);
    expect(result.current.error).toBeNull();
    expect(result.current.lastFetch).toBeInstanceOf(Date);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:3000/api/analogs?horizon=24h',
      expect.objectContaining({
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    );
  });

  it('handles API errors correctly', async () => {
    const errorMessage = 'API Error';
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ error: errorMessage }),
    });

    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(errorMessage);
  });

  it('handles network errors correctly', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('Network error');
  });

  it('handles HTTP errors correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    });

    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe('HTTP 500: Internal Server Error');
  });

  it('uses cached data when available', async () => {
    // First render - should fetch
    const { result: result1 } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result1.current.loading).toBe(false);
    });

    expect(result1.current.data).toEqual(mockAnalogData);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Second render with same horizon - should use cache
    const { result: result2 } = renderHook(() => useAnalogData('24h'));

    // Should immediately have data from cache
    expect(result2.current.data).toEqual(mockAnalogData);
    expect(result2.current.loading).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(1); // No additional fetch
  });

  it('refetch clears cache and fetches new data', async () => {
    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Call refetch
    await act(async () => {
      await result.current.refetch();
    });

    // Should have called fetch again
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('handles different horizons separately', async () => {
    // Render with 24h horizon
    const { result: result24h } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result24h.current.loading).toBe(false);
    });

    // Render with 48h horizon
    const { result: result48h } = renderHook(() => useAnalogData('48h'));

    await waitFor(() => {
      expect(result48h.current.loading).toBe(false);
    });

    // Should have made separate API calls
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockFetch).toHaveBeenNthCalledWith(
      1,
      'http://localhost:3000/api/analogs?horizon=24h',
      expect.any(Object)
    );
    expect(mockFetch).toHaveBeenNthCalledWith(
      2,
      'http://localhost:3000/api/analogs?horizon=48h',
      expect.any(Object)
    );
  });

  it('respects autoFetch option', async () => {
    const { result } = renderHook(() => 
      useAnalogData('24h', { autoFetch: false })
    );

    // Should not fetch automatically
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(mockFetch).not.toHaveBeenCalled();

    // Manual refetch should work
    await act(async () => {
      await result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockAnalogData);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('handles cache expiration correctly', async () => {
    const shortCacheDuration = 100; // 100ms

    // First render with short cache
    const { result: result1 } = renderHook(() => 
      useAnalogData('24h', { cacheDuration: shortCacheDuration })
    );

    await waitFor(() => {
      expect(result1.current.loading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Wait for cache to expire
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, shortCacheDuration + 10));
    });

    // Second render should fetch again due to expired cache
    const { result: result2 } = renderHook(() => 
      useAnalogData('24h', { cacheDuration: shortCacheDuration })
    );

    await waitFor(() => {
      expect(result2.current.loading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('handles retry logic on errors', async () => {
    jest.useFakeTimers();

    // Mock initial failure then success
    mockFetch
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockAnalogData,
      });

    const { result } = renderHook(() => 
      useAnalogData('24h', { retryOnError: true, maxRetries: 1 })
    );

    // Should initially fail
    await waitFor(() => {
      expect(result.current.error).toBe('Network error');
    });

    // Advance timers to trigger retry
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // Should succeed on retry
    await waitFor(() => {
      expect(result.current.data).toEqual(mockAnalogData);
      expect(result.current.error).toBeNull();
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);

    jest.useRealTimers();
  });

  it('preloads data correctly', async () => {
    await preloadAnalogData('24h');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:3000/api/analogs?horizon=24h',
      expect.objectContaining({
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    );

    // Subsequent hook should use preloaded data
    const { result } = renderHook(() => useAnalogData('24h'));

    expect(result.current.data).toEqual(mockAnalogData);
    expect(result.current.loading).toBe(false);
  });

  it('clears cache correctly', async () => {
    // Load data into cache
    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Clear cache
    clearAnalogCache('24h');

    // New render should fetch again
    const { result: result2 } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result2.current.loading).toBe(false);
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('handles timeout errors correctly', async () => {
    const timeoutError = new Error('Timeout');
    timeoutError.name = 'AbortError';
    mockFetch.mockRejectedValueOnce(timeoutError);

    const { result } = renderHook(() => useAnalogData('24h'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Timeout');
  });
});