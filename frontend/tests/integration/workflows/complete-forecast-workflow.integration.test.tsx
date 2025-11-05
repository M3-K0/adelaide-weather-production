/**
 * Complete Forecast Workflow Integration Tests
 * 
 * Tests end-to-end workflows involving multiple components working together,
 * including complete user journeys, data flow orchestration, and system-wide integrations.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

// Import all components for full workflow testing
import { ForecastCard } from '@/components/ForecastCard';
import MetricsDashboard from '@/components/MetricsDashboard';
import { CAPEBadge } from '@/components/CAPEBadge';
import { StatusBar } from '@/components/StatusBar';
import { AnalogExplorer } from '@/components/AnalogExplorer';
import { ForecastVersions } from '@/components/ForecastVersions';
import { AccessibilityProvider } from '@/components/AccessibilityProvider';

const { 
  renderWithIntegration, 
  testDataFlow,
  measureInteractionPerformance,
  testApiCallCoordination,
  testRealTimeSynchronization
} = integrationTestUtils;

// Full Application Wrapper for workflow testing
const WeatherForecastApp: React.FC<{
  forecastData?: any;
  metricsData?: any;
  analogData?: any;
}> = ({ 
  forecastData = mockApiResponses.forecast.success('24h'),
  metricsData = mockApiResponses.metrics.success(),
  analogData = mockApiResponses.analogs.success()
}) => (
  <AccessibilityProvider data-testid="app-a11y-provider">
    <div className="weather-forecast-app" data-testid="weather-app">
      <header data-testid="app-header">
        <StatusBar data-testid="status-bar" />
      </header>
      
      <main data-testid="app-main">
        <div className="forecast-section" data-testid="forecast-section">
          <ForecastCard 
            forecast={forecastData}
            data-testid="forecast-card-6h"
            className="forecast-6h"
          />
          <ForecastCard 
            forecast={{...forecastData, horizon: '12h'}}
            data-testid="forecast-card-12h"
            className="forecast-12h"
          />
          <ForecastCard 
            forecast={{...forecastData, horizon: '24h'}}
            data-testid="forecast-card-24h"
            className="forecast-24h"
          />
        </div>

        <div className="analytics-section" data-testid="analytics-section">
          <MetricsDashboard 
            data-testid="metrics-dashboard"
            autoRefresh={true}
            refreshInterval={30}
          />
          
          <AnalogExplorer 
            data={analogData}
            data-testid="analog-explorer"
          />
          
          <ForecastVersions 
            data-testid="forecast-versions"
          />
        </div>
      </main>
    </div>
  </AccessibilityProvider>
);

describe('Complete Forecast Workflow Integration', () => {
  let queryClient: QueryClient;
  let mockMetricsProvider: any;
  let mockAccessibilityProvider: any;
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
      trackAnalogSelection: jest.fn(),
      trackExport: jest.fn(),
      trackWorkflowStep: jest.fn(),
      trackWorkflowCompletion: jest.fn(),
      getMetrics: jest.fn(() => ({
        workflowsCompleted: 0,
        userJourneyStage: 'initial'
      }))
    };

    mockAccessibilityProvider = {
      announceToScreenReader: jest.fn(),
      setFocusManagement: jest.fn(),
      updateLiveRegion: jest.fn(),
      getAccessibilityStatus: jest.fn(() => ({
        screenReaderActive: false,
        highContrast: false,
        reducedMotion: false
      }))
    };

    user = userEvent.setup();
    MockStateManager.clearState();
  });

  describe('Complete User Journey Workflows', () => {
    it('should handle complete forecast exploration workflow', async () => {
      const workflowSteps = integrationData.workflow_scenarios.complete_forecast_workflow.steps;
      
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider,
          initialState: {
            workflowStage: 'initial',
            userJourney: 'forecast_exploration'
          }
        }
      );

      // Step 1: Load dashboard and verify all components are present
      await waitFor(() => {
        expect(screen.getByTestId('metrics-dashboard')).toBeInTheDocument();
        expect(screen.getByTestId('status-bar')).toBeInTheDocument();
        expect(screen.getByTestId('forecast-card-24h')).toBeInTheDocument();
      });

      mockMetricsProvider.trackWorkflowStep('dashboard_loaded', 1);

      // Step 2: Select specific forecast horizon
      const forecast24h = screen.getByTestId('forecast-card-24h');
      
      const horizonSelectionTime = await measureInteractionPerformance(
        async () => {
          await user.click(forecast24h);
        },
        500
      );

      await waitFor(() => {
        expect(forecast24h.getAttribute('data-selected')).toBe('true');
      });

      mockMetricsProvider.trackWorkflowStep('horizon_selected', 2);

      // Step 3: View CAPE details and risk assessment
      const capeValue = screen.getByText(/1250 J\/kg/);
      await user.click(capeValue);

      // Verify CAPE modal opens
      await waitFor(() => {
        expect(screen.getByText(/CAPE Scale Reference/)).toBeInTheDocument();
      });

      mockMetricsProvider.trackWorkflowStep('cape_details_viewed', 3);

      // Step 4: Explore analog patterns
      await user.keyboard('{Escape}'); // Close CAPE modal
      
      const analogExplorer = screen.getByTestId('analog-explorer');
      await user.click(analogExplorer);

      const firstAnalog = screen.getByText('2023-08-15T12:00:00Z');
      await user.click(firstAnalog);

      await waitFor(() => {
        expect(screen.getByText(/89%/)).toBeInTheDocument(); // Similarity score
      });

      mockMetricsProvider.trackWorkflowStep('analogs_explored', 4);

      // Step 5: Export forecast data
      const exportButton = screen.getByText(/Export/);
      await user.click(exportButton);

      mockMetricsProvider.trackWorkflowStep('data_exported', 5);
      mockMetricsProvider.trackWorkflowCompletion('forecast_exploration', 5);

      // Verify complete workflow tracking
      expect(mockMetricsProvider.trackWorkflowStep).toHaveBeenCalledTimes(5);
      expect(mockMetricsProvider.trackWorkflowCompletion).toHaveBeenCalledWith(
        'forecast_exploration',
        5
      );
    });

    it('should handle error recovery workflow gracefully', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Step 1: Trigger API error
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { 
          type: 'timeout',
          message: 'Request timeout',
          components: ['forecast-card-24h', 'metrics-dashboard']
        }
      }));

      // Step 2: Verify error display across components
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-24h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-error-state')).toBe('true');
        expect(metricsDashboard.getAttribute('data-error-state')).toBe('true');
      });

      mockMetricsProvider.trackWorkflowStep('error_detected', 1);

      // Step 3: User attempts retry
      const retryButton = screen.getByText(/Retry/);
      await user.click(retryButton);

      mockMetricsProvider.trackWorkflowStep('retry_attempted', 2);

      // Step 4: Simulate successful recovery
      window.dispatchEvent(new CustomEvent('api-recovery', {
        detail: { 
          type: 'success',
          components: ['forecast-card-24h', 'metrics-dashboard']
        }
      }));

      // Step 5: Verify normal operation restored
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-24h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        
        expect(forecastCard.getAttribute('data-error-state')).toBe('false');
        expect(metricsDashboard.getAttribute('data-error-state')).toBe('false');
      });

      mockMetricsProvider.trackWorkflowStep('recovery_successful', 3);
      mockMetricsProvider.trackWorkflowCompletion('error_recovery', 3);

      // Verify error recovery workflow was tracked
      expect(mockMetricsProvider.trackWorkflowCompletion).toHaveBeenCalledWith(
        'error_recovery',
        3
      );
    });

    it('should handle accessibility-focused workflow', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              screenReaderActive: true,
              highContrast: false,
              reducedMotion: false
            }))
          }
        }
      );

      // Step 1: Enable screen reader mode
      MockStateManager.setState('accessibilityMode', 'screen_reader');
      window.dispatchEvent(new CustomEvent('a11y-mode-change', {
        detail: { mode: 'screen_reader', enabled: true }
      }));

      mockMetricsProvider.trackWorkflowStep('screen_reader_enabled', 1);

      // Step 2: Navigate with keyboard only
      await user.tab(); // Focus first interactive element
      await user.tab(); // Navigate to next element
      await user.tab(); // Continue navigation

      const focusedElement = document.activeElement;
      expect(focusedElement).toHaveAttribute('tabindex');

      mockMetricsProvider.trackWorkflowStep('keyboard_navigation', 2);

      // Step 3: Verify ARIA labels and roles
      const forecastCard = screen.getByTestId('forecast-card-24h');
      expect(forecastCard).toHaveAttribute('aria-label');
      expect(forecastCard).toHaveAttribute('role');

      mockMetricsProvider.trackWorkflowStep('aria_verified', 3);

      // Step 4: Test live region announcements
      window.dispatchEvent(new CustomEvent('forecast-update', {
        detail: { message: 'Forecast updated with new data' }
      }));

      expect(mockAccessibilityProvider.updateLiveRegion).toHaveBeenCalledWith(
        expect.stringContaining('Forecast updated')
      );

      mockMetricsProvider.trackWorkflowStep('live_regions_tested', 4);
      mockMetricsProvider.trackWorkflowCompletion('accessibility_workflow', 4);
    });
  });

  describe('Multi-Component Data Flow Orchestration', () => {
    it('should orchestrate data flow across all components simultaneously', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate simultaneous data updates to multiple components
      const updateData = {
        forecast: mockApiResponses.forecast.success('6h'),
        metrics: mockApiResponses.metrics.success(),
        analogs: mockApiResponses.analogs.success(),
        timestamp: new Date().toISOString()
      };

      // Trigger coordinated update
      await testRealTimeSynchronization(
        [
          'forecast-card-6h',
          'forecast-card-12h', 
          'forecast-card-24h',
          'metrics-dashboard',
          'analog-explorer',
          'status-bar'
        ],
        updateData
      );

      // Verify all components received the update
      await waitFor(() => {
        const components = [
          'forecast-card-6h',
          'metrics-dashboard',
          'analog-explorer',
          'status-bar'
        ];

        components.forEach(componentId => {
          const component = screen.getByTestId(componentId);
          expect(component.getAttribute('data-last-update')).toBeTruthy();
        });
      });
    });

    it('should maintain data consistency during rapid updates', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate rapid sequential updates
      const rapidUpdates = Array.from({ length: 10 }, (_, i) => ({
        sequence: i,
        temperature: 20 + i,
        cape: 1000 + (i * 100),
        timestamp: new Date(Date.now() + i * 1000).toISOString()
      }));

      for (const update of rapidUpdates) {
        MockStateManager.setState('rapidUpdate', update);
        window.dispatchEvent(new CustomEvent('rapid-update', {
          detail: update
        }));
        
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Verify final state consistency across components
      await waitFor(() => {
        const forecastCard = screen.getByTestId('forecast-card-24h');
        const metricsDashboard = screen.getByTestId('metrics-dashboard');
        const statusBar = screen.getByTestId('status-bar');

        const finalUpdate = rapidUpdates[rapidUpdates.length - 1];
        
        expect(forecastCard.getAttribute('data-sequence')).toBe(String(finalUpdate.sequence));
        expect(metricsDashboard.getAttribute('data-sequence')).toBe(String(finalUpdate.sequence));
        expect(statusBar.getAttribute('data-sequence')).toBe(String(finalUpdate.sequence));
      });
    });

    it('should handle cross-component API call coordination', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Test coordinated API calls triggered by user interaction
      await testApiCallCoordination(
        'forecast-card-24h',
        ['metrics-dashboard', 'analog-explorer', 'status-bar'],
        '/api/forecast/24h',
        async () => {
          const refreshAllButton = screen.getByTitle(/Refresh Data/);
          await user.click(refreshAllButton);
        }
      );

      // Verify all dependent components were updated
      await waitFor(() => {
        expect(mockMetricsProvider.trackInteraction).toHaveBeenCalledWith(
          'refresh_all',
          'workflow',
          'coordinated_update'
        );
      });
    });
  });

  describe('Performance Under Load', () => {
    it('should maintain performance with all components active', async () => {
      const startTime = performance.now();

      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const renderTime = performance.now() - startTime;

      // Full app should render within reasonable time
      expect(renderTime).toBeLessThan(2000);

      // Test performance under interaction load
      const interactions = [
        () => user.click(screen.getByTestId('forecast-card-6h')),
        () => user.click(screen.getByTestId('forecast-card-12h')),
        () => user.click(screen.getByTestId('forecast-card-24h')),
        () => {
          const capeElement = screen.getByText(/1250 J\/kg/);
          return user.click(capeElement);
        },
        () => user.keyboard('{Escape}')
      ];

      const interactionStartTime = performance.now();
      
      for (const interaction of interactions) {
        await interaction();
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      const interactionTime = performance.now() - interactionStartTime;

      // All interactions should complete efficiently
      expect(interactionTime).toBeLessThan(3000);
    });

    it('should handle memory efficiently during extended usage', async () => {
      const { unmount } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate extended usage with multiple component interactions
      for (let i = 0; i < 50; i++) {
        // Trigger various component updates
        MockStateManager.setState(`update_${i}`, {
          iteration: i,
          timestamp: new Date().toISOString()
        });

        window.dispatchEvent(new CustomEvent('memory-test-update', {
          detail: { iteration: i }
        }));

        if (i % 10 === 0) {
          // Periodic cleanup simulation
          MockStateManager.clearState();
        }
      }

      // Clean unmount
      unmount();

      // Verify no major memory leaks (simplified check)
      const finalState = MockStateManager.getAllState();
      expect(Object.keys(finalState)).toHaveLength(0);
    });
  });

  describe('Real-World Usage Scenarios', () => {
    it('should handle meteorologist daily workflow', async () => {
      const { container } = renderWithIntegration(
        <WeatherForecastApp />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider,
          initialState: {
            userRole: 'meteorologist',
            workflowType: 'daily_forecast_analysis'
          }
        }
      );

      // Morning forecast review workflow
      const workflowSteps = [
        {
          name: 'review_overnight_updates',
          action: async () => {
            const metricsDashboard = screen.getByTestId('metrics-dashboard');
            await user.click(metricsDashboard);
          }
        },
        {
          name: 'analyze_forecast_accuracy',
          action: async () => {
            const accuracyChart = screen.getByText(/Average Accuracy/);
            await user.click(accuracyChart);
          }
        },
        {
          name: 'review_cape_patterns',
          action: async () => {
            const capeIndicator = screen.getByText(/1250 J\/kg/);
            await user.click(capeIndicator);
            await user.keyboard('{Escape}');
          }
        },
        {
          name: 'examine_analog_patterns',
          action: async () => {
            const analogExplorer = screen.getByTestId('analog-explorer');
            await user.click(analogExplorer);
            
            const firstAnalog = screen.getByText('2023-08-15T12:00:00Z');
            await user.click(firstAnalog);
          }
        },
        {
          name: 'export_analysis_report',
          action: async () => {
            const exportButton = screen.getByText(/Export/);
            await user.click(exportButton);
          }
        }
      ];

      // Execute meteorologist workflow
      for (const step of workflowSteps) {
        const stepStartTime = performance.now();
        await step.action();
        const stepTime = performance.now() - stepStartTime;

        // Each step should be responsive
        expect(stepTime).toBeLessThan(1000);
        
        mockMetricsProvider.trackWorkflowStep(step.name, workflowSteps.indexOf(step) + 1);
      }

      mockMetricsProvider.trackWorkflowCompletion('meteorologist_daily_workflow', workflowSteps.length);

      // Verify professional workflow completion
      expect(mockMetricsProvider.trackWorkflowCompletion).toHaveBeenCalledWith(
        'meteorologist_daily_workflow',
        5
      );
    });

    it('should handle emergency weather monitoring workflow', async () => {
      // Simulate severe weather scenario
      const severeWeatherData = {
        ...mockApiResponses.forecast.success('6h'),
        variables: {
          ...mockApiResponses.forecast.success('6h').variables,
          cape: { value: 3500, confidence: 0.92, available: true }, // Extreme CAPE
          t2m: { value: 45.2, confidence: 0.88, available: true }  // Extreme temperature
        },
        risk_assessment: {
          temperature_extreme: 'extreme',
          precipitation_heavy: 'high',
          wind_strong: 'extreme',
          thunderstorm: 'extreme'
        }
      };

      const { container } = renderWithIntegration(
        <WeatherForecastApp 
          forecastData={severeWeatherData}
        />,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider,
          initialState: {
            emergencyMode: true,
            alertLevel: 'severe'
          }
        }
      );

      // Verify emergency UI state
      await waitFor(() => {
        expect(screen.getByText('Extreme')).toBeInTheDocument();
        expect(screen.getByText('3,500')).toBeInTheDocument(); // CAPE value
      });

      // Emergency workflow: rapid assessment
      const emergencySteps = [
        'verify_extreme_conditions',
        'check_confidence_levels', 
        'review_historical_analogs',
        'export_emergency_briefing'
      ];

      const emergencyWorkflowTime = await measureInteractionPerformance(
        async () => {
          // Rapid assessment workflow
          const capeIndicator = screen.getByText(/Extreme/);
          await user.click(capeIndicator);
          await user.keyboard('{Escape}');
          
          const analogExplorer = screen.getByTestId('analog-explorer');
          await user.click(analogExplorer);
          
          const exportButton = screen.getByText(/Export/);
          await user.click(exportButton);
        },
        5000 // Emergency workflow should be very fast
      );

      expect(emergencyWorkflowTime).toBeLessThan(3000);

      mockMetricsProvider.trackWorkflowCompletion('emergency_weather_monitoring', 4);
    });
  });
});