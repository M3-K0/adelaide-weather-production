/**
 * CAPEBadge ↔ StatusBar Integration Tests
 * 
 * Tests real-time status synchronization between CAPEBadge and StatusBar components,
 * including risk level updates, visual state changes, and user interaction coordination.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { CAPEBadge } from '@/components/CAPEBadge';
import { StatusBar } from '@/components/StatusBar';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

const { 
  renderWithIntegration, 
  testRealTimeSynchronization,
  simulateRealTimeUpdate,
  expectComponentsSynchronized,
  measureInteractionPerformance
} = integrationTestUtils;

describe('CAPEBadge ↔ StatusBar Integration', () => {
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
      updateRiskLevel: jest.fn(),
      getMetrics: jest.fn(() => ({
        riskLevels: { cape: 'moderate' }
      }))
    };

    mockAccessibilityProvider = {
      announceToScreenReader: jest.fn(),
      setFocusManagement: jest.fn(),
      getAccessibilityStatus: jest.fn(() => ({
        screenReaderActive: false,
        highContrast: false,
        reducedMotion: false
      }))
    };

    user = userEvent.setup();
    MockStateManager.clearState();
  });

  describe('Risk Level Synchronization', () => {
    it('should synchronize CAPE risk levels between components', async () => {
      const capeValue = 2500; // Extreme level
      const expectedRiskLevel = 'extreme';

      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={capeValue}
            percentile={95}
            season="Summer"
            data-testid="cape-badge"
            data-cape-level={expectedRiskLevel}
            data-sync-state="loaded"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-level={expectedRiskLevel}
            data-risk-status="elevated"
            data-sync-state="loaded"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider,
          initialState: { 
            capeLevel: expectedRiskLevel,
            riskStatus: 'elevated'
          }
        }
      );

      // Verify initial synchronization
      await expectComponentsSynchronized(
        'cape-badge',
        'status-bar',
        'data-cape-level'
      );

      // Verify correct risk level display
      await waitFor(() => {
        expect(screen.getByText('Extreme')).toBeInTheDocument();
        expect(screen.getByText('2,500')).toBeInTheDocument();
      });
    });

    it('should update status bar when CAPE risk level changes', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={800} // Moderate level initially
            data-testid="cape-badge"
            data-cape-level="moderate"
            data-sync-timestamp="2024-01-15T10:30:00Z"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-level="moderate"
            data-risk-status="normal"
            data-sync-timestamp="2024-01-15T10:30:00Z"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate real-time CAPE update to extreme level
      await testRealTimeSynchronization(
        ['cape-badge', 'status-bar'],
        {
          capeValue: 3200,
          riskLevel: 'extreme',
          timestamp: '2024-01-15T10:31:00Z'
        }
      );

      // Verify both components reflect the new risk level
      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-cape-level')).toBe('extreme');
        expect(statusBar.getAttribute('data-cape-level')).toBe('extreme');
        expect(statusBar.getAttribute('data-risk-status')).toBe('critical');
      });
    });

    it('should handle rapid CAPE value fluctuations smoothly', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1000}
            data-testid="cape-badge"
            data-cape-level="moderate"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-level="moderate"
            data-risk-status="normal"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate rapid updates
      const rapidUpdates = [
        { capeValue: 1800, riskLevel: 'high' },
        { capeValue: 2200, riskLevel: 'extreme' },
        { capeValue: 1500, riskLevel: 'high' },
        { capeValue: 900, riskLevel: 'moderate' }
      ];

      for (const update of rapidUpdates) {
        await simulateRealTimeUpdate('cape', update, ['cape-badge', 'status-bar']);
        await new Promise(resolve => setTimeout(resolve, 50)); // Small delay between updates
      }

      // Verify final state synchronization
      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-cape-level')).toBe('moderate');
        expect(statusBar.getAttribute('data-cape-level')).toBe('moderate');
      });
    });
  });

  describe('Visual State Synchronization', () => {
    it('should synchronize visual states during CAPE modal interactions', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1500}
            showInfo={true}
            data-testid="cape-badge"
            data-modal-state="closed"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-focus="false"
            data-modal-state="closed"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const capeBadge = screen.getByTestId('cape-badge');
      
      // Simulate CAPE badge click to open modal
      const interactionTime = await measureInteractionPerformance(
        async () => {
          await user.click(capeBadge);
        },
        300 // Should be fast interaction
      );

      // Verify modal state synchronization
      await waitFor(() => {
        expect(capeBadge.getAttribute('data-modal-state')).toBe('open');
        expect(screen.getByTestId('status-bar').getAttribute('data-cape-focus')).toBe('true');
      });

      // Verify metrics tracking
      expect(mockMetricsProvider.trackCapeModal).toHaveBeenCalledWith(
        expect.any(String) // horizon parameter
      );

      // Verify accessibility announcement
      expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
        expect.stringContaining('CAPE information modal opened')
      );
    });

    it('should maintain visual consistency across different CAPE risk levels', async () => {
      const testCases = [
        { value: 200, level: 'low', color: 'green' },
        { value: 800, level: 'moderate', color: 'yellow' },
        { value: 1500, level: 'high', color: 'orange' },
        { value: 3000, level: 'extreme', color: 'red' }
      ];

      for (const testCase of testCases) {
        const { unmount } = renderWithIntegration(
          <div>
            <CAPEBadge 
              value={testCase.value}
              data-testid="cape-badge"
              data-cape-level={testCase.level}
              data-risk-color={testCase.color}
            />
            <StatusBar 
              data-testid="status-bar"
              data-cape-level={testCase.level}
              data-risk-color={testCase.color}
            />
          </div>,
          { 
            queryClient, 
            metricsProvider: mockMetricsProvider,
            accessibilityProvider: mockAccessibilityProvider
          }
        );

        // Verify color consistency
        await waitFor(() => {
          const capeBadge = screen.getByTestId('cape-badge');
          const statusBar = screen.getByTestId('status-bar');
          
          expect(capeBadge.getAttribute('data-risk-color')).toBe(testCase.color);
          expect(statusBar.getAttribute('data-risk-color')).toBe(testCase.color);
        });

        unmount();
      }
    });
  });

  describe('User Interaction Coordination', () => {
    it('should coordinate keyboard navigation between components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1200}
            showInfo={true}
            data-testid="cape-badge"
          />
          <StatusBar 
            data-testid="status-bar"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const capeBadge = screen.getByTestId('cape-badge');
      
      // Test keyboard navigation
      await user.tab(); // Should focus the CAPE badge
      expect(capeBadge).toHaveFocus();

      // Press Enter to open modal
      await user.keyboard('{Enter}');

      // Verify modal opened and focus management
      await waitFor(() => {
        expect(mockAccessibilityProvider.setFocusManagement).toHaveBeenCalledWith({
          component: 'cape-modal',
          trapFocus: true
        });
      });

      // Press Escape to close modal
      await user.keyboard('{Escape}');

      // Verify focus returns to badge
      await waitFor(() => {
        expect(capeBadge).toHaveFocus();
      });
    });

    it('should handle concurrent interactions gracefully', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1800}
            showInfo={true}
            data-testid="cape-badge"
          />
          <StatusBar 
            data-testid="status-bar"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const capeBadge = screen.getByTestId('cape-badge');
      const statusBar = screen.getByTestId('status-bar');

      // Simulate concurrent interactions
      const concurrentActions = [
        () => user.click(capeBadge), // Open CAPE modal
        () => user.hover(statusBar), // Hover status bar
        () => simulateRealTimeUpdate('cape', { value: 2000 }, ['cape-badge', 'status-bar']) // Real-time update
      ];

      const startTime = performance.now();
      await Promise.all(concurrentActions.map(action => action()));
      const endTime = performance.now();

      // Should handle concurrent actions efficiently
      expect(endTime - startTime).toBeLessThan(500);

      // Verify all interactions were processed
      await waitFor(() => {
        expect(mockMetricsProvider.trackInteraction).toHaveBeenCalled();
        expect(mockMetricsProvider.updateRiskLevel).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility Integration', () => {
    it('should coordinate screen reader announcements for risk level changes', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1000}
            data-testid="cape-badge"
            data-cape-level="moderate"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-level="moderate"
          />
        </div>,
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

      // Simulate risk level change
      await simulateRealTimeUpdate(
        'cape',
        { value: 2500, riskLevel: 'extreme' },
        ['cape-badge', 'status-bar']
      );

      // Verify screen reader announcement
      await waitFor(() => {
        expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
          expect.stringContaining('CAPE risk level changed to extreme')
        );
      });
    });

    it('should maintain accessibility attributes during state changes', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1500}
            data-testid="cape-badge"
            aria-label="CAPE risk level: high, 1500 J/kg"
            role="button"
          />
          <StatusBar 
            data-testid="status-bar"
            aria-live="polite"
            role="status"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Verify initial accessibility attributes
      const capeBadge = screen.getByTestId('cape-badge');
      const statusBar = screen.getByTestId('status-bar');

      expect(capeBadge).toHaveAttribute('aria-label');
      expect(capeBadge).toHaveAttribute('role', 'button');
      expect(statusBar).toHaveAttribute('aria-live', 'polite');
      expect(statusBar).toHaveAttribute('role', 'status');

      // Simulate state change
      await simulateRealTimeUpdate(
        'cape',
        { value: 3000, riskLevel: 'extreme' },
        ['cape-badge', 'status-bar']
      );

      // Verify accessibility attributes are maintained
      await waitFor(() => {
        expect(capeBadge).toHaveAttribute('aria-label');
        expect(capeBadge).toHaveAttribute('role', 'button');
        expect(statusBar).toHaveAttribute('aria-live', 'polite');
        expect(statusBar).toHaveAttribute('role', 'status');
      });
    });

    it('should support high contrast mode across components', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={2000}
            data-testid="cape-badge"
            data-theme="high-contrast"
          />
          <StatusBar 
            data-testid="status-bar"
            data-theme="high-contrast"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              screenReaderActive: false,
              highContrast: true,
              reducedMotion: false
            }))
          }
        }
      );

      // Verify high contrast mode is applied
      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-theme')).toBe('high-contrast');
        expect(statusBar.getAttribute('data-theme')).toBe('high-contrast');
      });
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle CAPE data unavailability gracefully', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={0} // Invalid/unavailable value
            data-testid="cape-badge"
            data-cape-available="false"
            data-error-state="true"
          />
          <StatusBar 
            data-testid="status-bar"
            data-cape-available="false"
            data-error-state="true"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Verify error states are synchronized
      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-cape-available')).toBe('false');
        expect(statusBar.getAttribute('data-cape-available')).toBe('false');
        expect(capeBadge.getAttribute('data-error-state')).toBe('true');
        expect(statusBar.getAttribute('data-error-state')).toBe('true');
      });

      // Simulate data recovery
      await simulateRealTimeUpdate(
        'cape',
        { value: 1200, riskLevel: 'high', available: true },
        ['cape-badge', 'status-bar']
      );

      // Verify recovery synchronization
      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-cape-available')).toBe('true');
        expect(statusBar.getAttribute('data-cape-available')).toBe('true');
        expect(capeBadge.getAttribute('data-error-state')).toBe('false');
        expect(statusBar.getAttribute('data-error-state')).toBe('false');
      });
    });

    it('should maintain synchronization during network interruptions', async () => {
      const { container } = renderWithIntegration(
        <div>
          <CAPEBadge 
            value={1500}
            data-testid="cape-badge"
            data-network-status="online"
          />
          <StatusBar 
            data-testid="status-bar"
            data-network-status="online"
          />
        </div>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate network interruption
      window.dispatchEvent(new CustomEvent('network-offline'));

      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-network-status')).toBe('offline');
        expect(statusBar.getAttribute('data-network-status')).toBe('offline');
      });

      // Simulate network recovery
      window.dispatchEvent(new CustomEvent('network-online'));

      await waitFor(() => {
        const capeBadge = screen.getByTestId('cape-badge');
        const statusBar = screen.getByTestId('status-bar');
        
        expect(capeBadge.getAttribute('data-network-status')).toBe('online');
        expect(statusBar.getAttribute('data-network-status')).toBe('online');
      });
    });
  });
});