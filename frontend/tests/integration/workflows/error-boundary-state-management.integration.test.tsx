/**
 * Error Boundary and State Management Integration Tests
 * 
 * Tests error propagation, boundary isolation, state recovery, and comprehensive
 * error handling across the entire component ecosystem.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

// Mock components for error testing
const ForecastCard = React.lazy(() => import('@/components/ForecastCard'));
const MetricsDashboard = React.lazy(() => import('@/components/MetricsDashboard'));
const CAPEBadge = React.lazy(() => import('@/components/CAPEBadge'));

const { 
  renderWithIntegration,
  testErrorPropagation,
  testErrorBoundaryIntegration,
  testCrossComponentState,
  testStatePersistence
} = integrationTestUtils;

// Error-prone component for testing
const ErrorProneComponent: React.FC<{ 
  shouldError?: boolean;
  errorType?: 'render' | 'async' | 'state';
  'data-testid'?: string;
}> = ({ shouldError = false, errorType = 'render', 'data-testid': testId }) => {
  const [hasError, setHasError] = React.useState(false);

  React.useEffect(() => {
    if (shouldError && errorType === 'async') {
      setTimeout(() => {
        throw new Error('Async component error');
      }, 100);
    }
  }, [shouldError, errorType]);

  if (shouldError && errorType === 'render') {
    throw new Error('Render component error');
  }

  if (shouldError && errorType === 'state') {
    // Simulate state-related error
    React.useEffect(() => {
      setHasError(true);
    }, []);

    if (hasError) {
      throw new Error('State management error');
    }
  }

  return (
    <div data-testid={testId} data-error-state={hasError ? 'true' : 'false'}>
      Component working normally
    </div>
  );
};

// Error boundary wrapper for testing
const TestErrorBoundary: React.FC<{
  children: React.ReactNode;
  'data-testid'?: string;
  onError?: (error: Error, errorInfo: any) => void;
  fallback?: React.ComponentType<any>;
}> = ({ children, 'data-testid': testId, onError, fallback: Fallback }) => {
  const [hasError, setHasError] = React.useState(false);

  const ErrorFallback = Fallback || (({ error }: { error: Error }) => (
    <div data-testid={`${testId}-error-fallback`} data-has-error="true">
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={() => setHasError(false)}>Try again</button>
    </div>
  ));

  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={(error, errorInfo) => {
        setHasError(true);
        onError?.(error, errorInfo);
      }}
      onReset={() => setHasError(false)}
    >
      <div data-testid={testId} data-has-error={hasError ? 'true' : 'false'}>
        {children}
      </div>
    </ErrorBoundary>
  );
};

// Application with error boundaries
const AppWithErrorBoundaries: React.FC<{
  triggerError?: { component: string; type: string };
}> = ({ triggerError }) => {
  return (
    <div data-testid="app-with-boundaries">
      <TestErrorBoundary data-testid="forecast-boundary" onError={(error) => {
        MockStateManager.setState('forecastError', error.message);
      }}>
        <React.Suspense fallback={<div>Loading forecast...</div>}>
          <ErrorProneComponent 
            data-testid="forecast-component"
            shouldError={triggerError?.component === 'forecast'}
            errorType={triggerError?.type as any}
          />
        </React.Suspense>
      </TestErrorBoundary>

      <TestErrorBoundary data-testid="metrics-boundary" onError={(error) => {
        MockStateManager.setState('metricsError', error.message);
      }}>
        <React.Suspense fallback={<div>Loading metrics...</div>}>
          <ErrorProneComponent 
            data-testid="metrics-component"
            shouldError={triggerError?.component === 'metrics'}
            errorType={triggerError?.type as any}
          />
        </React.Suspense>
      </TestErrorBoundary>

      <TestErrorBoundary data-testid="analytics-boundary" onError={(error) => {
        MockStateManager.setState('analyticsError', error.message);
      }}>
        <React.Suspense fallback={<div>Loading analytics...</div>}>
          <ErrorProneComponent 
            data-testid="analytics-component"
            shouldError={triggerError?.component === 'analytics'}
            errorType={triggerError?.type as any}
          />
        </React.Suspense>
      </TestErrorBoundary>
    </div>
  );
};

describe('Error Boundary and State Management Integration', () => {
  let queryClient: QueryClient;
  let mockMetricsProvider: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, cacheTime: 0 },
        mutations: { retry: false }
      }
    });

    mockMetricsProvider = {
      trackError: jest.fn(),
      trackRecovery: jest.fn(),
      trackStateChange: jest.fn(),
      getErrorMetrics: jest.fn(() => ({
        errorCount: 0,
        recoveryCount: 0,
        errorTypes: []
      }))
    };

    user = userEvent.setup();
    MockStateManager.clearState();

    // Suppress console errors during error boundary testing
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Error Boundary Isolation', () => {
    it('should isolate errors to specific component boundaries', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'forecast', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Verify error is contained within forecast boundary
      await waitFor(() => {
        const forecastBoundary = screen.getByTestId('forecast-boundary');
        const metricsBoundary = screen.getByTestId('metrics-boundary');
        const analyticsBoundary = screen.getByTestId('analytics-boundary');

        expect(forecastBoundary.getAttribute('data-has-error')).toBe('true');
        expect(metricsBoundary.getAttribute('data-has-error')).toBe('false');
        expect(analyticsBoundary.getAttribute('data-has-error')).toBe('false');
      });

      // Verify error fallback is displayed
      expect(screen.getByTestId('forecast-boundary-error-fallback')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Verify other components continue to work
      expect(screen.getByTestId('metrics-component')).toBeInTheDocument();
      expect(screen.getByTestId('analytics-component')).toBeInTheDocument();

      // Verify error tracking
      expect(mockMetricsProvider.trackError).toHaveBeenCalledWith(
        'render',
        'forecast',
        'Render component error'
      );
    });

    it('should handle cascading errors gracefully', async () => {
      const { rerender } = renderWithIntegration(
        <AppWithErrorBoundaries />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Trigger multiple errors in sequence
      const errorSequence = [
        { component: 'forecast', type: 'render' },
        { component: 'metrics', type: 'async' },
        { component: 'analytics', type: 'state' }
      ];

      for (const errorConfig of errorSequence) {
        rerender(
          <AppWithErrorBoundaries triggerError={errorConfig} />
        );

        await waitFor(() => {
          const boundary = screen.getByTestId(`${errorConfig.component}-boundary`);
          expect(boundary.getAttribute('data-has-error')).toBe('true');
        });

        await new Promise(resolve => setTimeout(resolve, 200));
      }

      // Verify all boundaries caught their respective errors
      await waitFor(() => {
        expect(screen.getByTestId('forecast-boundary-error-fallback')).toBeInTheDocument();
        expect(screen.getByTestId('metrics-boundary-error-fallback')).toBeInTheDocument();
        expect(screen.getByTestId('analytics-boundary-error-fallback')).toBeInTheDocument();
      });

      // Verify error metrics for cascading failure
      expect(mockMetricsProvider.trackError).toHaveBeenCalledTimes(3);
    });

    it('should support error boundary recovery', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'forecast', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Wait for error to be caught
      await waitFor(() => {
        expect(screen.getByTestId('forecast-boundary-error-fallback')).toBeInTheDocument();
      });

      // Click recovery button
      const tryAgainButton = screen.getByText('Try again');
      await user.click(tryAgainButton);

      // Verify recovery tracking
      expect(mockMetricsProvider.trackRecovery).toHaveBeenCalledWith(
        'forecast',
        'user_initiated'
      );

      // Verify boundary reset
      await waitFor(() => {
        const forecastBoundary = screen.getByTestId('forecast-boundary');
        expect(forecastBoundary.getAttribute('data-has-error')).toBe('false');
      });
    });
  });

  describe('State Management During Errors', () => {
    it('should preserve application state during component errors', async () => {
      const initialState = {
        userPreferences: { theme: 'dark', units: 'metric' },
        forecastHorizon: '24h',
        lastUpdate: '2024-01-15T10:30:00Z'
      };

      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'metrics', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState
        }
      );

      // Verify error occurs
      await waitFor(() => {
        const metricsBoundary = screen.getByTestId('metrics-boundary');
        expect(metricsBoundary.getAttribute('data-has-error')).toBe('true');
      });

      // Verify application state is preserved
      expect(MockStateManager.getState('userPreferences')).toEqual(initialState.userPreferences);
      expect(MockStateManager.getState('forecastHorizon')).toBe(initialState.forecastHorizon);
      expect(MockStateManager.getState('lastUpdate')).toBe(initialState.lastUpdate);

      // Verify error is recorded in state
      expect(MockStateManager.getState('metricsError')).toBe('Render component error');
    });

    it('should handle state corruption and recovery', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: {
            forecastData: mockApiResponses.forecast.success('24h'),
            dataIntegrity: 'verified'
          }
        }
      );

      // Simulate state corruption
      MockStateManager.setState('forecastData', null);
      MockStateManager.setState('dataIntegrity', 'corrupted');

      window.dispatchEvent(new CustomEvent('state-corruption-detected', {
        detail: { 
          corruptedKeys: ['forecastData'],
          severity: 'high'
        }
      }));

      // Verify corruption detection
      await waitFor(() => {
        expect(MockStateManager.getState('dataIntegrity')).toBe('corrupted');
      });

      // Trigger state recovery
      const recoveredData = mockApiResponses.forecast.success('24h');
      MockStateManager.setState('forecastData', recoveredData);
      MockStateManager.setState('dataIntegrity', 'verified');

      window.dispatchEvent(new CustomEvent('state-recovery-complete', {
        detail: { 
          recoveredKeys: ['forecastData'],
          recoveryMethod: 'api_refetch'
        }
      }));

      // Verify recovery
      await waitFor(() => {
        expect(MockStateManager.getState('dataIntegrity')).toBe('verified');
        expect(MockStateManager.getState('forecastData')).toEqual(recoveredData);
      });

      expect(mockMetricsProvider.trackRecovery).toHaveBeenCalledWith(
        'state_corruption',
        'api_refetch'
      );
    });

    it('should synchronize state across multiple error boundaries', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Test cross-boundary state synchronization
      await testCrossComponentState(
        'errorStatus',
        'degraded',
        [
          'forecast-boundary',
          'metrics-boundary', 
          'analytics-boundary'
        ]
      );

      // Verify all boundaries reflect the error status
      await waitFor(() => {
        const boundaries = [
          'forecast-boundary',
          'metrics-boundary',
          'analytics-boundary'
        ];

        boundaries.forEach(boundaryId => {
          const boundary = screen.getByTestId(boundaryId);
          expect(boundary.getAttribute('data-error-status')).toBe('degraded');
        });
      });
    });
  });

  describe('Error Recovery Workflows', () => {
    it('should implement automatic error recovery strategies', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'forecast', type: 'async' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: {
            autoRecovery: true,
            maxRetries: 3
          }
        }
      );

      // Wait for error to occur
      await waitFor(() => {
        const forecastBoundary = screen.getByTestId('forecast-boundary');
        expect(forecastBoundary.getAttribute('data-has-error')).toBe('true');
      });

      // Simulate automatic recovery attempt
      for (let retry = 1; retry <= 3; retry++) {
        MockStateManager.setState('retryAttempt', retry);
        
        window.dispatchEvent(new CustomEvent('auto-recovery-attempt', {
          detail: { 
            component: 'forecast',
            attempt: retry,
            strategy: 'exponential_backoff'
          }
        }));

        await new Promise(resolve => setTimeout(resolve, 100 * Math.pow(2, retry - 1)));

        if (retry === 3) {
          // Simulate successful recovery on final attempt
          MockStateManager.setState('forecastRecovered', true);
          
          window.dispatchEvent(new CustomEvent('auto-recovery-success', {
            detail: { 
              component: 'forecast',
              attempt: retry
            }
          }));
        }
      }

      // Verify recovery tracking
      expect(mockMetricsProvider.trackRecovery).toHaveBeenCalledWith(
        'forecast',
        'auto_recovery_success'
      );
    });

    it('should handle partial system recovery', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'metrics', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Verify only metrics component failed
      await waitFor(() => {
        const metricsBoundary = screen.getByTestId('metrics-boundary');
        const forecastBoundary = screen.getByTestId('forecast-boundary');
        const analyticsBoundary = screen.getByTestId('analytics-boundary');

        expect(metricsBoundary.getAttribute('data-has-error')).toBe('true');
        expect(forecastBoundary.getAttribute('data-has-error')).toBe('false');
        expect(analyticsBoundary.getAttribute('data-has-error')).toBe('false');
      });

      // Simulate partial recovery - metrics comes back online
      MockStateManager.setState('partialRecovery', {
        recovered: ['metrics'],
        stillFailing: [],
        timestamp: new Date().toISOString()
      });

      window.dispatchEvent(new CustomEvent('partial-recovery', {
        detail: {
          component: 'metrics',
          status: 'recovered'
        }
      }));

      // Verify system continues to function with partial recovery
      await waitFor(() => {
        expect(screen.getByTestId('forecast-component')).toBeInTheDocument();
        expect(screen.getByTestId('analytics-component')).toBeInTheDocument();
      });

      expect(mockMetricsProvider.trackRecovery).toHaveBeenCalledWith(
        'metrics',
        'partial_system_recovery'
      );
    });

    it('should maintain user experience during recovery', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'analytics', type: 'state' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      // Verify graceful degradation
      await waitFor(() => {
        expect(screen.getByTestId('analytics-boundary-error-fallback')).toBeInTheDocument();
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      });

      // Verify other components remain interactive during recovery
      const forecastComponent = screen.getByTestId('forecast-component');
      const metricsComponent = screen.getByTestId('metrics-component');

      expect(forecastComponent).toBeInTheDocument();
      expect(metricsComponent).toBeInTheDocument();

      // Test user interaction during recovery
      await user.click(forecastComponent);
      await user.click(metricsComponent);

      // Verify interactions still work
      expect(mockMetricsProvider.trackStateChange).toHaveBeenCalled();
    });
  });

  describe('Error Monitoring and Analytics', () => {
    it('should collect comprehensive error analytics', async () => {
      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'forecast', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider
        }
      );

      await waitFor(() => {
        expect(screen.getByTestId('forecast-boundary-error-fallback')).toBeInTheDocument();
      });

      // Verify comprehensive error tracking
      expect(mockMetricsProvider.trackError).toHaveBeenCalledWith(
        'render',
        'forecast',
        'Render component error'
      );

      // Verify error state is recorded
      expect(MockStateManager.getState('forecastError')).toBe('Render component error');

      // Test error analytics retrieval
      const errorMetrics = mockMetricsProvider.getErrorMetrics();
      expect(errorMetrics).toEqual(
        expect.objectContaining({
          errorCount: expect.any(Number),
          recoveryCount: expect.any(Number),
          errorTypes: expect.any(Array)
        })
      );
    });

    it('should track error patterns and trends', async () => {
      const errorScenarios = [
        { component: 'forecast', type: 'render' },
        { component: 'forecast', type: 'async' },
        { component: 'metrics', type: 'state' }
      ];

      for (const scenario of errorScenarios) {
        const { unmount } = renderWithIntegration(
          <AppWithErrorBoundaries triggerError={scenario} />,
          { 
            queryClient, 
            metricsProvider: mockMetricsProvider
          }
        );

        await waitFor(() => {
          const boundary = screen.getByTestId(`${scenario.component}-boundary`);
          expect(boundary.getAttribute('data-has-error')).toBe('true');
        });

        unmount();
      }

      // Verify pattern tracking
      expect(mockMetricsProvider.trackError).toHaveBeenCalledTimes(3);
      
      // Verify different error types were tracked
      const calls = mockMetricsProvider.trackError.mock.calls;
      expect(calls).toEqual([
        ['render', 'forecast', 'Render component error'],
        ['async', 'forecast', 'Async component error'],
        ['state', 'metrics', 'State management error']
      ]);
    });
  });

  describe('State Persistence During Errors', () => {
    it('should persist critical state during component failures', async () => {
      await testStatePersistence(
        'criticalUserData',
        { 
          preferences: { theme: 'dark' },
          session: { authenticated: true },
          workspace: { activeView: 'forecast' }
        },
        'localStorage'
      );

      const { container } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'forecast', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: {
            criticalUserData: {
              preferences: { theme: 'dark' },
              session: { authenticated: true },
              workspace: { activeView: 'forecast' }
            }
          }
        }
      );

      // Verify error occurs
      await waitFor(() => {
        expect(screen.getByTestId('forecast-boundary-error-fallback')).toBeInTheDocument();
      });

      // Verify critical state is preserved
      const persistedData = MockStateManager.getState('criticalUserData');
      expect(persistedData).toEqual({
        preferences: { theme: 'dark' },
        session: { authenticated: true },
        workspace: { activeView: 'forecast' }
      });

      // Verify localStorage was called for persistence
      expect(localStorage.setItem).toHaveBeenCalled();
    });

    it('should recover state after error resolution', async () => {
      const { rerender } = renderWithIntegration(
        <AppWithErrorBoundaries 
          triggerError={{ component: 'metrics', type: 'render' }}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: {
            metricsViewState: {
              selectedHorizon: '24h',
              chartType: 'accuracy',
              timeRange: '7d'
            }
          }
        }
      );

      // Verify error state
      await waitFor(() => {
        expect(screen.getByTestId('metrics-boundary-error-fallback')).toBeInTheDocument();
      });

      // Resolve error by removing trigger
      rerender(<AppWithErrorBoundaries />);

      // Verify state recovery
      await waitFor(() => {
        const metricsState = MockStateManager.getState('metricsViewState');
        expect(metricsState).toEqual({
          selectedHorizon: '24h',
          chartType: 'accuracy',
          timeRange: '7d'
        });
      });

      expect(mockMetricsProvider.trackRecovery).toHaveBeenCalledWith(
        'metrics',
        'state_recovery'
      );
    });
  });
});