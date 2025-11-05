/**
 * Tests for AnalogExplorer component
 * Ensures proper functionality of timeline interactions, export features, and data visualization
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { AnalogExplorer } from '@/components/AnalogExplorer';
import type { AnalogExplorerData, AnalogPattern } from '@/types';

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock recharts
jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ReferenceLine: () => <div data-testid="reference-line" />,
}));

// Mock date-fns to avoid timezone issues
jest.mock('date-fns', () => ({
  format: jest.fn((date: Date, formatString: string) => {
    if (formatString === 'MMM dd, yyyy') return 'Jan 01, 2023';
    if (formatString === 'HH:mm') return '12:00';
    return '2023-01-01T12:00:00Z';
  }),
  parseISO: jest.fn((dateString: string) => new Date(dateString)),
}));

// Mock data for testing
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
          events: ['Clear skies', 'Light winds'],
        },
        {
          hours_offset: 6,
          values: {
            't2m': 22.1,
            'u10': -1.8,
            'v10': 2.2,
            'msl': 1016.8,
            'r850': 68.1,
            'tp6h': 0.0,
            'cape': 920.0,
            't850': 19.5,
            'z500': 5825.0,
          },
          temperature_trend: 'rising',
          pressure_trend: 'rising',
        },
        {
          hours_offset: 12,
          values: {
            't2m': 24.8,
            'u10': -1.2,
            'v10': 2.8,
            'msl': 1018.1,
            'r850': 71.2,
            'tp6h': 0.0,
            'cape': 1050.0,
            't850': 21.3,
            'z500': 5830.0,
          },
          temperature_trend: 'rising',
          pressure_trend: 'stable',
          events: ['Temperature rising steadily'],
        },
      ],
      outcome_narrative: 'Temperature increased gradually with stable conditions throughout the period.',
      location: {
        latitude: -34.9285,
        longitude: 138.6007,
        name: 'Adelaide Test Station',
      },
      season_info: {
        month: 1,
        season: 'summer',
      },
    },
    {
      date: '2023-02-15T06:00:00Z',
      similarity_score: 0.87,
      initial_conditions: {
        't2m': 19.8,
        'u10': -3.1,
        'v10': 1.2,
        'msl': 1012.8,
        'r850': 72.5,
        'tp6h': 0.5,
        'cape': 750.0,
        't850': 17.9,
        'z500': 5815.0,
      },
      timeline: [
        {
          hours_offset: 0,
          values: {
            't2m': 19.8,
            'u10': -3.1,
            'v10': 1.2,
            'msl': 1012.8,
            'r850': 72.5,
            'tp6h': 0.5,
            'cape': 750.0,
            't850': 17.9,
            'z500': 5815.0,
          },
          temperature_trend: 'stable',
          pressure_trend: 'falling',
          events: ['Light rain began'],
        },
      ],
      outcome_narrative: 'Light rain developed with gradually cooling temperatures.',
      season_info: {
        month: 2,
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
    common_events: ['Temperature increase', 'Pressure changes', 'Clear conditions'],
  },
  generated_at: '2023-12-01T12:00:00Z',
};

// Mock global fetch
global.fetch = jest.fn();

// Mock URL and Blob for download testing
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

describe('AnalogExplorer', () => {
  const mockOnAnalogSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock document.body methods for download testing
    const mockLink = {
      href: '',
      download: '',
      click: jest.fn(),
    };
    jest.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'a') {
        return mockLink as any;
      }
      return document.createElement(tagName);
    });
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders loading state correctly', () => {
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        loading={true}
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    expect(screen.getByText('Historical Analog Patterns')).toBeInTheDocument();
    expect(screen.getByText('Top 5 Similar Patterns')).toBeInTheDocument();
    expect(screen.getByText('Timeline Visualization')).toBeInTheDocument();
  });

  it('renders error state correctly', () => {
    const errorMessage = 'Failed to load analog data';
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        error={errorMessage}
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    expect(screen.getByText('Analog Explorer Error')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('renders analog data correctly', () => {
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Check header
    expect(screen.getByText('Historical Analog Patterns')).toBeInTheDocument();
    expect(screen.getByText('+24h')).toBeInTheDocument();

    // Check analog cards
    expect(screen.getByText('95% match')).toBeInTheDocument();
    expect(screen.getByText('87% match')).toBeInTheDocument();
    expect(screen.getByText('Jan 01, 2023')).toBeInTheDocument();

    // Check export buttons
    expect(screen.getByText('CSV')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();

    // Check timeline controls
    expect(screen.getByTitle('Play')).toBeInTheDocument();
    expect(screen.getByTitle('Reset to start')).toBeInTheDocument();

    // Check chart components are rendered
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('handles timeline controls correctly', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Test play button
    const playButton = screen.getByTitle('Play');
    await user.click(playButton);
    expect(screen.getByTitle('Pause')).toBeInTheDocument();

    // Test reset button
    const resetButton = screen.getByTitle('Reset to start');
    await user.click(resetButton);
    expect(screen.getByTitle('Play')).toBeInTheDocument();
  });

  it('handles timeline scrubbing', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Find the timeline slider
    const slider = screen.getByRole('slider');
    expect(slider).toBeInTheDocument();

    // Test slider interaction
    fireEvent.change(slider, { target: { value: '0.5' } });
    expect(slider).toHaveValue('0.5');
  });

  it('handles analog card interactions', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Click on first analog card
    const firstCard = screen.getByText('95% match').closest('div');
    if (firstCard) {
      await user.click(firstCard);
      expect(mockOnAnalogSelect).toHaveBeenCalledWith(mockAnalogData.top_analogs[0]);
    }

    // Test expand details button
    const expandButton = screen.getAllByText('Show details')[0];
    await user.click(expandButton);
    expect(screen.getByText('Show less')).toBeInTheDocument();
  });

  it('handles variable selection', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Find variable selector
    const variableSelect = screen.getByDisplayValue('2m Temperature');
    expect(variableSelect).toBeInTheDocument();

    // Change variable
    await user.selectOptions(variableSelect, 'u10');
    expect(variableSelect).toHaveValue('u10');
  });

  it('handles CSV export', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    const csvButton = screen.getByText('CSV');
    await user.click(csvButton);

    // Verify that download was triggered
    expect(document.createElement).toHaveBeenCalledWith('a');
    expect(document.body.appendChild).toHaveBeenCalled();
    expect(document.body.removeChild).toHaveBeenCalled();
  });

  it('handles JSON export', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    const jsonButton = screen.getByText('JSON');
    await user.click(jsonButton);

    // Verify that download was triggered
    expect(document.createElement).toHaveBeenCalledWith('a');
    expect(document.body.appendChild).toHaveBeenCalled();
    expect(document.body.removeChild).toHaveBeenCalled();
  });

  it('renders empty state when no analogs available', () => {
    const emptyData: AnalogExplorerData = {
      ...mockAnalogData,
      top_analogs: [],
    };

    render(
      <AnalogExplorer
        data={emptyData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    expect(screen.getByText('No historical analogs found for this forecast')).toBeInTheDocument();
  });

  it('displays location information when available', () => {
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Expand first card to see location
    const expandButton = screen.getAllByText('Show details')[0];
    fireEvent.click(expandButton);

    // Location should be visible in expanded state
    expect(screen.getByText('Adelaide Test Station')).toBeInTheDocument();
  });

  it('handles timeline animation correctly', async () => {
    jest.useFakeTimers();
    
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Start playback
    const playButton = screen.getByTitle('Play');
    fireEvent.click(playButton);

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // Should show pause button
    expect(screen.getByTitle('Pause')).toBeInTheDocument();

    jest.useRealTimers();
  });

  it('displays trend indicators correctly', () => {
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Expand first card to see trend information
    const expandButton = screen.getAllByText('Show details')[0];
    fireEvent.click(expandButton);

    // Check for trend indicators in the current point info
    expect(screen.getByText('Temp:')).toBeInTheDocument();
    expect(screen.getByText('Pressure:')).toBeInTheDocument();
  });

  it('handles keyboard navigation correctly', async () => {
    const user = userEvent.setup();
    render(
      <AnalogExplorer
        data={mockAnalogData}
        horizon="24h"
        onAnalogSelect={mockOnAnalogSelect}
      />
    );

    // Test slider keyboard navigation
    const slider = screen.getByRole('slider');
    await user.click(slider);
    await user.keyboard('{ArrowRight}');
    
    // Slider should respond to keyboard input
    expect(slider).toHaveFocus();
  });
});