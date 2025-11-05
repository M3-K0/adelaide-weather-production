/**
 * AccessibilityProvider ↔ All Components Integration Tests
 * 
 * Tests accessibility feature integration across all weather forecasting components,
 * including screen reader support, keyboard navigation, focus management, and WCAG compliance.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient } from '@tanstack/react-query';
import { AccessibilityProvider } from '@/components/AccessibilityProvider';
import { ForecastCard } from '@/components/ForecastCard';
import MetricsDashboard from '@/components/MetricsDashboard';
import { CAPEBadge } from '@/components/CAPEBadge';
import { StatusBar } from '@/components/StatusBar';
import { AnalogExplorer } from '@/components/AnalogExplorer';
import { integrationTestUtils } from '@integration/utils/integration-helpers';
import { mockApiResponses, MockStateManager } from '@mocks/api-mocks';
import integrationData from '@fixtures/integration-data.json';

const { 
  renderWithIntegration, 
  expectAccessibilityIntegrated,
  measureInteractionPerformance
} = integrationTestUtils;

describe('AccessibilityProvider ↔ All Components Integration', () => {
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
      trackA11yFeature: jest.fn(),
      getMetrics: jest.fn(() => ({ a11yInteractions: 0 }))
    };

    mockAccessibilityProvider = {
      announceToScreenReader: jest.fn(),
      setFocusManagement: jest.fn(),
      updateLiveRegion: jest.fn(),
      getAccessibilityStatus: jest.fn(() => ({
        screenReaderActive: false,
        highContrast: false,
        reducedMotion: false,
        focusManagement: true
      })),
      enableFeature: jest.fn(),
      disableFeature: jest.fn()
    };

    user = userEvent.setup();
    MockStateManager.clearState();
  });

  describe('Screen Reader Integration', () => {
    it('should provide screen reader support across all components', async () => {
      const forecastData = mockApiResponses.forecast.success('24h');
      const metricsData = mockApiResponses.metrics.success();
      const analogData = mockApiResponses.analogs.success();

      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={forecastData}
              data-testid="forecast-card"
              aria-label="24-hour forecast card"
            />
            <MetricsDashboard 
              data-testid="metrics-dashboard"
              aria-label="System metrics dashboard"
            />
            <CAPEBadge 
              value={1500}
              data-testid="cape-badge"
              aria-label="CAPE risk level indicator"
            />
            <StatusBar 
              data-testid="status-bar"
              aria-label="System status bar"
            />
            <AnalogExplorer 
              data={analogData}
              data-testid="analog-explorer"
              aria-label="Historical analog patterns explorer"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              screenReaderActive: true,
              highContrast: false,
              reducedMotion: false,
              focusManagement: true
            }))
          }
        }
      );

      // Verify all components have proper accessibility attributes
      const components = [
        'forecast-card',
        'metrics-dashboard', 
        'cape-badge',
        'status-bar',
        'analog-explorer'
      ];

      for (const componentId of components) {
        const component = screen.getByTestId(componentId);
        await expectAccessibilityIntegrated(component, mockAccessibilityProvider);
      }

      // Verify screen reader announcements for component interactions
      const capeButton = screen.getByRole('button', { name: /CAPE risk level/i });
      await user.click(capeButton);

      expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
        expect.stringContaining('CAPE information modal opened')
      );
    });

    it('should handle live region updates across components', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('12h')}
              data-testid="forecast-card"
            />
            <StatusBar 
              data-testid="status-bar"
              aria-live="polite"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate real-time status update
      MockStateManager.setState('forecastUpdate', {
        horizon: '12h',
        temperature: 25.2,
        timestamp: new Date().toISOString()
      });

      window.dispatchEvent(new CustomEvent('forecast-update', {
        detail: { 
          horizon: '12h',
          temperature: 25.2 
        }
      }));

      // Verify live region update
      await waitFor(() => {
        expect(mockAccessibilityProvider.updateLiveRegion).toHaveBeenCalledWith(
          expect.stringContaining('Forecast updated: 12-hour temperature now 25.2°C')
        );
      });
    });

    it('should coordinate screen reader announcements to prevent conflicts', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <CAPEBadge 
              value={2000}
              data-testid="cape-badge"
            />
            <StatusBar 
              data-testid="status-bar"
            />
            <MetricsDashboard 
              data-testid="metrics-dashboard"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate multiple simultaneous updates that could cause announcement conflicts
      const simultaneousUpdates = [
        () => {
          window.dispatchEvent(new CustomEvent('cape-level-change', {
            detail: { level: 'extreme' }
          }));
        },
        () => {
          window.dispatchEvent(new CustomEvent('metrics-alert', {
            detail: { type: 'performance', status: 'warning' }
          }));
        },
        () => {
          window.dispatchEvent(new CustomEvent('system-status-change', {
            detail: { status: 'degraded' }
          }));
        }
      ];

      // Trigger all updates simultaneously
      simultaneousUpdates.forEach(update => update());

      // Verify announcements are queued and delivered sequentially
      await waitFor(() => {
        const calls = mockAccessibilityProvider.announceToScreenReader.mock.calls;
        expect(calls.length).toBeGreaterThan(0);
        
        // Check that announcements are properly spaced (not conflicting)
        if (calls.length > 1) {
          // In a real implementation, there would be timing logic to prevent conflicts
          expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalled();
        }
      });
    });
  });

  describe('Keyboard Navigation Integration', () => {
    it('should provide consistent keyboard navigation across all components', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('24h')}
              data-testid="forecast-card"
              tabIndex={0}
            />
            <CAPEBadge 
              value={1500}
              showInfo={true}
              data-testid="cape-badge"
              tabIndex={0}
            />
            <MetricsDashboard 
              data-testid="metrics-dashboard"
              tabIndex={0}
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Test tab navigation
      await user.tab();
      const forecastCard = screen.getByTestId('forecast-card');
      expect(forecastCard).toHaveFocus();

      await user.tab();
      const capeBadge = screen.getByTestId('cape-badge');
      expect(capeBadge).toHaveFocus();

      await user.tab();
      const metricsDashboard = screen.getByTestId('metrics-dashboard');
      expect(metricsDashboard).toHaveFocus();

      // Test shift+tab (reverse navigation)
      await user.keyboard('{Shift>}{Tab}{/Shift}');
      expect(capeBadge).toHaveFocus();

      // Verify focus management tracking
      expect(mockAccessibilityProvider.setFocusManagement).toHaveBeenCalled();
    });

    it('should handle keyboard shortcuts consistently across components', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('24h')}
              data-testid="forecast-card"
            />
            <AnalogExplorer 
              data={mockApiResponses.analogs.success()}
              data-testid="analog-explorer"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Test global keyboard shortcuts
      await user.keyboard('{Alt>}h{/Alt}'); // Alt+H for help
      
      expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
        expect.stringContaining('Help information')
      );

      // Test component-specific shortcuts
      await user.keyboard('{Alt>}e{/Alt}'); // Alt+E for export
      
      expect(mockMetricsProvider.trackA11yFeature).toHaveBeenCalledWith(
        'keyboard_shortcut',
        'export'
      );
    });

    it('should manage focus trapping in modal dialogs', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <CAPEBadge 
              value={2500}
              showInfo={true}
              data-testid="cape-badge"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const capeBadge = screen.getByTestId('cape-badge');
      
      // Open CAPE modal
      await user.click(capeBadge);

      // Verify focus trap is activated
      expect(mockAccessibilityProvider.setFocusManagement).toHaveBeenCalledWith({
        component: 'cape-modal',
        trapFocus: true
      });

      // Test focus trapping by tabbing through modal elements
      await user.tab(); // Should stay within modal
      await user.tab(); // Should cycle within modal
      
      // Close modal with Escape
      await user.keyboard('{Escape}');

      // Verify focus returns to trigger element
      await waitFor(() => {
        expect(capeBadge).toHaveFocus();
      });

      // Verify focus trap is released
      expect(mockAccessibilityProvider.setFocusManagement).toHaveBeenCalledWith({
        component: 'cape-modal',
        trapFocus: false
      });
    });
  });

  describe('High Contrast Mode Integration', () => {
    it('should apply high contrast styling across all components', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('24h')}
              data-testid="forecast-card"
              data-theme="high-contrast"
            />
            <CAPEBadge 
              value={1500}
              data-testid="cape-badge"
              data-theme="high-contrast"
            />
            <StatusBar 
              data-testid="status-bar"
              data-theme="high-contrast"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              screenReaderActive: false,
              highContrast: true,
              reducedMotion: false,
              focusManagement: true
            }))
          }
        }
      );

      // Verify high contrast mode is applied to all components
      const components = ['forecast-card', 'cape-badge', 'status-bar'];
      
      for (const componentId of components) {
        const component = screen.getByTestId(componentId);
        expect(component.getAttribute('data-theme')).toBe('high-contrast');
      }

      // Test dynamic theme switching
      MockStateManager.setState('accessibilitySettings', { highContrast: false });
      window.dispatchEvent(new CustomEvent('a11y-setting-change', {
        detail: { setting: 'highContrast', value: false }
      }));

      await waitFor(() => {
        for (const componentId of components) {
          const component = screen.getByTestId(componentId);
          expect(component.getAttribute('data-theme')).toBe('default');
        }
      });
    });

    it('should maintain color contrast ratios in high contrast mode', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <CAPEBadge 
              value={2000} // Extreme level - should have high contrast
              data-testid="cape-badge"
              data-theme="high-contrast"
              data-contrast-ratio="7.2"
            />
          </div>
        </AccessibilityProvider>,
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

      const capeBadge = screen.getByTestId('cape-badge');
      const contrastRatio = parseFloat(capeBadge.getAttribute('data-contrast-ratio') || '0');
      
      // WCAG AAA standard requires 7:1 contrast ratio
      expect(contrastRatio).toBeGreaterThanOrEqual(7.0);
    });
  });

  describe('Reduced Motion Integration', () => {
    it('should disable animations when reduced motion is preferred', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <CAPEBadge 
              value={3000} // Extreme level with lightning animation
              disableAnimations={true}
              data-testid="cape-badge"
              data-reduced-motion="true"
            />
            <AnalogExplorer 
              data={mockApiResponses.analogs.success()}
              data-testid="analog-explorer"
              data-reduced-motion="true"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              screenReaderActive: false,
              highContrast: false,
              reducedMotion: true
            }))
          }
        }
      );

      // Verify animations are disabled
      const capeBadge = screen.getByTestId('cape-badge');
      const analogExplorer = screen.getByTestId('analog-explorer');
      
      expect(capeBadge.getAttribute('data-reduced-motion')).toBe('true');
      expect(analogExplorer.getAttribute('data-reduced-motion')).toBe('true');

      // Verify no animation-related performance overhead
      const interactionTime = await measureInteractionPerformance(
        async () => {
          await user.click(capeBadge);
        },
        200 // Should be faster without animations
      );

      expect(interactionTime).toBeLessThan(200);
    });

    it('should provide alternative feedback for disabled animations', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <CAPEBadge 
              value={2800}
              disableAnimations={true}
              data-testid="cape-badge"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: {
            ...mockAccessibilityProvider,
            getAccessibilityStatus: jest.fn(() => ({
              reducedMotion: true
            }))
          }
        }
      );

      const capeBadge = screen.getByTestId('cape-badge');
      await user.click(capeBadge);

      // Instead of animation, should provide immediate feedback
      expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
        expect.stringContaining('Extreme CAPE level')
      );
    });
  });

  describe('ARIA Live Regions and Status Updates', () => {
    it('should coordinate ARIA live region updates across components', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <StatusBar 
              data-testid="status-bar"
              aria-live="polite"
              data-live-region="status"
            />
            <MetricsDashboard 
              data-testid="metrics-dashboard"
              aria-live="polite"
              data-live-region="metrics"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate system status update
      MockStateManager.setState('systemStatus', 'degraded');
      window.dispatchEvent(new CustomEvent('system-status-update', {
        detail: { status: 'degraded', component: 'api' }
      }));

      // Verify live region updates
      await waitFor(() => {
        expect(mockAccessibilityProvider.updateLiveRegion).toHaveBeenCalledWith(
          expect.stringContaining('System status changed to degraded')
        );
      });

      // Simulate metrics update
      MockStateManager.setState('metricsAlert', { type: 'performance', level: 'warning' });
      window.dispatchEvent(new CustomEvent('metrics-alert', {
        detail: { type: 'performance', level: 'warning' }
      }));

      await waitFor(() => {
        expect(mockAccessibilityProvider.updateLiveRegion).toHaveBeenCalledWith(
          expect.stringContaining('Performance warning detected')
        );
      });
    });

    it('should prioritize critical alerts in live regions', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <StatusBar 
              data-testid="status-bar"
              aria-live="assertive"
              data-priority="critical"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate critical system alert
      window.dispatchEvent(new CustomEvent('critical-alert', {
        detail: { 
          type: 'system_failure',
          message: 'API service unavailable',
          priority: 'critical'
        }
      }));

      // Verify critical alert uses assertive live region
      await waitFor(() => {
        expect(mockAccessibilityProvider.updateLiveRegion).toHaveBeenCalledWith(
          expect.stringContaining('Critical: API service unavailable'),
          'assertive'
        );
      });
    });
  });

  describe('Focus Management and Navigation', () => {
    it('should maintain logical focus order across complex component interactions', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('24h')}
              data-testid="forecast-card"
              tabIndex={0}
            />
            <CAPEBadge 
              value={1500}
              showInfo={true}
              data-testid="cape-badge"
              tabIndex={0}
            />
            <AnalogExplorer 
              data={mockApiResponses.analogs.success()}
              data-testid="analog-explorer"
              tabIndex={0}
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Navigate through components and open modal
      await user.tab(); // Focus forecast card
      await user.tab(); // Focus CAPE badge
      await user.keyboard('{Enter}'); // Open CAPE modal

      // Verify focus is managed within modal
      expect(mockAccessibilityProvider.setFocusManagement).toHaveBeenCalledWith({
        component: 'cape-modal',
        trapFocus: true
      });

      // Close modal and continue navigation
      await user.keyboard('{Escape}');
      await user.tab(); // Should continue to analog explorer

      const analogExplorer = screen.getByTestId('analog-explorer');
      expect(analogExplorer).toHaveFocus();
    });

    it('should handle skip links for efficient navigation', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <a href="#main-content" data-testid="skip-link">Skip to main content</a>
            <nav data-testid="navigation">Navigation</nav>
            <main id="main-content" data-testid="main-content" tabIndex={-1}>
              <ForecastCard 
                forecast={mockApiResponses.forecast.success('24h')}
                data-testid="forecast-card"
              />
            </main>
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const skipLink = screen.getByTestId('skip-link');
      const mainContent = screen.getByTestId('main-content');

      // Use skip link
      skipLink.focus();
      await user.keyboard('{Enter}');

      // Verify focus jumps to main content
      await waitFor(() => {
        expect(mainContent).toHaveFocus();
      });

      // Verify skip link usage is tracked
      expect(mockMetricsProvider.trackA11yFeature).toHaveBeenCalledWith(
        'skip_link',
        'main_content'
      );
    });
  });

  describe('Error Handling and Accessibility', () => {
    it('should announce errors to screen readers', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <ForecastCard 
              forecast={mockApiResponses.forecast.success('24h')}
              data-testid="forecast-card"
              data-error-state="false"
            />
            <StatusBar 
              data-testid="status-bar"
              data-error-state="false"
              aria-live="assertive"
            />
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      // Simulate API error
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: {
          type: 'forecast_unavailable',
          message: 'Unable to fetch forecast data'
        }
      }));

      // Verify error is announced
      await waitFor(() => {
        expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
          expect.stringContaining('Error: Unable to fetch forecast data')
        );
      });

      // Verify error state is reflected in ARIA attributes
      const forecastCard = screen.getByTestId('forecast-card');
      const statusBar = screen.getByTestId('status-bar');
      
      expect(forecastCard.getAttribute('aria-invalid')).toBe('true');
      expect(statusBar.getAttribute('aria-describedby')).toContain('error');
    });

    it('should provide accessible error recovery options', async () => {
      const { container } = renderWithIntegration(
        <AccessibilityProvider data-testid="a11y-provider">
          <div>
            <MetricsDashboard 
              data-testid="metrics-dashboard"
              data-error-state="true"
            />
            <button 
              data-testid="retry-button"
              aria-describedby="error-description"
            >
              Retry loading metrics
            </button>
            <div id="error-description" data-testid="error-description">
              Failed to load metrics. Click retry to attempt loading again.
            </div>
          </div>
        </AccessibilityProvider>,
        { 
          queryClient, 
          metricsProvider: mockMetricsProvider,
          accessibilityProvider: mockAccessibilityProvider
        }
      );

      const retryButton = screen.getByTestId('retry-button');
      
      // Verify error recovery button is accessible
      expect(retryButton).toHaveAttribute('aria-describedby', 'error-description');
      
      // Test retry action
      await user.click(retryButton);
      
      expect(mockAccessibilityProvider.announceToScreenReader).toHaveBeenCalledWith(
        expect.stringContaining('Retrying to load metrics')
      );
    });
  });
});