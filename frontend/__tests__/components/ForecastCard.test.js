/**
 * ForecastCard Component Tests
 * Tests React component rendering and functionality
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ForecastCard from '../../app/page'; // Extract ForecastCard component

// Mock ForecastCard data
const mockForecastData = {
  horizon: '+6h',
  temp: 22.5,
  confidence: 2.5,
  confidencePct: 85,
  p05: 20.0,
  p50: 22.5,
  p95: 25.0,
  windDir: 180,
  windSpeed: 12.5,
  windGust: 18.0,
  latency: '45ms',
  analogCount: 50,
  sparklineData: [20.0, 20.8, 21.5, 22.5, 23.2, 24.0, 25.0],
  isAvailable: true
};

const mockUnavailableData = {
  ...mockForecastData,
  isAvailable: false,
  temp: null,
  confidence: null
};

// Mock the sparkline component since it's complex to test
jest.mock('../../components/ui/sparkline', () => {
  return function MockSparkline({ data, className }) {
    return (
      <div data-testid='sparkline' className={className}>
        Sparkline: {data?.join(',')}
      </div>
    );
  };
});

describe('ForecastCard Component', () => {
  test('renders forecast data correctly', () => {
    render(<ForecastCard {...mockForecastData} />);

    // Check horizon display
    expect(screen.getByText('+6h')).toBeInTheDocument();

    // Check temperature display
    expect(screen.getByText('22.5°C')).toBeInTheDocument();

    // Check confidence display
    expect(screen.getByText('85%')).toBeInTheDocument();

    // Check wind information
    expect(screen.getByText('12.5 m/s')).toBeInTheDocument();
    expect(screen.getByText('S')).toBeInTheDocument(); // 180° = South

    // Check latency display
    expect(screen.getByText('45ms')).toBeInTheDocument();

    // Check analog count
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  test('handles unavailable forecast data', () => {
    render(<ForecastCard {...mockUnavailableData} />);

    // Should show unavailable state
    expect(screen.getByText('Data Unavailable')).toBeInTheDocument();

    // Should not show numeric values
    expect(screen.queryByText('22.5°C')).not.toBeInTheDocument();
  });

  test('displays percentile range correctly', () => {
    render(<ForecastCard {...mockForecastData} />);

    // Check percentile range display
    expect(screen.getByText('20.0')).toBeInTheDocument(); // p05
    expect(screen.getByText('25.0')).toBeInTheDocument(); // p95
  });

  test('shows wind direction correctly', () => {
    const testCases = [
      { direction: 0, expected: 'N' },
      { direction: 90, expected: 'E' },
      { direction: 180, expected: 'S' },
      { direction: 270, expected: 'W' },
      { direction: 45, expected: 'NE' },
      { direction: 225, expected: 'SW' }
    ];

    testCases.forEach(({ direction, expected }) => {
      const { unmount } = render(
        <ForecastCard {...mockForecastData} windDir={direction} />
      );

      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });

  test('renders sparkline with correct data', () => {
    render(<ForecastCard {...mockForecastData} />);

    const sparkline = screen.getByTestId('sparkline');
    expect(sparkline).toBeInTheDocument();
    expect(sparkline).toHaveTextContent('20,20.8,21.5,22.5,23.2,24,25');
  });

  test('handles missing wind gust data', () => {
    const dataWithoutGust = { ...mockForecastData, windGust: undefined };
    render(<ForecastCard {...dataWithoutGust} />);

    // Should still render wind speed
    expect(screen.getByText('12.5 m/s')).toBeInTheDocument();

    // Should not show gust information
    expect(screen.queryByText('Gust:')).not.toBeInTheDocument();
  });

  test('applies correct CSS classes for styling', () => {
    const { container } = render(<ForecastCard {...mockForecastData} />);

    // Check for expected CSS classes
    const card = container.firstChild;
    expect(card).toHaveClass('bg-card');
    expect(card).toHaveClass('text-card-foreground');
  });

  test('shows confidence with appropriate color coding', () => {
    // Test high confidence (should be green)
    const { rerender } = render(
      <ForecastCard {...mockForecastData} confidencePct={90} />
    );

    let confidenceElement = screen.getByText('90%');
    expect(confidenceElement).toHaveClass('text-green-600');

    // Test medium confidence (should be yellow)
    rerender(<ForecastCard {...mockForecastData} confidencePct={60} />);
    confidenceElement = screen.getByText('60%');
    expect(confidenceElement).toHaveClass('text-yellow-600');

    // Test low confidence (should be red)
    rerender(<ForecastCard {...mockForecastData} confidencePct={30} />);
    confidenceElement = screen.getByText('30%');
    expect(confidenceElement).toHaveClass('text-red-600');
  });

  test('handles extreme temperature values', () => {
    const extremeData = { ...mockForecastData, temp: -40.5 };
    render(<ForecastCard {...extremeData} />);

    expect(screen.getByText('-40.5°C')).toBeInTheDocument();
  });

  test('handles very long latency values', () => {
    const slowData = { ...mockForecastData, latency: '2500ms' };
    render(<ForecastCard {...slowData} />);

    const latencyElement = screen.getByText('2500ms');
    expect(latencyElement).toBeInTheDocument();
    // Should have warning styling for slow responses
    expect(latencyElement).toHaveClass('text-red-600');
  });

  test('accessibility: has proper ARIA labels', () => {
    render(<ForecastCard {...mockForecastData} />);

    // Check for ARIA labels
    expect(screen.getByRole('region')).toBeInTheDocument();
    expect(screen.getByLabelText(/forecast for/i)).toBeInTheDocument();
  });

  test('accessibility: keyboard navigation support', () => {
    render(<ForecastCard {...mockForecastData} />);

    const card = screen.getByRole('region');
    expect(card).toHaveAttribute('tabIndex', '0');
  });
});

describe('ForecastCard Integration', () => {
  test('integrates with real API data structure', () => {
    // Simulate real API response structure
    const realApiData = {
      horizon: '6h',
      variables: {
        t2m: {
          value: 22.5,
          p05: 20.0,
          p95: 25.0,
          confidence: 85,
          available: true,
          analog_count: 50
        }
      },
      wind10m: {
        speed: 12.5,
        direction: 180
      },
      latency_ms: 45
    };

    // Convert to ForecastCard format (as done in main component)
    const cardData = {
      horizon: `+${realApiData.horizon}`,
      temp: realApiData.variables.t2m.value,
      confidence:
        Math.abs(
          realApiData.variables.t2m.p95 - realApiData.variables.t2m.p05
        ) / 2,
      confidencePct: Math.round(realApiData.variables.t2m.confidence),
      p05: realApiData.variables.t2m.p05,
      p50: realApiData.variables.t2m.value,
      p95: realApiData.variables.t2m.p95,
      windDir: realApiData.wind10m.direction,
      windSpeed: realApiData.wind10m.speed,
      latency: `${realApiData.latency_ms}ms`,
      analogCount: realApiData.variables.t2m.analog_count,
      isAvailable: realApiData.variables.t2m.available,
      sparklineData: [20.0, 20.8, 21.5, 22.5, 23.2, 24.0, 25.0]
    };

    render(<ForecastCard {...cardData} />);

    // Verify the integration works correctly
    expect(screen.getByText('+6h')).toBeInTheDocument();
    expect(screen.getByText('22.5°C')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('45ms')).toBeInTheDocument();
  });
});
