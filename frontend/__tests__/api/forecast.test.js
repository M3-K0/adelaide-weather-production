/**
 * Frontend API Proxy Tests
 * Tests the server-side API proxy route for security and functionality
 */

import { createMocks } from 'node-mocks-http';
import { GET } from '../../app/api/forecast/route';

// Mock environment variables
const originalEnv = process.env;

beforeEach(() => {
  jest.resetModules();
  process.env = {
    ...originalEnv,
    API_TOKEN: 'test-secure-token',
    API_BASE_URL: 'http://localhost:8000'
  };
});

afterEach(() => {
  process.env = originalEnv;
});

// Mock fetch globally
global.fetch = jest.fn();

describe('/api/forecast API Proxy', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('should proxy request with authentication', async () => {
    // Mock successful API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        horizon: '6h',
        variables: {
          t2m: {
            value: 20.5,
            p05: 18.0,
            p95: 23.0,
            confidence: 85,
            available: true,
            analog_count: 50
          }
        },
        wind10m: { speed: 12.5, direction: 180 },
        timestamp: '2025-10-26T20:00:00Z',
        latency_ms: 45
      })
    });

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    // Verify fetch was called with correct parameters
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/forecast?horizon=6h&vars=t2m',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-secure-token',
          'Content-Type': 'application/json'
        })
      })
    );

    // Verify response
    expect(response.status).toBe(200);
    expect(data.horizon).toBe('6h');
    expect(data.variables.t2m).toBeDefined();
  });

  test('should validate horizon parameter', async () => {
    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=invalid&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toContain('Invalid horizon');
    expect(fetch).not.toHaveBeenCalled();
  });

  test('should validate variables parameter', async () => {
    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=invalid_var'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toContain('Invalid variables');
    expect(fetch).not.toHaveBeenCalled();
  });

  test('should handle API authentication errors', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized'
    });

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.error).toBe('Authentication failed');
  });

  test('should handle API rate limiting', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests'
    });

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(429);
    expect(data.error).toContain('Rate limit exceeded');
  });

  test('should handle API timeout', async () => {
    fetch.mockRejectedValueOnce(new Error('AbortError'));

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(504);
    expect(data.error).toContain('timeout');
  });

  test('should handle network errors', async () => {
    fetch.mockRejectedValueOnce(new Error('Network error'));

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);
    const data = await response.json();

    expect(response.status).toBe(503);
    expect(data.error).toContain('unavailable');
  });

  test('should include security headers', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ horizon: '6h' })
    });

    const { req } = createMocks({
      method: 'GET',
      url: '/api/forecast?horizon=6h&vars=t2m'
    });

    const response = await GET(req);

    // Check security headers
    expect(response.headers.get('Cache-Control')).toBe('public, max-age=300');
    expect(response.headers.get('Access-Control-Allow-Origin')).toBe('*');
  });

  test('should fail when API_TOKEN missing', async () => {
    delete process.env.API_TOKEN;

    // This should cause the module to exit, but in test we'll catch the error
    expect(() => {
      require('../../app/api/forecast/route');
    }).toThrow();
  });
});

describe('CORS Handling', () => {
  test('should handle OPTIONS preflight request', async () => {
    const { req } = createMocks({
      method: 'OPTIONS'
    });

    // Import the OPTIONS handler
    const { OPTIONS } = require('../../app/api/forecast/route');
    const response = await OPTIONS();

    expect(response.status).toBe(200);
    expect(response.headers.get('Access-Control-Allow-Methods')).toContain(
      'GET'
    );
    expect(response.headers.get('Access-Control-Allow-Headers')).toContain(
      'Content-Type'
    );
  });
});
