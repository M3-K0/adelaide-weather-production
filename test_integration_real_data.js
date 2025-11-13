#!/usr/bin/env node
/**
 * API Integration Test with Real Data
 * Tests the complete integration between frontend and backend with real data
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

// Test configuration
const API_BASE = 'http://localhost:8000';
const VALID_TOKEN = 'dev-token-change-in-production';

class IntegrationTester {
  constructor() {
    this.passed = 0;
    this.failed = 0;
    this.results = [];
  }

  async request(method, url, headers = {}, body = null) {
    return new Promise((resolve, reject) => {
      const urlObj = new URL(url);
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
        path: urlObj.pathname + urlObj.search,
        method: method.toUpperCase(),
        headers: headers
      };

      const req = (urlObj.protocol === 'https:' ? https : http).request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          try {
            const jsonData = data ? JSON.parse(data) : {};
            resolve({ status: res.statusCode, data: jsonData, headers: res.headers });
          } catch (e) {
            resolve({ status: res.statusCode, data: data, headers: res.headers });
          }
        });
      });

      req.on('error', reject);
      if (body) req.write(body);
      req.end();
    });
  }

  assert(condition, message) {
    if (condition) {
      this.passed++;
      console.log(`✓ ${message}`);
    } else {
      this.failed++;
      console.log(`✗ ${message}`);
    }
    this.results.push({ passed: condition, message });
  }

  async runTests() {
    console.log('🚀 Starting API Integration Tests with Real Data\n');

    await this.testHealthEndpoint();
    await this.testAuthentication();
    await this.testForecastEndpoints();
    await this.testErrorHandling();
    await this.testPerformance();

    console.log('\n📊 Test Results Summary:');
    console.log(`✅ Passed: ${this.passed}`);
    console.log(`❌ Failed: ${this.failed}`);
    console.log(`📈 Success Rate: ${(this.passed / (this.passed + this.failed) * 100).toFixed(1)}%`);

    if (this.failed > 0) {
      console.log('\n❌ Failed Tests:');
      this.results.filter(r => !r.passed).forEach(r => console.log(`  - ${r.message}`));
      process.exit(1);
    } else {
      console.log('\n🎉 All tests passed!');
      process.exit(0);
    }
  }

  async testHealthEndpoint() {
    console.log('🏥 Testing Health Endpoint...');
    
    try {
      const response = await this.request('GET', `${API_BASE}/health`);
      
      this.assert(response.status === 200, 'Health endpoint returns 200 status');
      this.assert(response.data.status === 'healthy', 'Health status is healthy');
      this.assert(typeof response.data.uptime_seconds === 'number', 'Uptime is a number');
      this.assert(response.data.version === '1.0.0-test', 'Version matches expected');
    } catch (error) {
      this.assert(false, `Health endpoint request failed: ${error.message}`);
    }
  }

  async testAuthentication() {
    console.log('\n🔐 Testing Authentication...');
    
    // Test unauthenticated request
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=t2m`);
      this.assert(response.status === 403, 'Unauthenticated request returns 403');
    } catch (error) {
      this.assert(false, `Authentication test failed: ${error.message}`);
    }

    // Test valid token
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=t2m`, {
        'Authorization': `Bearer ${VALID_TOKEN}`
      });
      this.assert(response.status === 200, 'Valid token allows access');
    } catch (error) {
      this.assert(false, `Valid token test failed: ${error.message}`);
    }

    // Test invalid token
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=t2m`, {
        'Authorization': 'Bearer invalid-token-xyz'
      });
      this.assert([401, 403].includes(response.status), 'Invalid token is rejected');
    } catch (error) {
      this.assert(false, `Invalid token test failed: ${error.message}`);
    }
  }

  async testForecastEndpoints() {
    console.log('\n🌤️ Testing Forecast Endpoints with Real Data...');
    
    // Test all horizons
    const horizons = ['6h', '12h', '24h', '48h'];
    
    for (const horizon of horizons) {
      try {
        const response = await this.request('GET', `${API_BASE}/forecast?horizon=${horizon}&vars=t2m,u10,v10`, {
          'Authorization': `Bearer ${VALID_TOKEN}`
        });
        
        this.assert(response.status === 200, `Forecast works for horizon ${horizon}`);
        this.assert(response.data.horizon === horizon, `Response horizon matches request for ${horizon}`);
        this.assert(response.data.variables && response.data.variables.t2m, `t2m variable present for ${horizon}`);
        this.assert(response.data.variables && response.data.variables.u10, `u10 variable present for ${horizon}`);
        this.assert(response.data.variables && response.data.variables.v10, `v10 variable present for ${horizon}`);
        
        // Check variable structure
        const t2m = response.data.variables.t2m;
        this.assert(typeof t2m.value === 'number', `t2m value is numeric for ${horizon}`);
        this.assert(typeof t2m.confidence === 'number', `t2m confidence is numeric for ${horizon}`);
        this.assert(t2m.confidence >= 0 && t2m.confidence <= 100, `t2m confidence in valid range for ${horizon}`);
        this.assert(typeof t2m.available === 'boolean', `t2m availability is boolean for ${horizon}`);
        
        // Check wind calculation when u10/v10 present
        if (response.data.wind10m) {
          this.assert(typeof response.data.wind10m.speed === 'number', `Wind speed calculated for ${horizon}`);
          this.assert(typeof response.data.wind10m.direction === 'number', `Wind direction calculated for ${horizon}`);
          this.assert(response.data.wind10m.speed >= 0, `Wind speed non-negative for ${horizon}`);
          this.assert(response.data.wind10m.direction >= 0 && response.data.wind10m.direction < 360, `Wind direction valid for ${horizon}`);
        }
        
      } catch (error) {
        this.assert(false, `Forecast test for ${horizon} failed: ${error.message}`);
      }
    }
    
    // Test variable selection
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=t2m,cape`, {
        'Authorization': `Bearer ${VALID_TOKEN}`
      });
      
      this.assert(response.status === 200, 'Variable selection works');
      this.assert(response.data.variables && response.data.variables.t2m, 't2m variable present in selection');
      this.assert(response.data.variables && response.data.variables.cape, 'CAPE variable present in selection');
      
    } catch (error) {
      this.assert(false, `Variable selection test failed: ${error.message}`);
    }
  }

  async testErrorHandling() {
    console.log('\n🚨 Testing Error Handling...');
    
    // Test invalid horizon
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=72h&vars=t2m`, {
        'Authorization': `Bearer ${VALID_TOKEN}`
      });
      
      this.assert(response.status === 400, 'Invalid horizon returns 400');
      this.assert(response.data.detail && response.data.detail.toLowerCase().includes('horizon'), 'Error message mentions horizon');
    } catch (error) {
      this.assert(false, `Invalid horizon test failed: ${error.message}`);
    }

    // Test invalid variable
    try {
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=invalid_var`, {
        'Authorization': `Bearer ${VALID_TOKEN}`
      });
      
      this.assert(response.status === 400, 'Invalid variable returns 400');
      this.assert(response.data.detail && response.data.detail.toLowerCase().includes('variable'), 'Error message mentions variable');
    } catch (error) {
      this.assert(false, `Invalid variable test failed: ${error.message}`);
    }
  }

  async testPerformance() {
    console.log('\n⚡ Testing Performance...');
    
    try {
      const startTime = Date.now();
      const response = await this.request('GET', `${API_BASE}/forecast?horizon=6h&vars=t2m,u10,v10`, {
        'Authorization': `Bearer ${VALID_TOKEN}`
      });
      const endTime = Date.now();
      
      const responseTime = endTime - startTime;
      
      this.assert(response.status === 200, 'Performance test forecast succeeds');
      this.assert(responseTime < 5000, `Response time under 5s (${responseTime}ms)`);
      this.assert(responseTime < 2000, `Response time under 2s (${responseTime}ms)`);
      this.assert(response.data.latency_ms && response.data.latency_ms < 2000, 'Internal latency under 2s');
      
    } catch (error) {
      this.assert(false, `Performance test failed: ${error.message}`);
    }
  }
}

// Run the tests
const tester = new IntegrationTester();
tester.runTests().catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});