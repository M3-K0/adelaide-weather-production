/**
 * AnalogExplorer ↔ ForecastVersions Integration Tests
 * 
 * Tests historical data consistency and synchronization between AnalogExplorer 
 * and ForecastVersions components, including timeline navigation, data validation,
 * and cross-component state management.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { AnalogExplorer } from '@/components/AnalogExplorer';
import { ForecastVersions } from '@/components/ForecastVersions';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

const { 
  renderWithIntegration, 
  testDataFlow,
  expectComponentsSynchronized,
  testCrossComponentState,
  measureInteractionPerformance
} = integrationTestUtils;

describe('AnalogExplorer ↔ ForecastVersions Integration', () => {
  let queryClient: QueryClient;
  let mockMetricsProvider: any;
  let mockAnalogData: any;
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
      trackAnalogSelection: jest.fn(),
      trackTimelineNavigation: jest.fn(),
      trackExport: jest.fn(),
      getMetrics: jest.fn(() => ({
        analogsViewed: 0,
        timelineInteractions: 0
      }))
    };

    mockAnalogData = mockApiResponses.analogs.success();

    user = userEvent.setup();
    MockStateManager.clearState();
  });

  describe('Historical Data Consistency', () => {
    it('should maintain consistent analog data across components', async () => {
      const selectedAnalog = mockAnalogData.top_analogs[0];
      const selectedDate = selectedAnalog.date;

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedDate}
            data-timeline-position="6h"
            data-sync-state="loaded"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedDate}
            data-timeline-position="6h"
            data-sync-state="loaded"
            data-historical-data="available"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: { 
            selectedAnalog: selectedDate,
            analogData: mockAnalogData,
            timelinePosition: '6h'
          }
        }
      );

      // Verify data consistency between components
      await expectComponentsSynchronized(
        'analog-explorer',
        'forecast-versions',
        'data-selected-analog'
      );

      await expectComponentsSynchronized(
        'analog-explorer',
        'forecast-versions',
        'data-timeline-position'
      );

      // Verify historical data is properly displayed
      await waitFor(() => {
        expect(screen.getByText('2023-08-15T12:00:00Z')).toBeInTheDocument();
        expect(screen.getByText(/24\.2/)).toBeInTheDocument(); // Outcome actual
        expect(screen.getByText(/89%/)).toBeInTheDocument(); // Similarity score
      });
    });

    it('should synchronize analog selection across components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog=""
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog=""
            data-historical-data="available"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate analog selection in AnalogExplorer
      await testDataFlow(
        'analog-explorer',
        'forecast-versions',
        async () => {
          // Click on first analog pattern
          const firstAnalog = screen.getByText('2023-08-15T12:00:00Z');
          await user.click(firstAnalog);
        },
        {
          'selected-analog': '2023-08-15T12:00:00Z',
          'timeline-position': '0h'
        }
      );

      // Verify metrics tracking
      expect(mockMetricsProvider.trackAnalogSelection).toHaveBeenCalledWith(
        '2023-08-15T12:00:00Z',
        0.89 // similarity score
      );
    });

    it('should validate historical data integrity during component interactions', async () => {
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-data-integrity="verified"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-data-integrity="verified"
            data-historical-data="available"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Verify data integrity attributes
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-data-integrity')).toBe('verified');
        expect(forecastVersions.getAttribute('data-data-integrity')).toBe('verified');
      });

      // Test data validation during selection
      const analogTimeline = mockAnalogData.top_analogs[0].timeline;
      
      // Verify timeline data consistency
      analogTimeline.forEach((point, index) => {
        expect(point.hours_offset).toBe(index * 6); // 6-hour intervals
        expect(typeof point.t2m).toBe('number');
        expect(typeof point.cape).toBe('number');
      });
    });
  });

  describe('Timeline Navigation Synchronization', () => {
    it('should synchronize timeline position across components', async () => {
      const selectedAnalog = mockAnalogData.top_analogs[0];

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedAnalog.date}
            data-timeline-position="0h"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedAnalog.date}
            data-timeline-position="0h"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate timeline scrubbing in AnalogExplorer
      await testDataFlow(
        'analog-explorer',
        'forecast-versions',
        async () => {
          // Simulate timeline slider interaction
          const timelineSlider = screen.getByRole('slider', { name: /timeline/i });
          await user.click(timelineSlider);
          
          // Move to 12-hour position
          MockStateManager.setState('timelinePosition', '12h');
          window.dispatchEvent(new CustomEvent('timeline-change', {
            detail: { position: '12h', hours_offset: 12 }
          }));
        },
        {
          'timeline-position': '12h'
        }
      );

      // Verify timeline navigation tracking
      expect(mockMetricsProvider.trackTimelineNavigation).toHaveBeenCalledWith(
        selectedAnalog.date,
        12
      );
    });

    it('should maintain timeline state during rapid navigation', async () => {
      const selectedAnalog = mockAnalogData.top_analogs[0];

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedAnalog.date}
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedAnalog.date}
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate rapid timeline navigation
      const timelinePositions = ['6h', '12h', '18h', '24h', '12h', '6h'];
      
      for (const position of timelinePositions) {
        await testCrossComponentState(
          'timelinePosition',
          position,
          ['analog-explorer', 'forecast-versions']
        );
        
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Verify final state consistency
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-timeline-position')).toBe('6h');
        expect(forecastVersions.getAttribute('data-timeline-position')).toBe('6h');
      });
    });

    it('should handle timeline boundaries correctly', async () => {
      const selectedAnalog = mockAnalogData.top_analogs[0];

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedAnalog.date}
            data-timeline-min="0h"
            data-timeline-max="24h"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedAnalog.date}
            data-timeline-min="0h"
            data-timeline-max="24h"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Test boundary conditions
      const boundaryTests = [
        { position: '-6h', expected: '0h' }, // Below minimum
        { position: '30h', expected: '24h' }, // Above maximum
        { position: '0h', expected: '0h' },   // At minimum
        { position: '24h', expected: '24h' }  // At maximum
      ];

      for (const test of boundaryTests) {
        MockStateManager.setState('timelinePosition', test.position);
        window.dispatchEvent(new CustomEvent('timeline-boundary-check', {
          detail: { position: test.position }
        }));

        await waitFor(() => {
          const analogExplorer = screen.getByTestId('analog-explorer');
          const forecastVersions = screen.getByTestId('forecast-versions');
          
          expect(analogExplorer.getAttribute('data-timeline-position')).toBe(test.expected);
          expect(forecastVersions.getAttribute('data-timeline-position')).toBe(test.expected);
        });
      }
    });
  });

  describe('Cross-Component State Management', () => {
    it('should maintain analog selection state during component unmount/remount', async () => {
      const selectedAnalog = mockAnalogData.top_analogs[1];
      const selectedDate = selectedAnalog.date;

      // Initial render with selected analog
      const { unmount } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedDate}
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedDate}
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: { selectedAnalog: selectedDate }
        }
      );

      // Verify initial state
      expect(MockStateManager.getState('selectedAnalog')).toBe(selectedDate);

      // Unmount components
      unmount();

      // Re-render components
      renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={selectedDate}
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={selectedDate}
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          initialState: { selectedAnalog: selectedDate }
        }
      );

      // Verify state persistence
      await waitFor(() => {
        expect(MockStateManager.getState('selectedAnalog')).toBe(selectedDate);
        expect(screen.getByText(selectedDate)).toBeInTheDocument();
      });
    });

    it('should synchronize export functionality across components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-export-available="true"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-export-available="true"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate export action
      const exportButton = screen.getByText(/Export/i);
      
      const exportTime = await measureInteractionPerformance(
        async () => {
          await user.click(exportButton);
        },
        1000 // Export should complete within 1 second
      );

      // Verify export tracking
      expect(mockMetricsProvider.trackExport).toHaveBeenCalledWith(
        expect.objectContaining({
          component: 'analog-explorer',
          dataType: 'analog-patterns'
        })
      );

      // Verify export state synchronization
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-export-state')).toBe('completed');
        expect(forecastVersions.getAttribute('data-export-state')).toBe('completed');
      });
    });

    it('should handle multi-analog selection and comparison', async () => {
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-multi-select="enabled"
            data-selected-analogs="[]"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-multi-select="enabled"
            data-selected-analogs="[]"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      const analogs = mockAnalogData.top_analogs;

      // Select multiple analogs
      for (let i = 0; i < 2; i++) {
        const analogElement = screen.getByText(analogs[i].date);
        await user.click(analogElement, { ctrlKey: true }); // Multi-select with Ctrl
        
        await waitFor(() => {
          const selectedAnalogs = JSON.parse(
            screen.getByTestId('analog-explorer').getAttribute('data-selected-analogs') || '[]'
          );
          expect(selectedAnalogs).toHaveLength(i + 1);
        });
      }

      // Verify both components reflect multi-selection
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        const explorerSelected = JSON.parse(analogExplorer.getAttribute('data-selected-analogs') || '[]');
        const versionsSelected = JSON.parse(forecastVersions.getAttribute('data-selected-analogs') || '[]');
        
        expect(explorerSelected).toHaveLength(2);
        expect(versionsSelected).toHaveLength(2);
        expect(explorerSelected).toEqual(versionsSelected);
      });
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle large analog datasets efficiently', async () => {
      // Create a large dataset
      const largeAnalogData = {
        ...mockAnalogData,
        top_analogs: Array.from({ length: 100 }, (_, i) => ({
          ...mockAnalogData.top_analogs[0],
          date: `2023-${String(i + 1).padStart(2, '0')}-15T12:00:00Z`,
          similarity_score: 0.9 - (i * 0.005)
        }))
      };

      const startTime = performance.now();

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={largeAnalogData}
            data-testid="analog-explorer"
            data-analog-count="100"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-analog-count="100"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      const renderTime = performance.now() - startTime;

      // Rendering should complete within reasonable time even with large dataset
      expect(renderTime).toBeLessThan(2000);

      // Verify components handle large dataset
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        expect(analogExplorer.getAttribute('data-analog-count')).toBe('100');
      });
    });

    it('should optimize timeline scrubbing performance', async () => {
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-selected-analog={mockAnalogData.top_analogs[0].date}
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-selected-analog={mockAnalogData.top_analogs[0].date}
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate rapid timeline scrubbing
      const scrubPositions = Array.from({ length: 20 }, (_, i) => `${i}h`);
      
      const scrubStartTime = performance.now();
      
      for (const position of scrubPositions) {
        MockStateManager.setState('timelinePosition', position);
        window.dispatchEvent(new CustomEvent('timeline-scrub', {
          detail: { position }
        }));
        
        // Small delay to simulate real scrubbing
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      const scrubEndTime = performance.now();
      const totalScrubTime = scrubEndTime - scrubStartTime;
      
      // Scrubbing should be smooth and responsive
      expect(totalScrubTime).toBeLessThan(1000);
      
      // Verify final state consistency
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-timeline-position')).toBe('19h');
        expect(forecastVersions.getAttribute('data-timeline-position')).toBe('19h');
      });
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle missing analog data gracefully', async () => {
      const emptyAnalogData = mockApiResponses.analogs.noAnalogs();

      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={emptyAnalogData}
            data-testid="analog-explorer"
            data-analog-count="0"
            data-error-state="false"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-analog-count="0"
            data-error-state="false"
            data-historical-data="unavailable"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Verify components handle empty data gracefully
      await waitFor(() => {
        expect(screen.getByText(/No analog patterns found/i)).toBeInTheDocument();
        
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-analog-count')).toBe('0');
        expect(forecastVersions.getAttribute('data-analog-count')).toBe('0');
        expect(forecastVersions.getAttribute('data-historical-data')).toBe('unavailable');
      });
    });

    it('should recover from analog data corruption', async () => {
      // Start with valid data
      const { container } = renderWithIntegration(
        <div>
          <AnalogExplorer 
            data={mockAnalogData}
            data-testid="analog-explorer"
            data-data-integrity="verified"
          />
          <ForecastVersions 
            data-testid="forecast-versions"
            data-data-integrity="verified"
          />
        </div>,
        { queryClient, metricsProvider: mockMetricsProvider }
      );

      // Simulate data corruption
      const corruptedData = {
        ...mockAnalogData,
        top_analogs: [
          {
            ...mockAnalogData.top_analogs[0],
            timeline: null // Corrupted timeline data
          }
        ]
      };

      MockStateManager.setState('analogData', corruptedData);
      window.dispatchEvent(new CustomEvent('analog-data-update', {
        detail: { data: corruptedData }
      }));

      // Verify error detection
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-data-integrity')).toBe('corrupted');
        expect(forecastVersions.getAttribute('data-data-integrity')).toBe('corrupted');
      });

      // Simulate data recovery
      MockStateManager.setState('analogData', mockAnalogData);
      window.dispatchEvent(new CustomEvent('analog-data-recovery', {
        detail: { data: mockAnalogData }
      }));

      // Verify recovery
      await waitFor(() => {
        const analogExplorer = screen.getByTestId('analog-explorer');
        const forecastVersions = screen.getByTestId('forecast-versions');
        
        expect(analogExplorer.getAttribute('data-data-integrity')).toBe('verified');
        expect(forecastVersions.getAttribute('data-data-integrity')).toBe('verified');
      });
    });
  });
});