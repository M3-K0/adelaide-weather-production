/**
 * UI Component Interface Contracts
 * Adelaide Weather Forecasting System
 *
 * This file defines comprehensive TypeScript interfaces for all UI components
 * to enable contract-first parallel development between frontend and backend teams.
 *
 * @version 1.0.0
 * @author Design Systems Architect
 */

// Core Data Types
export interface VariableResult {
  /** Primary forecast value */
  value: number | null;
  /** 5th percentile value (lower bound) */
  p05: number | null;
  /** 95th percentile value (upper bound) */
  p95: number | null;
  /** Confidence level as percentage (0-100) */
  confidence: number | null;
  /** Whether this variable has sufficient data for reliable forecasting */
  available: boolean;
  /** Number of analog weather patterns used in this forecast */
  analog_count: number | null;
}

export interface WindResult {
  /** Wind speed in m/s */
  speed: number | null;
  /** Wind direction in degrees (0-360, where 0/360=North, 90=East, etc.) */
  direction: number | null;
  /** Wind gust speed in m/s */
  gust: number | null;
  /** Whether wind data is available and reliable */
  available: boolean;
}

export interface ForecastResponse {
  /** Forecast time horizon (e.g., "6h", "12h", "24h", "48h") */
  horizon: string;
  /** ISO timestamp when this forecast was generated */
  generated_at: string;
  /** Map of variable names to their forecast results */
  variables: Record<string, VariableResult>;
  /** 10-meter wind forecast data */
  wind10m: WindResult | null;
  /** System version information for traceability */
  versions: {
    model: string;
    index: string;
    datasets: string;
    schema: string;
  };
  /** Content hashes for cache validation */
  hashes: {
    model: string;
    index: string;
    datasets: string;
  };
  /** API response latency in milliseconds */
  latency_ms: number;
}

// Component Props Interfaces

/**
 * ForecastCard Component Interface
 *
 * Main weather forecast display card showing temperature, confidence,
 * wind conditions, and trend visualization.
 */
export interface ForecastCardProps {
  /** Time horizon display string (e.g., "+6h", "+12h") */
  horizon: string;
  /** Primary temperature value in Celsius */
  temp: number;
  /** Temperature confidence range (±degrees) */
  confidence: number;
  /** Confidence as percentage (0-100) for UI styling */
  confidencePct: number;
  /** 5th percentile temperature */
  p05: number;
  /** 50th percentile (median) temperature */
  p50: number;
  /** 95th percentile temperature */
  p95: number;
  /** Wind direction in degrees (0-360) */
  windDir: number;
  /** Wind speed in m/s */
  windSpeed: number;
  /** Optional wind gust speed in m/s */
  windGust?: number;
  /** API latency display string (e.g., "42ms") */
  latency: string;
  /** Temperature trend data for sparkline visualization */
  sparklineData: number[];
  /** Number of analog patterns used */
  analogCount: number;
  /** Whether forecast data is available and reliable */
  isAvailable?: boolean;
  /** Optional click handler for card interactions */
  onClick?: () => void;
  /** Optional className for custom styling */
  className?: string;
  /** Accessibility label override */
  ariaLabel?: string;
}

/**
 * CAPE Badge Component Interface
 *
 * Displays atmospheric instability indicator with color-coded severity levels.
 */
export interface CAPEBadgeProps {
  /** CAPE value in J/kg */
  value: number | null;
  /** Data availability status */
  available: boolean;
  /** Confidence level (0-100) */
  confidence?: number;
  /** Size variant for different use cases */
  size?: 'sm' | 'md' | 'lg';
  /** Display format preference */
  format?: 'compact' | 'detailed';
  /** Optional tooltip content */
  tooltip?: string;
  /** Optional click handler */
  onClick?: () => void;
  /** Custom className */
  className?: string;
}

/**
 * Status Bar Component Interface
 *
 * System status indicator showing operational health, data freshness,
 * and performance metrics.
 */
export interface StatusBarProps {
  /** Overall system status */
  status: 'healthy' | 'degraded' | 'down' | 'maintenance';
  /** Last data update timestamp */
  lastUpdated: string;
  /** System performance metrics */
  metrics: {
    /** Average API response time */
    avgLatency: number;
    /** Success rate percentage */
    successRate: number;
    /** Number of active forecasts */
    activeForecast: number;
    /** Data freshness in minutes */
    dataAge: number;
  };
  /** Version information */
  versions: {
    model: string;
    index: string;
    datasets: string;
  };
  /** Optional status message */
  message?: string;
  /** Compact display mode */
  compact?: boolean;
  /** Optional refresh handler */
  onRefresh?: () => void;
  /** Custom className */
  className?: string;
}

/**
 * Navigation Component Interface
 *
 * Main application navigation with active state management.
 */
export interface NavigationProps {
  /** Currently active navigation item */
  activeItem: string;
  /** Navigation item click handler */
  onItemClick: (itemId: string) => void;
  /** Navigation items configuration */
  items: NavigationItem[];
  /** Collapsed state for mobile */
  collapsed?: boolean;
  /** Custom className */
  className?: string;
}

export interface NavigationItem {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Lucide icon name or React component */
  icon: string | React.ComponentType<any>;
  /** Optional badge content */
  badge?: string | number;
  /** Disabled state */
  disabled?: boolean;
  /** Optional href for external links */
  href?: string;
}

/**
 * Weather Chart Component Interface
 *
 * Interactive time-series chart for detailed forecast visualization.
 */
export interface WeatherChartProps {
  /** Chart data with timestamps and values */
  data: ChartDataPoint[];
  /** Variables to display */
  variables: ChartVariable[];
  /** Time range for x-axis */
  timeRange: {
    start: string;
    end: string;
  };
  /** Chart height in pixels */
  height?: number;
  /** Interactive features enabled */
  interactive?: boolean;
  /** Show confidence intervals */
  showConfidence?: boolean;
  /** Custom className */
  className?: string;
}

export interface ChartDataPoint {
  /** ISO timestamp */
  timestamp: string;
  /** Variable values at this time */
  values: Record<string, number | null>;
  /** Confidence intervals */
  confidence?: Record<string, { min: number; max: number }>;
}

export interface ChartVariable {
  /** Variable identifier (e.g., "t2m", "wind_speed") */
  key: string;
  /** Display name */
  label: string;
  /** Units for axis labels */
  unit: string;
  /** Chart color */
  color: string;
  /** Whether to show by default */
  visible: boolean;
  /** Chart type */
  type: 'line' | 'area' | 'bar';
}

// Design System Types

/**
 * Design Token Interfaces
 * Comprehensive design system token definitions
 */
export interface DesignTokens {
  colors: ColorTokens;
  typography: TypographyTokens;
  spacing: SpacingTokens;
  shadows: ShadowTokens;
  borders: BorderTokens;
  animations: AnimationTokens;
}

export interface ColorTokens {
  // Semantic color scales
  primary: ColorScale;
  secondary: ColorScale;
  accent: ColorScale;
  success: ColorScale;
  warning: ColorScale;
  error: ColorScale;
  neutral: ColorScale;

  // Weather-specific colors
  weather: {
    hot: string;
    warm: string;
    mild: string;
    cool: string;
    cold: string;
    freezing: string;
  };

  // Confidence level colors
  confidence: {
    high: string; // 80-100%
    medium: string; // 50-79%
    low: string; // 0-49%
  };

  // Chart colors
  chart: string[];
}

export interface ColorScale {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string; // Base color
  600: string;
  700: string;
  800: string;
  900: string;
  950: string;
}

export interface TypographyTokens {
  fontFamily: {
    sans: string[];
    mono: string[];
  };
  fontSize: {
    xs: [string, { lineHeight: string }];
    sm: [string, { lineHeight: string }];
    base: [string, { lineHeight: string }];
    lg: [string, { lineHeight: string }];
    xl: [string, { lineHeight: string }];
    '2xl': [string, { lineHeight: string }];
    '3xl': [string, { lineHeight: string }];
    '4xl': [string, { lineHeight: string }];
    '5xl': [string, { lineHeight: string }];
    '6xl': [string, { lineHeight: string }];
  };
  fontWeight: {
    light: string;
    normal: string;
    medium: string;
    semibold: string;
    bold: string;
  };
}

export interface SpacingTokens {
  0: string;
  1: string;
  2: string;
  3: string;
  4: string;
  5: string;
  6: string;
  8: string;
  10: string;
  12: string;
  16: string;
  20: string;
  24: string;
  32: string;
  40: string;
  48: string;
  56: string;
  64: string;
}

export interface ShadowTokens {
  sm: string;
  base: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  inner: string;
  glow: {
    cyan: string;
    amber: string;
    red: string;
    green: string;
  };
}

export interface BorderTokens {
  width: {
    0: string;
    1: string;
    2: string;
    4: string;
    8: string;
  };
  radius: {
    none: string;
    sm: string;
    base: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
}

export interface AnimationTokens {
  duration: {
    fast: string;
    normal: string;
    slow: string;
  };
  easing: {
    linear: string;
    in: string;
    out: string;
    inOut: string;
  };
  keyframes: {
    fadeIn: Record<string, any>;
    slideUp: Record<string, any>;
    pulse: Record<string, any>;
    spin: Record<string, any>;
  };
}

// State Management Types

/**
 * Application State Interfaces
 */
export interface AppState {
  /** Current navigation state */
  navigation: NavigationState;
  /** Forecast data state */
  forecasts: ForecastState;
  /** System status state */
  system: SystemState;
  /** User preferences */
  preferences: PreferencesState;
}

export interface NavigationState {
  activeItem: string;
  sidebarCollapsed: boolean;
  history: string[];
}

export interface ForecastState {
  /** Current forecast data by horizon */
  data: Record<string, ForecastResponse>;
  /** Loading states */
  loading: Record<string, boolean>;
  /** Error states */
  errors: Record<string, string | null>;
  /** Last fetch timestamps */
  lastFetch: Record<string, string>;
  /** Auto-refresh settings */
  autoRefresh: {
    enabled: boolean;
    interval: number;
  };
}

export interface SystemState {
  status: 'healthy' | 'degraded' | 'down' | 'maintenance';
  metrics: {
    avgLatency: number;
    successRate: number;
    activeForecast: number;
    dataAge: number;
  };
  versions: {
    model: string;
    index: string;
    datasets: string;
  };
  lastHealthCheck: string;
}

export interface PreferencesState {
  /** Temperature unit preference */
  temperatureUnit: 'celsius' | 'fahrenheit';
  /** Wind speed unit preference */
  windUnit: 'ms' | 'kmh' | 'mph' | 'knots';
  /** Theme preference */
  theme: 'dark' | 'light' | 'system';
  /** Accessibility preferences */
  accessibility: {
    reduceMotion: boolean;
    highContrast: boolean;
    fontSize: 'normal' | 'large' | 'larger';
  };
  /** Notification preferences */
  notifications: {
    enabled: boolean;
    weatherAlerts: boolean;
    systemAlerts: boolean;
  };
}

// Component Composition Types

/**
 * Higher-Order Component and Composition Interfaces
 */
export interface WithLoadingProps {
  loading?: boolean;
  skeleton?: React.ComponentType<any>;
}

export interface WithErrorProps {
  error?: string | null;
  fallback?: React.ComponentType<{ error: string }>;
  onRetry?: () => void;
}

export interface WithTooltipProps {
  tooltip?: string | React.ReactNode;
  tooltipPlacement?: 'top' | 'bottom' | 'left' | 'right';
  tooltipDelay?: number;
}

// API Integration Types

/**
 * API Client Interface Contracts
 */
export interface ForecastAPIClient {
  /** Fetch forecast for specific horizon */
  getForecast(horizon: string, variables?: string[]): Promise<ForecastResponse>;
  /** Fetch forecasts for multiple horizons */
  getMultipleForecasts(
    horizons: string[],
    variables?: string[]
  ): Promise<Record<string, ForecastResponse>>;
  /** Get system health status */
  getSystemStatus(): Promise<SystemStatus>;
  /** Cancel ongoing requests */
  cancelRequests(): void;
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'down' | 'maintenance';
  timestamp: string;
  services: {
    api: ServiceHealth;
    database: ServiceHealth;
    cache: ServiceHealth;
    model: ServiceHealth;
  };
  metrics: {
    responseTime: number;
    uptime: number;
    errorRate: number;
  };
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'down';
  latency?: number;
  lastCheck: string;
  message?: string;
}

// Event Handling Types

/**
 * Component Event Interfaces
 */
export interface ForecastCardEvents {
  onClick?: (horizon: string) => void;
  onExpand?: (horizon: string) => void;
  onShare?: (data: ForecastCardProps) => void;
  onRefresh?: (horizon: string) => void;
}

export interface ChartEvents {
  onDataPointHover?: (point: ChartDataPoint) => void;
  onTimeRangeChange?: (range: { start: string; end: string }) => void;
  onVariableToggle?: (variable: string, visible: boolean) => void;
  onZoom?: (range: { start: string; end: string }) => void;
}

// Testing and Development Types

/**
 * Mock Data and Testing Interfaces
 */
export interface MockDataGenerator {
  /** Generate realistic forecast data */
  generateForecast(horizon: string, options?: MockOptions): ForecastResponse;
  /** Generate component test props */
  generateComponentProps<T>(component: string, overrides?: Partial<T>): T;
  /** Generate chart data */
  generateChartData(points: number, variables: string[]): ChartDataPoint[];
}

export interface MockOptions {
  /** Temperature range for random generation */
  tempRange?: [number, number];
  /** Confidence level range */
  confidenceRange?: [number, number];
  /** Include unavailable data scenarios */
  includeUnavailable?: boolean;
  /** Latency range for simulation */
  latencyRange?: [number, number];
}

// Accessibility Types

/**
 * Accessibility Interface Contracts
 */
export interface AccessibilityProps {
  /** ARIA label for screen readers */
  'aria-label'?: string;
  /** ARIA description */
  'aria-describedby'?: string;
  /** ARIA live region politeness */
  'aria-live'?: 'off' | 'polite' | 'assertive';
  /** Role for semantic meaning */
  role?: string;
  /** Tab index for keyboard navigation */
  tabIndex?: number;
  /** Keyboard event handlers */
  onKeyDown?: (event: React.KeyboardEvent) => void;
  onKeyUp?: (event: React.KeyboardEvent) => void;
}

// Performance Types

/**
 * Performance Optimization Interfaces
 */
export interface PerformanceMetrics {
  /** Component render time */
  renderTime: number;
  /** Memory usage */
  memoryUsage: number;
  /** Bundle size impact */
  bundleSize: number;
  /** Time to interactive */
  timeToInteractive: number;
}

export interface OptimizationConfig {
  /** Enable code splitting */
  codeSplitting: boolean;
  /** Enable image optimization */
  imageOptimization: boolean;
  /** Enable prefetching */
  prefetching: boolean;
  /** Cache strategy */
  cacheStrategy: 'memory' | 'sessionStorage' | 'localStorage' | 'none';
}
