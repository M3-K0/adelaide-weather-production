/**
 * MetricsDashboard Component Tests
 * 
 * Tests for the metrics dashboard functionality including
 * data loading, filtering, and export capabilities.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MetricsDashboard } from '@/components';
import * as metricsApi from '@/lib/metricsApi';

// Mock the metrics API
jest.mock('@/lib/metricsApi', () => ({
  metricsApi: {
    getMetricsSummary: jest.fn(),
    exportMetrics: jest.fn(),
    clearCache: jest.fn(),
  },
}));

const mockMetricsApi = metricsApi.metricsApi as jest.Mocked<typeof metricsApi.metricsApi>;

// Mock recharts to avoid rendering issues in tests
jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  Legend: () => <div data-testid="legend" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  Download: () => <div data-testid="download-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
  Filter: () => <div data-testid="filter-icon" />,
  Calendar: () => <div data-testid="calendar-icon" />,
  BarChart3: () => <div data-testid="bar-chart-icon" />,
  Activity: () => <div data-testid="activity-icon" />,
  AlertCircle: () => <div data-testid="alert-icon" />,
  CheckCircle: () => <div data-testid="check-icon" />,
  Settings: () => <div data-testid="settings-icon" />,
  Info: () => <div data-testid="info-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  Database: () => <div data-testid="database-icon" />,
  Wifi: () => <div data-testid="wifi-icon" />,
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  XCircle: () => <div data-testid="x-circle-icon" />,
  TrendingUp: () => <div data-testid="trending-up-icon" />,
  TrendingDown: () => <div data-testid="trending-down-icon" />,
  Minus: () => <div data-testid="minus-icon" />,
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  format: jest.fn((date, formatStr) => {
    if (formatStr === 'MMM dd HH:mm') return 'Oct 29 12:00';
    if (formatStr === 'HH:mm') return '12:00';
    return '2023-10-29T12:00:00.000Z';
  }),
}));

const mockMetricsData = {
  forecast_accuracy: [
    {
      horizon: '24h' as const,
      variable: 't2m' as const,
      mae: 1.2,
      bias: 0.1,
      accuracy_percent: 92.5,
      confidence_interval: 3.5,
      last_updated: '2023-10-29T12:00:00.000Z',
    },
    {
      horizon: '24h' as const,
      variable: 'u10' as const,
      mae: 2.1,
      bias: -0.2,
      accuracy_percent: 88.3,
      confidence_interval: 5.2,
      last_updated: '2023-10-29T12:00:00.000Z',
    },
  ],
  performance_metrics: [
    {
      metric_name: 'API Response Time',
      value: 150,
      unit: 'ms',
      status: 'good' as const,
      threshold_warning: 500,
      threshold_critical: 1000,
      last_updated: '2023-10-29T12:00:00.000Z',
    },
    {
      metric_name: 'Cache Hit Rate',
      value: 85,
      unit: '%',
      status: 'good' as const,
      threshold_warning: 70,
      threshold_critical: 50,
      last_updated: '2023-10-29T12:00:00.000Z',
    },
  ],
  system_health: [
    {
      component: 'API Server',
      status: 'up' as const,
      uptime_percent: 99.5,
      last_check: '2023-10-29T12:00:00.000Z',
      response_time_ms: 45,
    },
    {
      component: 'Database',
      status: 'up' as const,
      uptime_percent: 99.8,
      last_check: '2023-10-29T12:00:00.000Z',
      response_time_ms: 15,
    },
  ],
  trends: {
    accuracy_trends: [
      { timestamp: '2023-10-29T11:00:00.000Z', value: 91.2 },
      { timestamp: '2023-10-29T12:00:00.000Z', value: 92.5 },
    ],
    performance_trends: [
      { timestamp: '2023-10-29T11:00:00.000Z', value: 145 },
      { timestamp: '2023-10-29T12:00:00.000Z', value: 150 },
    ],
    confidence_trends: [
      { timestamp: '2023-10-29T11:00:00.000Z', value: 88.5 },
      { timestamp: '2023-10-29T12:00:00.000Z', value: 90.2 },
    ],
  },
  generated_at: '2023-10-29T12:00:00.000Z',
  time_range: '24h' as const,
};

describe('MetricsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockMetricsApi.getMetricsSummary.mockResolvedValue(mockMetricsData);
  });

  it('renders dashboard header with title', async () => {
    render(<MetricsDashboard />);
    
    expect(screen.getByText('Metrics Dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart-icon')).toBeInTheDocument();
  });

  it('loads and displays metrics data', async () => {
    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalled();
    });

    // Check for performance metrics
    expect(screen.getByText('API Response Time')).toBeInTheDocument();
    expect(screen.getByText('Cache Hit Rate')).toBeInTheDocument();

    // Check for system health components
    expect(screen.getByText('API Server')).toBeInTheDocument();
    expect(screen.getByText('Database')).toBeInTheDocument();
  });

  it('displays system status badge', async () => {
    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('System Healthy')).toBeInTheDocument();
    });
  });

  it('handles time range selection', async () => {
    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalled();
    });

    const timeRangeSelect = screen.getByDisplayValue('Last 24 Hours');
    fireEvent.change(timeRangeSelect, { target: { value: '7d' } });

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledWith(
        expect.objectContaining({
          timeRange: '7d',
        })
      );
    });
  });

  it('toggles filter panel', async () => {
    render(<MetricsDashboard />);
    
    const filterButton = screen.getByTitle('Toggle Filters');
    fireEvent.click(filterButton);

    expect(screen.getByText('Forecast Horizons')).toBeInTheDocument();
    expect(screen.getByText('Weather Variables')).toBeInTheDocument();
  });

  it('handles horizon filter changes', async () => {
    render(<MetricsDashboard />);
    
    // Open filters
    const filterButton = screen.getByTitle('Toggle Filters');
    fireEvent.click(filterButton);

    // Click on a horizon button to toggle it
    const horizon6h = screen.getByText('6h');
    fireEvent.click(horizon6h);

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledWith(
        expect.objectContaining({
          horizons: expect.not.arrayContaining(['6h']),
        })
      );
    });
  });

  it('handles variable filter changes', async () => {
    render(<MetricsDashboard />);
    
    // Open filters
    const filterButton = screen.getByTitle('Toggle Filters');
    fireEvent.click(filterButton);

    // Click on a variable button to toggle it
    const tempVariable = screen.getByText('2m Temperature');
    fireEvent.click(tempVariable);

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledWith(
        expect.objectContaining({
          variables: expect.not.arrayContaining(['t2m']),
        })
      );
    });
  });

  it('handles refresh button click', async () => {
    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByTitle('Refresh Data');
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(2);
    });
  });

  it('handles export functionality', async () => {
    const mockExportData = {
      format: 'json' as const,
      filename: 'metrics-2023-10-29.json',
      data: JSON.stringify(mockMetricsData, null, 2),
    };

    mockMetricsApi.exportMetrics.mockResolvedValue(mockExportData);

    // Mock URL.createObjectURL and related functions
    global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = jest.fn();
    
    // Mock document.createElement and related DOM methods
    const mockAnchor = {
      href: '',
      download: '',
      click: jest.fn(),
    };
    jest.spyOn(document, 'createElement').mockReturnValue(mockAnchor as any);
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor as any);

    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalled();
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(mockMetricsApi.exportMetrics).toHaveBeenCalledWith('json', expect.any(Object));
    });

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(mockAnchor.click).toHaveBeenCalled();
  });

  it('displays loading state initially', () => {
    mockMetricsApi.getMetricsSummary.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<MetricsDashboard />);
    
    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
    expect(screen.getByTestId('refresh-icon')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch metrics';
    mockMetricsApi.getMetricsSummary.mockRejectedValue(new Error(errorMessage));

    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Metrics')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeInTheDocument();

    // Test retry functionality
    mockMetricsApi.getMetricsSummary.mockResolvedValue(mockMetricsData);
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(2);
    });
  });

  it('calculates summary statistics correctly', async () => {
    render(<MetricsDashboard />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalled();
    });

    // Check average accuracy calculation
    const expectedAvgAccuracy = ((92.5 + 88.3) / 2).toFixed(1);
    expect(screen.getByText(`${expectedAvgAccuracy}%`)).toBeInTheDocument();

    // Check average uptime calculation
    const expectedAvgUptime = ((99.5 + 99.8) / 2).toFixed(1);
    expect(screen.getByText(`${expectedAvgUptime}%`)).toBeInTheDocument();
  });

  it('auto-refreshes when enabled', async () => {
    jest.useFakeTimers();
    
    render(<MetricsDashboard autoRefresh={true} refreshInterval={5} />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(1);
    });

    // Fast-forward 5 seconds
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(2);
    });

    jest.useRealTimers();
  });

  it('does not auto-refresh when disabled', async () => {
    jest.useFakeTimers();
    
    render(<MetricsDashboard autoRefresh={false} />);
    
    await waitFor(() => {
      expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(1);
    });

    // Fast-forward 30 seconds
    jest.advanceTimersByTime(30000);

    // Should still only be called once
    expect(mockMetricsApi.getMetricsSummary).toHaveBeenCalledTimes(1);

    jest.useRealTimers();
  });
});