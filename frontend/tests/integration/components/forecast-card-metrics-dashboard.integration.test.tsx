/**
 * ForecastCard ↔ MetricsDashboard Integration Tests
 * 
 * Tests the data flow and synchronization between ForecastCard and MetricsDashboard
 * components, including metrics tracking, performance monitoring, and state synchronization.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { ForecastCard } from '@/components/ForecastCard';
import MetricsDashboard from '@/components/MetricsDashboard';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

const { 
  renderWithIntegration, 
  expectMetricsTracked, 
  testDataFlow,
  testApiCallCoordination,
  measureInteractionPerformance
} = integrationTestUtils;

describe('ForecastCard ↔ MetricsDashboard Integration', () => {
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
      trackInteraction: jest.fn(),
      trackCapeModal: jest.fn(),
      trackAnalogToggle: jest.fn(),
      trackDetailsToggle: jest.fn(),
      trackExport: jest.fn(),
      trackRefresh: jest.fn(),
      updatePerformance: jest.fn(),
      getMetrics: jest.fn(() => ({
        interactions: 0,
        performance: { loadTime: 100, renderTime: 50 }
      }))
    };

    user = userEvent.setup();
    MockStateManager.clearState();
  });

  describe('Data Flow Integration', () => {
    it('should synchronize forecast data between components', async () => {
      const forecastData = mockApiResponses.forecast.success('24h');
      const metricsData = mockApiResponses.metrics.success();

      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-24h"
            data-sync-state="loaded"
            data-last-update="2024-01-15T10:30:00Z"
            data-forecast-horizon="24h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-sync-state="loaded"
            data-last-update="2024-01-15T10:30:00Z"
            data-forecast-horizon="24h"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: { 
            forecastData,
            metricsData,
            lastUpdate: '2024-01-15T10:30:00Z'
          }
        }
      );

      // Verify components are synchronized
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-24h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-sync-state')).toBe('loaded');
        expect(metricsDashboard.getAttribute('data-sync-state')).toBe('loaded');
        expect(forecastCard.getAttribute('data-last-update')).toBe(
          metricsDashboard.getAttribute('data-last-update')
        );
      });
    });

    it('should propagate metrics updates from ForecastCard to MetricsDashboard', async () => {
      const forecastData = mockApiResponses.forecast.success('12h');

      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-12h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-loading="false"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate user interaction that should trigger metrics update
      const capeButton = screen.getByText(/1250 J\/kg/);
      
      await testDataFlow(
        'forecast-card-12h',
        'metrics-dashboard',
        async () => {
          await user.click(capeButton);
        },
        {
          'last-interaction': 'cape_modal_open'
        }
      );

      // Verify metrics provider was called
      expectMetricsTracked(mockMetricsProvider, [
        { method: 'trackCapeModal', args: ['12h'] },
        { method: 'trackInteraction', args: ['cape_modal_open', 'forecast_card', '12h'] }
      ]);
    });

    it('should coordinate loading states between components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={mockApiResponses.forecast.success('6h')}
            data-testid="forecast-card-6h"
            data-loading="false"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-loading="false"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Test loading state coordination
      await integrationTestUtils.testLoadingStateCoordination(
        ['forecast-card-6h', 'metrics-dashboard'],
        async () => {
          // Simulate API call that would trigger loading states
          MockStateManager.setState('loading', true);
          window.dispatchEvent(new CustomEvent('api-loading-start'));
          
          await new Promise(resolve => setTimeout(resolve, 100));
          
          MockStateManager.setState('loading', false);
          window.dispatchEvent(new CustomEvent('api-loading-end'));
        }
      );
    });
  });

  describe('Performance Integration', () => {
    it('should maintain performance standards during component interactions', async () => {
      const forecastData = mockApiResponses.forecast.success('24h');

      renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-24h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Measure performance of component interaction
      const interactionTime = await measureInteractionPerformance(
        async () => {
          const detailsButton = screen.getByText(/Forecast Details/);
          await user.click(detailsButton);
          
          await waitFor(() => {
            expect(screen.getByText(/Generated:/)).toBeInTheDocument();
          });
        },
        500 // Max 500ms for interaction
      );

      expect(interactionTime).toBeLessThan(500);
      
      // Verify performance metrics were updated
      expect(mockMetricsProvider.updatePerformance).toHaveBeenCalledWith(
        expect.objectContaining({
          interactionTime: expect.any(Number),
          component: 'forecast_card'
        })
      );
    });

    it('should handle concurrent component updates efficiently', async () => {
      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={mockApiResponses.forecast.success('24h')}
            data-testid="forecast-card-24h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate concurrent updates
      const concurrentUpdates = [
        () => {
          const analogsButton = screen.getByText(/Historical Analogs/);
          return user.click(analogsButton);
        },
        () => {
          const refreshButton = screen.getByTitle(/Refresh Data/);
          return user.click(refreshButton);
        },
        () => {
          const exportButton = screen.getByText(/Export/);
          return user.click(exportButton);
        }
      ];

      const startTime = performance.now();
      await Promise.all(concurrentUpdates.map(update => update()));
      const endTime = performance.now();

      // Concurrent updates should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(1000);

      // Verify all interactions were tracked
      await waitFor(() => {
        expect(mockMetricsProvider.trackInteraction).toHaveBeenCalledTimes(3);
      });
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle API errors gracefully across components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={mockApiResponses.forecast.success('24h')}
            data-testid="forecast-card-24h"
            data-error-state="false"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-error-state="false"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Test error propagation
      await integrationTestUtils.testErrorPropagation(
        'forecast-card-24h',
        ['forecast-card-24h', 'metrics-dashboard'],
        async () => {
          // Simulate API error
          MockStateManager.setState('apiError', {
            type: 'server_error',
            message: 'Internal server error'
          });
          
          window.dispatchEvent(new CustomEvent('api-error', {
            detail: { 
              type: 'server_error',
              message: 'Internal server error',
              components: ['forecast-card-24h', 'metrics-dashboard']
            }
          }));
        }
      );
    });

    it('should recover from errors and resynchronize components', async () => {
      const forecastData = mockApiResponses.forecast.success('12h');

      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-12h"
            data-error-state="false"
            data-sync-state="loaded"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-error-state="false"
            data-sync-state="loaded"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Trigger error
      MockStateManager.setState('apiError', { type: 'timeout' });
      window.dispatchEvent(new CustomEvent('api-error'));

      // Verify error state
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-12h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-error-state')).toBe('true');
        expect(metricsDashboard.getAttribute('data-error-state')).toBe('true');
      });

      // Trigger recovery
      MockStateManager.setState('apiError', null);
      MockStateManager.setState('recovery', true);
      window.dispatchEvent(new CustomEvent('api-recovery'));

      // Verify recovery and resynchronization
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-12h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-error-state')).toBe('false');
        expect(metricsDashboard.getAttribute('data-error-state')).toBe('false');
        expect(forecastCard.getAttribute('data-sync-state')).toBe('loaded');
        expect(metricsDashboard.getAttribute('data-sync-state')).toBe('loaded');
      });
    });
  });

  describe('API Integration', () => {
    it('should coordinate API calls between components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={mockApiResponses.forecast.success('24h')}
            data-testid="forecast-card-24h"
            data-api-state="loaded"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-api-state="loaded"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      await testApiCallCoordination(
        'forecast-card-24h',
        ['metrics-dashboard'],
        '/api/forecast/24h',
        async () => {
          const refreshButton = screen.getByTitle(/Refresh Data/);
          await user.click(refreshButton);
        }
      );
    });

    it('should handle API response mapping and type safety', async () => {
      const validForecastData = mockApiResponses.forecast.success('6h');
      
      // Verify the forecast data structure matches TypeScript types
      expect(validForecastData).toMatchObject({
        location: expect.any(String),
        horizon: expect.any(String),
        generated_at: expect.any(String),
        variables: expect.objectContaining({
          t2m: expect.objectContaining({
            value: expect.any(Number),
            confidence: expect.any(Number),
            available: expect.any(Boolean)
          })
        }),
        risk_assessment: expect.objectContaining({
          temperature_extreme: expect.stringMatching(/^(minimal|low|moderate|high|extreme)$/),
          precipitation_heavy: expect.stringMatching(/^(minimal|low|moderate|high|extreme)$/),
          wind_strong: expect.stringMatching(/^(minimal|low|moderate|high|extreme)$/),
          thunderstorm: expect.stringMatching(/^(minimal|low|moderate|high|extreme)$/)
        })
      });

      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={validForecastData}
            data-testid="forecast-card-6h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Verify components render correctly with typed data
      await waitFor(() => {
        expect(screen.getByText(/23\.5/)).toBeInTheDocument(); // Temperature value
        expect(screen.getByText(/°C/)).toBeInTheDocument(); // Temperature unit
        expect(screen.getByText(/85%/)).toBeInTheDocument(); // Confidence percentage
      });
    });
  });

  describe('State Management Integration', () => {
    it('should maintain consistent state across component unmount/remount cycles', async () => {
      const forecastData = mockApiResponses.forecast.success('24h');
      const initialState = {
        forecastData,
        lastUpdate: '2024-01-15T10:30:00Z',
        userPreferences: { theme: 'dark', units: 'metric' }
      };

      // Initial render
      const { unmount } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-24h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState 
        }
      );

      // Verify initial state
      expect(MockStateManager.getState('forecastData')).toEqual(forecastData);

      // Unmount components
      unmount();

      // Re-render with same state
      renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-24h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState 
        }
      );

      // Verify state persistence
      await waitFor(() => {
        expect(MockStateManager.getState('forecastData')).toEqual(forecastData);
        expect(MockStateManager.getState('lastUpdate')).toBe('2024-01-15T10:30:00Z');
      });
    });

    it('should synchronize state changes across browser tabs', async () => {
      await integrationTestUtils.testStatePersistence(
        'forecastHorizon',
        '48h',
        'localStorage'
      );

      const { container } = renderWithIntegration(
        <div>
          <ForecastCard 
            forecast={mockApiResponses.forecast.success('48h')}
            data-testid="forecast-card-48h"
            data-forecast-horizon="48h"
          />
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            data-forecast-horizon="48h"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Verify components reflect the persisted state
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-48h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-forecast-horizon')).toBe('48h');
        expect(metricsDashboard.getAttribute('data-forecast-horizon')).toBe('48h');
      });
    });
  });
});