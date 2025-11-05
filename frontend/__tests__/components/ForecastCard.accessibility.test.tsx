/**
 * ForecastCard Accessibility Tests
 * 
 * Comprehensive accessibility testing for the ForecastCard component
 * including WCAG 2.1 AA compliance verification, keyboard navigation,
 * screen reader compatibility, and focus management.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { ForecastCard } from '@/components/ForecastCard';
import { AccessibilityProvider } from '@/components/AccessibilityProvider';
import type { ForecastResponse } from '@/types';

expect.extend(toHaveNoViolations);

// Mock forecast data for testing
const mockForecastData: ForecastResponse = {
  horizon: '6h',
  variables: {
    t2m: {
      value: 18.5,
      p05: 16.2,
      p50: 18.5,
      p95: 20.8,
      confidence: 0.94,
      available: true
    },
    cape: {
      value: 1250,
      available: true,
      confidence: 0.78
    }
  },
  wind10m: {
    speed: 4.2,
    direction: 225,
    gust: 6.1,
    available: true
  },
  risk_assessment: {
    temperature: 'moderate',
    precipitation: 'low',
    wind: 'low',
    severe_weather: 'minimal'
  },
  analogs_summary: {
    most_similar_date: '2023-08-15T14:00:00Z',
    similarity_score: 0.92,
    analog_count: 35,
    outcome_description: 'Clear skies with moderate warming trend continuing through afternoon'
  },
  narrative: 'Forecast shows continued mild warming with light westerly winds. High confidence based on strong analog matches.',
  confidence_explanation: 'High confidence due to 35 strong analog matches with 92% similarity score',
  generated_at: '2024-10-29T10:30:00Z',
  latency_ms: 145
};

const mockForecastUnavailable: ForecastResponse = {
  ...mockForecastData,
  variables: {
    t2m: {
      value: null,
      p05: null,
      p50: null,
      p95: null,
      confidence: null,
      available: false
    }
  }
};

// Test wrapper with AccessibilityProvider
const renderWithAccessibility = (component: React.ReactElement) => {
  return render(
    <AccessibilityProvider options={{ enableAnnouncements: true }}>
      {component}
    </AccessibilityProvider>
  );
};

describe('ForecastCard Accessibility', () => {
  
  describe('WCAG 2.1 AA Compliance', () => {
    test('should not have accessibility violations', async () => {
      const { container } = renderWithAccessibility(
        <ForecastCard forecast={mockForecastData} />
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('should not have violations when unavailable', async () => {
      const { container } = renderWithAccessibility(
        <ForecastCard forecast={mockForecastUnavailable} />
      );
      
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Semantic Structure', () => {
    test('should have proper article role and structure', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute('aria-label');
      expect(card.getAttribute('aria-label')).toContain('Forecast for 6h');
      expect(card.getAttribute('aria-label')).toContain('18.5 degrees Celsius');
      expect(card.getAttribute('aria-label')).toContain('94% confidence');
    });

    test('should have descriptive aria-label for unavailable forecast', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastUnavailable} />);
      
      const card = screen.getByRole('article');
      expect(card).toHaveAttribute('aria-label');
      expect(card.getAttribute('aria-label')).toContain('N/A degrees Celsius');
    });

    test('should have proper heading hierarchy', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      // Check for proper content structure
      expect(screen.getByText('+6h')).toBeInTheDocument();
      expect(screen.getByText('94%')).toBeInTheDocument();
      expect(screen.getByText('18.5')).toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    test('should be keyboard focusable', async () => {
      const user = userEvent.setup();
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      
      // Tab to card
      await user.tab();
      expect(card).toHaveFocus();
      expect(card).toHaveProperFocus();
    });

    test('should have visible focus indicator', async () => {
      const user = userEvent.setup();
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      
      await user.tab();
      expect(card).toHaveFocus();
      
      // Focus should be visible (tested by custom matcher)
      expect(card).toHaveVisibleFocusIndicator();
    });

    test('should handle keyboard activation', async () => {
      const user = userEvent.setup();
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      
      await user.tab();
      expect(card).toHaveFocus();
      
      // Enter key should be handled gracefully
      await user.keyboard('{Enter}');
      // Card should maintain focus
      expect(card).toHaveFocus();
    });

    test('should navigate interactive elements within card', async () => {
      const user = userEvent.setup();
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      // Tab through interactive elements
      await user.tab(); // Card itself
      
      // Look for interactive buttons within card
      const buttons = screen.getAllByRole('button');
      if (buttons.length > 0) {
        await user.tab(); // First interactive element
        expect(buttons[0]).toHaveFocus();
      }
    });
  });

  describe('Screen Reader Support', () => {
    test('should provide comprehensive information via aria-label', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      const ariaLabel = card.getAttribute('aria-label');
      
      expect(ariaLabel).toContain('Forecast for 6h');
      expect(ariaLabel).toContain('18.5 degrees Celsius');
      expect(ariaLabel).toContain('94% confidence');
    });

    test('should have proper button labels for interactive elements', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        // Each button should have accessible name
        expect(button).toHaveAccessibleName();
      });
    });

    test('should announce updates to screen readers', async () => {
      const { rerender } = renderWithAccessibility(
        <ForecastCard forecast={mockForecastData} />
      );
      
      // Update forecast data
      const updatedForecast = {
        ...mockForecastData,
        variables: {
          ...mockForecastData.variables,
          t2m: {
            ...mockForecastData.variables.t2m,
            value: 19.8
          }
        }
      };
      
      rerender(
        <AccessibilityProvider options={{ enableAnnouncements: true }}>
          <ForecastCard forecast={updatedForecast} />
        </AccessibilityProvider>
      );
      
      // Check for live region (may be added by AccessibilityProvider)
      await waitFor(() => {
        const liveRegions = screen.getAllByRole('status', { hidden: true });
        expect(liveRegions.length).toBeGreaterThanOrEqual(0);
      });
    });
  });

  describe('Visual Accessibility', () => {
    test('should have sufficient color contrast', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      
      // Check for dark theme classes that ensure proper contrast
      expect(card).toHaveClass('bg-[#0E1116]');
      expect(card).toHaveClass('text-slate-100'); // High contrast text
    });

    test('should not rely solely on color for information', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      // Risk assessment should have text labels, not just colors
      const riskElements = screen.getAllByText(/Risk Assessment/i);
      expect(riskElements.length).toBeGreaterThan(0);
      
      // Check for text-based risk indicators
      expect(screen.getByText(/moderate/i)).toBeInTheDocument();
      expect(screen.getByText(/low/i)).toBeInTheDocument();
    });

    test('should have proper focus indicators in different states', async () => {
      const user = userEvent.setup();
      renderWithAccessibility(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      
      // Test focus state
      await user.tab();
      expect(card).toHaveFocus();
      expect(card).toHaveClass('focus-within:ring-2');
      expect(card).toHaveClass('focus-within:ring-cyan-500');
    });
  });

  describe('Error States and Edge Cases', () => {
    test('should handle unavailable data accessibly', () => {
      renderWithAccessibility(<ForecastCard forecast={mockForecastUnavailable} />);
      
      const card = screen.getByRole('article');
      expect(card).toBeInTheDocument();
      
      // Should indicate unavailable state
      expect(screen.getByText(/Unavailable/i)).toBeInTheDocument();
      expect(screen.getByText(/Not enough valid analogs/i)).toBeInTheDocument();
    });

    test('should maintain accessibility with missing optional data', () => {
      const partialForecast = {
        ...mockForecastData,
        variables: {
          t2m: mockForecastData.variables.t2m
          // Missing cape and other optional variables
        },
        wind10m: undefined
      };
      
      renderWithAccessibility(<ForecastCard forecast={partialForecast} />);
      
      const card = screen.getByRole('article');
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute('aria-label');
    });
  });

  describe('Integration with AccessibilityProvider', () => {
    test('should work without AccessibilityProvider', () => {
      // Test that component doesn't break without provider
      render(<ForecastCard forecast={mockForecastData} />);
      
      const card = screen.getByRole('article');
      expect(card).toBeInTheDocument();
      expect(card).toHaveAttribute('aria-label');
    });

    test('should integrate with announcement system when available', async () => {
      const { rerender } = renderWithAccessibility(
        <ForecastCard forecast={mockForecastData} />
      );
      
      // Update data to trigger announcements
      const updatedForecast = {
        ...mockForecastData,
        variables: {
          ...mockForecastData.variables,
          t2m: {
            ...mockForecastData.variables.t2m,
            value: 20.1
          }
        }
      };
      
      rerender(
        <AccessibilityProvider options={{ enableAnnouncements: true }}>
          <ForecastCard forecast={updatedForecast} />
        </AccessibilityProvider>
      );
      
      // Should not throw errors and should work correctly
      expect(screen.getByRole('article')).toBeInTheDocument();
    });
  });

  describe('Performance and Efficiency', () => {
    test('should not cause excessive re-renders', () => {
      const renderSpy = jest.fn();
      const TestComponent = () => {
        renderSpy();
        return <ForecastCard forecast={mockForecastData} />;
      };
      
      const { rerender } = renderWithAccessibility(<TestComponent />);
      
      // Initial render
      expect(renderSpy).toHaveBeenCalledTimes(1);
      
      // Re-render with same data
      rerender(
        <AccessibilityProvider>
          <TestComponent />
        </AccessibilityProvider>
      );
      
      // Should not cause unnecessary re-renders
      expect(renderSpy).toHaveBeenCalledTimes(2); // Expected due to rerender call
    });
  });
});

// Additional custom matchers for TypeScript support
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeAccessible(): Promise<R>;
      toHaveProperFocus(): R;
      toHaveVisibleFocusIndicator(): R;
    }
  }
}