/**
 * K6 Load Testing Script: Complex User Journeys
 * 
 * Advanced user behavior simulation for Adelaide Weather Forecasting System
 * Tests realistic user patterns, error handling, and system resilience
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

// Custom metrics for detailed analysis
const apiResponseTime = new Trend('api_response_time');
const frontendResponseTime = new Trend('frontend_response_time');
const errorRate = new Rate('error_rate');
const cacheHitRate = new Rate('cache_hit_rate');
const forecastAccuracy = new Trend('forecast_accuracy_score');
const userSessionDuration = new Trend('user_session_duration');
const apiCallsPerSession = new Counter('api_calls_per_session');

// Test configuration with progressive load phases
export const options = {
  stages: [
    // Ramp-up phase
    { duration: '2m', target: 10 },   // Baseline load
    { duration: '5m', target: 50 },   // Target load  
    { duration: '3m', target: 100 },  // Stress load
    { duration: '2m', target: 200 },  // Spike load
    { duration: '1m', target: 300 },  // Break point
    { duration: '3m', target: 50 },   // Recovery
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  
  // Thresholds for SLA compliance
  thresholds: {
    'http_req_duration': ['p(95)<2000', 'p(99)<5000'], // 95% under 2s, 99% under 5s
    'http_req_failed': ['rate<0.01'],                   // <1% error rate
    'api_response_time': ['p(90)<1500'],                // API 90% under 1.5s
    'frontend_response_time': ['p(90)<3000'],           // Frontend 90% under 3s
    'error_rate': ['rate<0.005'],                       // <0.5% error rate
    'cache_hit_rate': ['rate>0.60'],                    // >60% cache hit rate
  },

  // Browser simulation options
  userAgent: 'K6-LoadTest/1.0 (Weather-Forecast-Testing)',
  
  // Test data and environment
  ext: {
    loadimpact: {
      distribution: {
        'amazon:us:ashburn': { loadZone: 'amazon:us:ashburn', percent: 25 },
        'amazon:us:portland': { loadZone: 'amazon:us:portland', percent: 25 },
        'amazon:eu:dublin': { loadZone: 'amazon:eu:dublin', percent: 25 },
        'amazon:ap:sydney': { loadZone: 'amazon:ap:sydney', percent: 25 },
      }
    }
  }
};

// Test configuration
const config = {
  api_base: __ENV.API_BASE || 'http://localhost:8000',
  frontend_base: __ENV.FRONTEND_BASE || 'http://localhost:3000',
  api_token: __ENV.API_TOKEN || 'dev-token-change-in-production',
  test_duration: parseInt(__ENV.TEST_DURATION) || 300, // 5 minutes default
};

// Test data sets for realistic simulation
const weatherVariables = [
  ['t2m'],
  ['t2m', 'u10', 'v10'],
  ['t2m', 'u10', 'v10', 'msl'],
  ['t2m', 'u10', 'v10', 'msl', 'cape'],
  ['t2m', 'u10', 'v10', 'msl', 'z500', 't850', 'q850', 'u850', 'v850', 'cape']
];

const forecastHorizons = ['6h', '12h', '24h', '48h'];

const userProfiles = [
  { name: 'casual_user', api_weight: 0.3, session_duration: 120 },
  { name: 'power_user', api_weight: 0.7, session_duration: 300 },
  { name: 'meteorologist', api_weight: 0.9, session_duration: 600 },
  { name: 'mobile_user', api_weight: 0.4, session_duration: 90 },
  { name: 'api_consumer', api_weight: 1.0, session_duration: 30 },
];

/**
 * Setup function - runs once per VU
 */
export function setup() {
  console.log(`🚀 Starting K6 load test with ${config.test_duration}s duration`);
  console.log(`📊 API Base: ${config.api_base}`);
  console.log(`🌐 Frontend Base: ${config.frontend_base}`);
  
  // Validate test environment
  const healthCheck = http.get(`${config.api_base}/health`);
  if (!check(healthCheck, { 'API health check passed': (r) => r.status === 200 })) {
    throw new Error('API health check failed - aborting test');
  }
  
  const frontendCheck = http.get(`${config.frontend_base}/`);
  if (!check(frontendCheck, { 'Frontend health check passed': (r) => r.status === 200 })) {
    throw new Error('Frontend health check failed - aborting test');
  }
  
  return { 
    api_ready: true, 
    frontend_ready: true,
    test_start_time: new Date().toISOString()
  };
}

/**
 * Main test function - realistic user journey simulation
 */
export default function(data) {
  const sessionStart = new Date();
  const userProfile = userProfiles[Math.floor(Math.random() * userProfiles.length)];
  const sessionId = `session_${__VU}_${__ITER}`;
  
  console.log(`👤 Starting ${userProfile.name} session: ${sessionId}`);

  // User journey simulation based on profile
  group('User Session Journey', () => {
    
    // Journey 1: Weather Dashboard Access (Most Common)
    if (Math.random() < 0.8) {
      group('Weather Dashboard Access', () => {
        weatherDashboardJourney(userProfile, sessionId);
      });
    }
    
    // Journey 2: Meteorologist Analysis (Power Users)
    if (userProfile.name === 'meteorologist' && Math.random() < 0.6) {
      group('Meteorologist Analysis', () => {
        meteorologistAnalysisJourney(userProfile, sessionId);
      });
    }
    
    // Journey 3: Mobile Quick Check (Mobile Users)
    if (userProfile.name === 'mobile_user' && Math.random() < 0.9) {
      group('Mobile Quick Check', () => {
        mobileQuickCheckJourney(userProfile, sessionId);
      });
    }
    
    // Journey 4: API Integration Testing (API Consumers)
    if (userProfile.name === 'api_consumer') {
      group('API Integration', () => {
        apiIntegrationJourney(userProfile, sessionId);
      });
    }
    
    // Journey 5: Error Recovery Testing (Random)
    if (Math.random() < 0.1) {
      group('Error Recovery', () => {
        errorRecoveryJourney(userProfile, sessionId);
      });
    }
  });

  // Calculate session metrics
  const sessionEnd = new Date();
  const sessionDuration = (sessionEnd - sessionStart) / 1000;
  userSessionDuration.add(sessionDuration);
  
  console.log(`✅ Completed ${userProfile.name} session: ${sessionId} (${sessionDuration}s)`);
  
  // Think time between sessions
  sleep(Math.random() * 5 + 1);
}

/**
 * Weather Dashboard Journey - Most common user pattern
 */
function weatherDashboardJourney(userProfile, sessionId) {
  // 1. Load main dashboard
  const dashboardResponse = http.get(`${config.frontend_base}/`, {
    headers: { 'User-Agent': getUserAgent(userProfile) },
    tags: { journey: 'dashboard', session: sessionId }
  });
  
  check(dashboardResponse, {
    'Dashboard loads successfully': (r) => r.status === 200,
    'Dashboard response time < 3s': (r) => r.timings.duration < 3000,
  });
  
  frontendResponseTime.add(dashboardResponse.timings.duration);
  
  // Think time - user reads dashboard
  sleep(2 + Math.random() * 3);
  
  // 2. Get current weather forecast
  const horizon = forecastHorizons[Math.floor(Math.random() * forecastHorizons.length)];
  const variables = weatherVariables[Math.floor(Math.random() * weatherVariables.length)];
  
  const forecastResponse = http.get(`${config.api_base}/forecast`, {
    headers: { 
      'Authorization': `Bearer ${config.api_token}`,
      'User-Agent': getUserAgent(userProfile)
    },
    params: {
      horizon: horizon,
      vars: variables.join(',')
    },
    tags: { journey: 'dashboard', session: sessionId, api_call: 'forecast' }
  });
  
  const forecastSuccess = check(forecastResponse, {
    'Forecast API responds': (r) => r.status === 200,
    'Forecast has variables': (r) => r.json('variables') !== undefined,
    'Forecast response time < 2s': (r) => r.timings.duration < 2000,
    'Forecast has narrative': (r) => r.json('narrative') !== undefined,
  });
  
  apiResponseTime.add(forecastResponse.timings.duration);
  apiCallsPerSession.add(1);
  
  if (!forecastSuccess) {
    errorRate.add(1);
  } else {
    errorRate.add(0);
    
    // Check for cache headers
    const cacheHeader = forecastResponse.headers['x-cache-status'];
    cacheHitRate.add(cacheHeader === 'hit' ? 1 : 0);
    
    // Simulate forecast accuracy scoring (would be real in production)
    const latency = forecastResponse.json('latency_ms');
    const analogCount = forecastResponse.json('analogs_summary.analog_count');
    const accuracyScore = Math.min(100, 50 + (analogCount || 0) + (latency < 1000 ? 20 : 0));
    forecastAccuracy.add(accuracyScore);
  }
  
  // Think time - user analyzes results
  sleep(5 + Math.random() * 5);
  
  // 3. Interactive exploration (based on user profile)
  if (Math.random() < userProfile.api_weight) {
    // Power users explore more data
    exploreAdditionalForecasts(userProfile, sessionId);
  }
}

/**
 * Meteorologist Analysis Journey - Deep technical analysis
 */
function meteorologistAnalysisJourney(userProfile, sessionId) {
  console.log(`🔬 Meteorologist analysis session: ${sessionId}`);
  
  // 1. Load analog demo page
  const analogResponse = http.get(`${config.frontend_base}/analog-demo`, {
    tags: { journey: 'meteorologist', session: sessionId }
  });
  
  check(analogResponse, {
    'Analog demo loads': (r) => r.status === 200,
  });
  
  sleep(3);
  
  // 2. Comprehensive forecast analysis - all horizons
  for (const horizon of forecastHorizons) {
    const detailedForecast = http.get(`${config.api_base}/forecast`, {
      headers: { 'Authorization': `Bearer ${config.api_token}` },
      params: {
        horizon: horizon,
        vars: 't2m,u10,v10,msl,z500,t850,q850,u850,v850,cape'
      },
      tags: { journey: 'meteorologist', session: sessionId, horizon: horizon }
    });
    
    check(detailedForecast, {
      [`${horizon} forecast success`]: (r) => r.status === 200,
      [`${horizon} has CAPE data`]: (r) => r.json('variables.cape') !== undefined,
    });
    
    apiCallsPerSession.add(1);
    sleep(2);
  }
  
  // 3. CAPE analysis demo
  const capeResponse = http.get(`${config.frontend_base}/cape-demo`, {
    tags: { journey: 'meteorologist', session: sessionId }
  });
  
  check(capeResponse, {
    'CAPE demo loads': (r) => r.status === 200,
  });
  
  sleep(10); // Meteorologists spend time analyzing
}

/**
 * Mobile Quick Check Journey - Optimized for mobile
 */
function mobileQuickCheckJourney(userProfile, sessionId) {
  console.log(`📱 Mobile quick check session: ${sessionId}`);
  
  // Mobile-optimized requests
  const mobileHeaders = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate'
  };
  
  // Quick dashboard load
  const mobileResponse = http.get(`${config.frontend_base}/`, {
    headers: mobileHeaders,
    tags: { journey: 'mobile', session: sessionId }
  });
  
  check(mobileResponse, {
    'Mobile dashboard loads': (r) => r.status === 200,
    'Mobile response time < 5s': (r) => r.timings.duration < 5000,
  });
  
  sleep(1);
  
  // Quick forecast check - minimal data
  const quickForecast = http.get(`${config.api_base}/forecast`, {
    headers: { 
      'Authorization': `Bearer ${config.api_token}`,
      ...mobileHeaders
    },
    params: {
      horizon: '6h',
      vars: 't2m,u10,v10'
    },
    tags: { journey: 'mobile', session: sessionId }
  });
  
  check(quickForecast, {
    'Mobile forecast success': (r) => r.status === 200,
    'Mobile forecast fast': (r) => r.timings.duration < 1500,
  });
  
  apiCallsPerSession.add(1);
}

/**
 * API Integration Journey - Direct API usage
 */
function apiIntegrationJourney(userProfile, sessionId) {
  console.log(`🔌 API integration session: ${sessionId}`);
  
  // Simulate automated API client behavior
  const apiTests = [
    { horizon: '24h', vars: 't2m,u10,v10,msl' },
    { horizon: '48h', vars: 't2m,cape' },
    { horizon: '6h', vars: 't2m,u10,v10,msl,z500,t850,q850,u850,v850,cape' },
  ];
  
  for (const test of apiTests) {
    const apiResponse = http.get(`${config.api_base}/forecast`, {
      headers: { 
        'Authorization': `Bearer ${config.api_token}`,
        'Accept': 'application/json',
        'User-Agent': 'WeatherBot/1.0'
      },
      params: test,
      tags: { journey: 'api', session: sessionId, test: `${test.horizon}_${test.vars}` }
    });
    
    check(apiResponse, {
      'API response valid': (r) => r.status === 200,
      'API response has data': (r) => r.json('variables') !== undefined,
      'API response fast': (r) => r.timings.duration < 1000,
    });
    
    apiCallsPerSession.add(1);
    sleep(0.5); // Rapid API calls
  }
}

/**
 * Error Recovery Journey - Test resilience
 */
function errorRecoveryJourney(userProfile, sessionId) {
  console.log(`⚠️  Error recovery session: ${sessionId}`);
  
  // 1. Invalid request testing
  const invalidRequest = http.get(`${config.api_base}/forecast`, {
    headers: { 'Authorization': `Bearer ${config.api_token}` },
    params: {
      horizon: 'invalid',
      vars: 'invalid_var'
    },
    tags: { journey: 'error', session: sessionId, test: 'invalid_params' }
  });
  
  check(invalidRequest, {
    'Invalid request handled': (r) => r.status === 400,
    'Error message present': (r) => r.json('error') !== undefined,
  });
  
  // 2. Missing auth testing
  const noAuthRequest = http.get(`${config.api_base}/forecast`, {
    params: { horizon: '24h', vars: 't2m' },
    tags: { journey: 'error', session: sessionId, test: 'no_auth' }
  });
  
  check(noAuthRequest, {
    'No auth handled': (r) => r.status === 403,
  });
  
  // 3. Rate limit testing (rapid requests)
  for (let i = 0; i < 5; i++) {
    const rapidRequest = http.get(`${config.api_base}/forecast`, {
      headers: { 'Authorization': `Bearer ${config.api_token}` },
      params: { horizon: '6h', vars: 't2m' },
      tags: { journey: 'error', session: sessionId, test: 'rate_limit' }
    });
    
    // Should succeed until rate limit
    if (rapidRequest.status === 429) {
      console.log('✅ Rate limit triggered as expected');
      break;
    }
  }
}

/**
 * Additional forecast exploration for power users
 */
function exploreAdditionalForecasts(userProfile, sessionId) {
  const explorationTests = Math.floor(Math.random() * 3) + 1;
  
  for (let i = 0; i < explorationTests; i++) {
    const horizon = forecastHorizons[Math.floor(Math.random() * forecastHorizons.length)];
    const variables = weatherVariables[Math.floor(Math.random() * weatherVariables.length)];
    
    const explorationResponse = http.get(`${config.api_base}/forecast`, {
      headers: { 'Authorization': `Bearer ${config.api_token}` },
      params: {
        horizon: horizon,
        vars: variables.join(',')
      },
      tags: { journey: 'exploration', session: sessionId }
    });
    
    check(explorationResponse, {
      'Exploration request success': (r) => r.status === 200,
    });
    
    apiCallsPerSession.add(1);
    sleep(2);
  }
}

/**
 * Generate user agent based on profile
 */
function getUserAgent(userProfile) {
  const userAgents = {
    'casual_user': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'power_user': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'meteorologist': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'mobile_user': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'api_consumer': 'WeatherAPI-Client/1.0 (automated)'
  };
  
  return userAgents[userProfile.name] || userAgents['casual_user'];
}

/**
 * Teardown function - runs once at the end
 */
export function teardown(data) {
  console.log(`🏁 K6 load test completed`);
  console.log(`📊 Test started at: ${data.test_start_time}`);
  console.log(`📈 Check detailed metrics in the HTML report`);
}

/**
 * Generate HTML report
 */
export function handleSummary(data) {
  return {
    'load-test-report.html': htmlReport(data),
    'load-test-summary.json': JSON.stringify(data, null, 2),
  };
}