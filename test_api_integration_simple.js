#!/usr/bin/env node
/**
 * Simple API Integration Test
 * Tests real data integration with running backend
 */

const { test, expect } = require('@playwright/test');

// Test configuration
const API_BASE = 'http://localhost:8000';
const VALID_TOKEN = 'dev-token-change-in-production';

test.describe('API Integration Tests with Real Backend', () => {
  test('health endpoint responds correctly', async ({ request }) => {
    const response = await request.get(`${API_BASE}/health`);
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('timestamp');
    expect(data).toHaveProperty('uptime_seconds');
  });

  test('authenticated forecast request works', async ({ request }) => {
    const response = await request.get(`${API_BASE}/forecast?horizon=6h&vars=t2m`, {
      headers: {
        'Authorization': `Bearer ${VALID_TOKEN}`
      }
    });
    
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('horizon', '6h');
    expect(data).toHaveProperty('variables');
    expect(data).toHaveProperty('timestamp');
    expect(data).toHaveProperty('latency_ms');
    
    // Check t2m variable structure
    expect(data.variables).toHaveProperty('t2m');
    const t2m = data.variables.t2m;
    expect(t2m).toHaveProperty('value');
    expect(t2m).toHaveProperty('p05');
    expect(t2m).toHaveProperty('p95');
    expect(t2m).toHaveProperty('confidence');
    expect(t2m).toHaveProperty('available');
  });

  test('unauthenticated request is rejected', async ({ request }) => {
    const response = await request.get(`${API_BASE}/forecast?horizon=6h&vars=t2m`);
    expect(response.status()).toBe(403);
  });

  test('invalid horizon returns error', async ({ request }) => {
    const response = await request.get(`${API_BASE}/forecast?horizon=72h&vars=t2m`, {
      headers: {
        'Authorization': `Bearer ${VALID_TOKEN}`
      }
    });
    
    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data).toHaveProperty('detail');
    expect(data.detail).toContain('horizon');
  });

  test('forecast for all horizons works', async ({ request }) => {
    const horizons = ['6h', '12h', '24h', '48h'];
    
    for (const horizon of horizons) {
      const response = await request.get(`${API_BASE}/forecast?horizon=${horizon}&vars=t2m,u10,v10`, {
        headers: {
          'Authorization': `Bearer ${VALID_TOKEN}`
        }
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.horizon).toBe(horizon);
      expect(data.variables).toHaveProperty('t2m');
      expect(data.variables).toHaveProperty('u10');
      expect(data.variables).toHaveProperty('v10');
      
      // Should calculate wind10m when u10 and v10 present
      if (data.wind10m) {
        expect(data.wind10m).toHaveProperty('speed');
        expect(data.wind10m).toHaveProperty('direction');
        expect(data.wind10m.speed).toBeGreaterThanOrEqual(0);
        expect(data.wind10m.direction).toBeGreaterThanOrEqual(0);
        expect(data.wind10m.direction).toBeLessThan(360);
      }
    }
  });

  test('metrics endpoint works with authentication', async ({ request }) => {
    const response = await request.get(`${API_BASE}/metrics`);
    expect(response.status()).toBe(200);
    
    const metricsText = await response.text();
    expect(metricsText).toContain('# HELP');
    expect(metricsText).toContain('# TYPE');
  });
});

console.log('Running API integration tests...');