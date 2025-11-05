/**
 * Forecast Versioning API Client
 * =============================
 * 
 * TypeScript client for interacting with the forecast versioning API endpoints.
 * Provides comprehensive forecast version management, comparison, and export functionality.
 * 
 * Features:
 * - Forecast version listing and retrieval
 * - Version comparison with detailed analysis
 * - Historical data search and filtering
 * - Export job management with progress tracking
 * - Performance analytics and trends
 * 
 * Author: T-013 Implementation
 * Version: 1.0.0 - Versioned Storage with UI Access
 */

import { format, parseISO } from 'date-fns';

// ============================================================================
// Types for Forecast Versioning
// ============================================================================

export interface ForecastVersionSummary {
  version_id: string;
  forecast_time: string;
  created_at: string;
  horizon: string;
  confidence_score?: number;
  risk_level?: string;
  model_version: string;
  latency_ms?: number;
  analog_count?: number;
  variable_count: number;
}

export interface ForecastVersionDetail {
  version_id: string;
  forecast_time: string;
  created_at: string;
  horizon: string;
  location_lat: number;
  location_lon: number;
  variables: Record<string, any>;
  wind_data?: Record<string, any>;
  model_version: string;
  index_version: string;
  dataset_hash: string;
  api_version: string;
  latency_ms?: number;
  analog_count?: number;
  total_analogs_used?: number;
  confidence_score?: number;
  risk_level?: string;
  narrative?: string;
  confidence_explanation?: string;
  user_id?: string;
  correlation_id?: string;
  request_params?: Record<string, any>;
}

export interface VersionComparison {
  comparison_id: string;
  created_at: string;
  created_by?: string;
  version_a: ForecastVersionSummary;
  version_b: ForecastVersionSummary;
  variables_compared: string[];
  differences: Record<string, any>;
  similarity_score?: number;
  significant_changes: string[];
  notes?: string;
  tags: string[];
}

export interface VersionComparisonRequest {
  version_ids: string[];
  variables?: string[];
  notes?: string;
}

export interface ExportRequest {
  export_type: 'json' | 'csv' | 'archive';
  start_date: string;
  end_date: string;
  horizons: string[];
  variables: string[];
  include_metadata?: boolean;
  include_comparisons?: boolean;
  filters?: Record<string, any>;
}

export interface ExportStatus {
  export_id: string;
  created_at: string;
  created_by: string;
  export_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired';
  progress_percent: number;
  file_size_bytes?: number;
  record_count?: number;
  download_url?: string;
  expires_at?: string;
  error_message?: string;
}

export interface VersionAnalytics {
  time_range: {
    start: string;
    end: string;
  };
  total_versions: number;
  versions_by_horizon: Record<string, number>;
  versions_by_model: Record<string, number>;
  avg_latency_ms: number;
  avg_confidence_score: number;
  avg_analog_count: number;
  confidence_trend: Array<{
    date: string;
    value: number;
    count: number;
  }>;
  accuracy_trend: Array<{
    date: string;
    accuracy: number;
    variable: string;
  }>;
  usage_trend: Array<{
    date: string;
    versions: number;
    avg_latency: number;
  }>;
}

export interface VersionSearchRequest {
  query?: string;
  start_date?: string;
  end_date?: string;
  horizons?: string[];
  model_versions?: string[];
  confidence_min?: number;
  confidence_max?: number;
  risk_levels?: string[];
  variables?: string[];
  user_id?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export interface VersionListResponse extends PaginatedResponse<ForecastVersionSummary> {
  filters_applied: Record<string, any>;
}

export interface VersionSearchResponse extends PaginatedResponse<ForecastVersionSummary> {
  search_criteria: Record<string, any>;
}

// ============================================================================
// API Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const VERSIONING_BASE = `${API_BASE_URL}/api/versions`;

// Default headers for API requests
const getDefaultHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add authentication if available
  const token = typeof window !== 'undefined' ? localStorage.getItem('api_token') : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

// ============================================================================
// Error Handling
// ============================================================================

export class VersioningApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'VersioningApiError';
  }
}

async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new VersioningApiError(
      errorData.error?.message || errorData.detail || `HTTP ${response.status}`,
      response.status,
      errorData
    );
  }

  return response.json();
}

// ============================================================================
// Core API Functions
// ============================================================================

/**
 * Get paginated list of forecast versions with optional filtering
 */
export async function getForecastVersions(params: {
  start_date?: string;
  end_date?: string;
  horizon?: string;
  model_version?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<VersionListResponse> {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, value.toString());
    }
  });

  const url = `${VERSIONING_BASE}?${searchParams.toString()}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: getDefaultHeaders(),
  });

  const data = await handleApiResponse<{
    versions: ForecastVersionSummary[];
    pagination: any;
    filters_applied: any;
  }>(response);

  return {
    data: data.versions,
    pagination: data.pagination,
    filters_applied: data.filters_applied,
  };
}

/**
 * Get detailed information for a specific forecast version
 */
export async function getForecastVersionDetail(versionId: string): Promise<ForecastVersionDetail> {
  const response = await fetch(`${VERSIONING_BASE}/${versionId}`, {
    method: 'GET',
    headers: getDefaultHeaders(),
  });

  return handleApiResponse<ForecastVersionDetail>(response);
}

/**
 * Compare multiple forecast versions
 */
export async function compareForecastVersions(
  request: VersionComparisonRequest
): Promise<VersionComparison> {
  const response = await fetch(`${VERSIONING_BASE}/compare`, {
    method: 'POST',
    headers: getDefaultHeaders(),
    body: JSON.stringify(request),
  });

  return handleApiResponse<VersionComparison>(response);
}

/**
 * Advanced search for forecast versions
 */
export async function searchForecastVersions(
  request: VersionSearchRequest
): Promise<VersionSearchResponse> {
  const response = await fetch(`${VERSIONING_BASE}/search`, {
    method: 'POST',
    headers: getDefaultHeaders(),
    body: JSON.stringify(request),
  });

  const data = await handleApiResponse<{
    versions: ForecastVersionSummary[];
    pagination: any;
    search_criteria: any;
  }>(response);

  return {
    data: data.versions,
    pagination: data.pagination,
    search_criteria: data.search_criteria,
  };
}

/**
 * Create a new export job for historical forecast data
 */
export async function createExportJob(request: ExportRequest): Promise<ExportStatus> {
  const response = await fetch(`${API_BASE_URL}/api/exports`, {
    method: 'POST',
    headers: getDefaultHeaders(),
    body: JSON.stringify(request),
  });

  return handleApiResponse<ExportStatus>(response);
}

/**
 * Get the status of an export job
 */
export async function getExportStatus(exportId: string): Promise<ExportStatus> {
  const response = await fetch(`${API_BASE_URL}/api/exports/${exportId}`, {
    method: 'GET',
    headers: getDefaultHeaders(),
  });

  return handleApiResponse<ExportStatus>(response);
}

/**
 * Download an exported file
 */
export async function downloadExport(exportId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/exports/${exportId}/download`, {
    method: 'GET',
    headers: getDefaultHeaders(),
  });

  if (!response.ok) {
    throw new VersioningApiError(`Download failed: ${response.status}`, response.status);
  }

  return response.blob();
}

/**
 * Get analytics and trends for forecast versions
 */
export async function getVersionAnalytics(days: number = 30): Promise<VersionAnalytics> {
  const response = await fetch(`${VERSIONING_BASE}/analytics?days=${days}`, {
    method: 'GET',
    headers: getDefaultHeaders(),
  });

  return handleApiResponse<VersionAnalytics>(response);
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format forecast version for display
 */
export function formatVersionSummary(version: ForecastVersionSummary): {
  title: string;
  subtitle: string;
  confidence: string;
  metadata: string[];
} {
  const forecastDate = parseISO(version.forecast_time);
  const title = `${version.horizon} Forecast`;
  const subtitle = format(forecastDate, 'PPpp');
  
  const confidence = version.confidence_score 
    ? `${Math.round(version.confidence_score * 100)}%`
    : 'N/A';

  const metadata = [
    `Model: ${version.model_version}`,
    `Variables: ${version.variable_count}`,
    version.analog_count ? `Analogs: ${version.analog_count}` : '',
    version.latency_ms ? `${version.latency_ms}ms` : '',
  ].filter(Boolean);

  return { title, subtitle, confidence, metadata };
}

/**
 * Calculate time ago string for version timestamps
 */
export function getTimeAgo(timestamp: string): string {
  const date = parseISO(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else {
    return `${diffDays}d ago`;
  }
}

/**
 * Get risk level color for UI display
 */
export function getRiskLevelColor(riskLevel?: string): string {
  switch (riskLevel) {
    case 'minimal':
      return 'text-green-600 bg-green-50';
    case 'low':
      return 'text-blue-600 bg-blue-50';
    case 'moderate':
      return 'text-yellow-600 bg-yellow-50';
    case 'high':
      return 'text-orange-600 bg-orange-50';
    case 'extreme':
      return 'text-red-600 bg-red-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

/**
 * Format confidence score for display
 */
export function formatConfidence(confidence?: number): string {
  if (confidence === undefined || confidence === null) {
    return 'Unknown';
  }
  
  const percent = Math.round(confidence * 100);
  
  if (percent >= 90) return `Very High (${percent}%)`;
  if (percent >= 75) return `High (${percent}%)`;
  if (percent >= 50) return `Moderate (${percent}%)`;
  if (percent >= 25) return `Low (${percent}%)`;
  return `Very Low (${percent}%)`;
}

/**
 * Generate download filename for exports
 */
export function generateExportFilename(
  exportType: string,
  startDate: string,
  endDate: string,
  horizons: string[]
): string {
  const start = format(parseISO(startDate), 'yyyy-MM-dd');
  const end = format(parseISO(endDate), 'yyyy-MM-dd');
  const horizonStr = horizons.join('-');
  
  return `weather-forecast-versions_${start}_to_${end}_${horizonStr}.${exportType}`;
}

/**
 * Validate version comparison request
 */
export function validateComparisonRequest(request: VersionComparisonRequest): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (!request.version_ids || request.version_ids.length < 2) {
    errors.push('At least 2 versions are required for comparison');
  }

  if (request.version_ids && request.version_ids.length > 5) {
    errors.push('Maximum 5 versions can be compared at once');
  }

  // Validate UUID format
  if (request.version_ids) {
    request.version_ids.forEach((id, index) => {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(id)) {
        errors.push(`Version ID at position ${index + 1} is not a valid UUID`);
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Validate export request
 */
export function validateExportRequest(request: ExportRequest): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (!['json', 'csv', 'archive'].includes(request.export_type)) {
    errors.push('Export type must be json, csv, or archive');
  }

  try {
    const startDate = parseISO(request.start_date);
    const endDate = parseISO(request.end_date);
    
    if (startDate >= endDate) {
      errors.push('Start date must be before end date');
    }

    const daysDiff = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
    if (daysDiff > 365) {
      errors.push('Date range cannot exceed 365 days');
    }
  } catch (e) {
    errors.push('Invalid date format (use ISO 8601)');
  }

  if (!request.horizons || request.horizons.length === 0) {
    errors.push('At least one horizon must be specified');
  }

  if (!request.variables || request.variables.length === 0) {
    errors.push('At least one variable must be specified');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Poll export status until completion or timeout
 */
export async function pollExportStatus(
  exportId: string,
  onProgress?: (status: ExportStatus) => void,
  timeoutMs: number = 300000 // 5 minutes
): Promise<ExportStatus> {
  const startTime = Date.now();
  const pollInterval = 2000; // 2 seconds

  while (Date.now() - startTime < timeoutMs) {
    const status = await getExportStatus(exportId);
    
    if (onProgress) {
      onProgress(status);
    }

    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }

    if (status.status === 'expired') {
      throw new VersioningApiError('Export expired before completion');
    }

    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  throw new VersioningApiError('Export polling timeout');
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes?: number): string {
  if (!bytes) return 'Unknown size';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Get export type display name
 */
export function getExportTypeDisplayName(exportType: string): string {
  switch (exportType) {
    case 'json':
      return 'JSON Format';
    case 'csv':
      return 'CSV Spreadsheet';
    case 'archive':
      return 'Complete Archive';
    default:
      return exportType.toUpperCase();
  }
}

// ============================================================================
// Export for easy importing
// ============================================================================

export const versioningApi = {
  getForecastVersions,
  getForecastVersionDetail,
  compareForecastVersions,
  searchForecastVersions,
  createExportJob,
  getExportStatus,
  downloadExport,
  getVersionAnalytics,
  pollExportStatus,
};

export const versioningUtils = {
  formatVersionSummary,
  getTimeAgo,
  getRiskLevelColor,
  formatConfidence,
  generateExportFilename,
  validateComparisonRequest,
  validateExportRequest,
  formatFileSize,
  getExportTypeDisplayName,
};