#!/usr/bin/env node

/**
 * System Health Check for Performance Testing
 * Validates that all services are ready for performance testing
 */

const axios = require('axios');
const { performance } = require('perf_hooks');

class HealthChecker {
  constructor(config = {}) {
    this.apiUrl = config.apiUrl || process.env.API_URL || 'http://localhost:8000';
    this.frontendUrl = config.frontendUrl || process.env.FRONTEND_URL || 'http://localhost:3000';
    this.timeout = config.timeout || 10000;
    this.retries = config.retries || 3;
    
    this.results = {
      api: { healthy: false, responseTime: 0, details: {} },
      frontend: { healthy: false, responseTime: 0, details: {} },
      database: { healthy: false, responseTime: 0, details: {} },
      cache: { healthy: false, responseTime: 0, details: {} },
      overall: { healthy: false, readyForTesting: false }
    };
  }

  async checkAllServices() {
    console.log('🏥 Starting system health check...');
    console.log(`API: ${this.apiUrl}`);
    console.log(`Frontend: ${this.frontendUrl}`);
    
    const checks = await Promise.allSettled([
      this.checkAPI(),
      this.checkFrontend(),
      this.checkDatabase(),
      this.checkCache()
    ]);
    
    this.evaluateOverallHealth();
    this.printResults();
    
    return this.results;
  }

  async checkAPI() {
    console.log('📡 Checking API health...');
    
    try {
      // Basic health check
      const healthStart = performance.now();
      const healthResponse = await axios.get(`${this.apiUrl}/health`, {
        timeout: this.timeout,
        validateStatus: () => true
      });
      const healthTime = performance.now() - healthStart;
      
      this.results.api.responseTime = healthTime;
      this.results.api.details.healthEndpoint = {
        status: healthResponse.status,
        responseTime: healthTime,
        data: healthResponse.data
      };
      
      // Test forecast endpoint
      const forecastStart = performance.now();
      const forecastResponse = await axios.get(`${this.apiUrl}/forecast?horizon=24h&vars=t2m`, {
        timeout: this.timeout,
        validateStatus: () => true,
        headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'dev-token'}` }
      });
      const forecastTime = performance.now() - forecastStart;
      
      this.results.api.details.forecastEndpoint = {
        status: forecastResponse.status,
        responseTime: forecastTime,
        hasData: !!forecastResponse.data?.forecast
      };
      
      // Test performance endpoint
      try {
        const perfResponse = await axios.get(`${this.apiUrl}/performance`, {
          timeout: this.timeout,
          validateStatus: () => true
        });
        this.results.api.details.performanceEndpoint = {
          status: perfResponse.status,
          data: perfResponse.data
        };
      } catch (error) {
        this.results.api.details.performanceEndpoint = {
          error: error.message
        };
      }
      
      // Evaluate API health
      this.results.api.healthy = 
        healthResponse.status === 200 &&
        healthResponse.data?.status === 'healthy' &&
        forecastResponse.status === 200 &&
        forecastResponse.data?.forecast &&
        healthTime < 1000 &&
        forecastTime < 2000;
      
      console.log(`  Health endpoint: ${healthResponse.status} (${healthTime.toFixed(2)}ms)`);
      console.log(`  Forecast endpoint: ${forecastResponse.status} (${forecastTime.toFixed(2)}ms)`);
      
    } catch (error) {
      console.log(`  ❌ API check failed: ${error.message}`);
      this.results.api.details.error = error.message;
      this.results.api.healthy = false;
    }
  }

  async checkFrontend() {
    console.log('🌐 Checking frontend health...');
    
    try {
      const start = performance.now();
      const response = await axios.get(this.frontendUrl, {
        timeout: this.timeout,
        validateStatus: () => true,
        headers: {
          'User-Agent': 'HealthChecker/1.0'
        }
      });
      const responseTime = performance.now() - start;
      
      this.results.frontend.responseTime = responseTime;
      this.results.frontend.details.status = response.status;
      this.results.frontend.details.responseTime = responseTime;
      
      // Check if response contains expected content
      const hasExpectedContent = response.data && 
        (response.data.includes('Adelaide Weather') || 
         response.data.includes('weather') ||
         response.data.includes('forecast'));
      
      this.results.frontend.details.hasExpectedContent = hasExpectedContent;
      this.results.frontend.details.contentLength = response.data?.length || 0;
      
      this.results.frontend.healthy = 
        response.status === 200 &&
        responseTime < 3000 &&
        hasExpectedContent;
      
      console.log(`  Status: ${response.status} (${responseTime.toFixed(2)}ms)`);
      console.log(`  Content length: ${response.data?.length || 0} bytes`);
      
    } catch (error) {
      console.log(`  ❌ Frontend check failed: ${error.message}`);
      this.results.frontend.details.error = error.message;
      this.results.frontend.healthy = false;
    }
  }

  async checkDatabase() {
    console.log('🗄️  Checking database health...');
    
    try {
      // Database health is checked through API endpoint that queries the database
      const start = performance.now();
      const response = await axios.get(`${this.apiUrl}/forecast?horizon=6h&vars=t2m`, {
        timeout: this.timeout,
        validateStatus: () => true,
        headers: { 'Authorization': `Bearer ${process.env.API_TOKEN || 'dev-token'}` }
      });
      const responseTime = performance.now() - start;
      
      this.results.database.responseTime = responseTime;
      this.results.database.details.status = response.status;
      this.results.database.details.responseTime = responseTime;
      
      // Check if response indicates successful database query
      const hasValidData = response.data?.forecast?.analogs_count > 0 ||
                          response.data?.forecast?.variables?.length > 0;
      
      this.results.database.details.hasValidData = hasValidData;
      this.results.database.details.analogsCount = response.data?.forecast?.analogs_count || 0;
      
      this.results.database.healthy = 
        response.status === 200 &&
        hasValidData &&
        responseTime < 3000;
      
      console.log(`  Database query: ${response.status} (${responseTime.toFixed(2)}ms)`);
      console.log(`  Analogs found: ${response.data?.forecast?.analogs_count || 0}`);
      
    } catch (error) {
      console.log(`  ❌ Database check failed: ${error.message}`);
      this.results.database.details.error = error.message;
      this.results.database.healthy = false;
    }
  }

  async checkCache() {
    console.log('🗃️  Checking cache health...');
    
    try {
      // Check cache through performance endpoint
      const response = await axios.get(`${this.apiUrl}/performance`, {
        timeout: this.timeout,
        validateStatus: () => true
      });
      
      this.results.cache.details.status = response.status;
      
      if (response.status === 200 && response.data?.cache) {
        const cacheData = response.data.cache;
        
        this.results.cache.details.hitRate = cacheData.hit_rate_percent;
        this.results.cache.details.totalRequests = cacheData.total_requests;
        this.results.cache.details.memoryUsage = cacheData.memory_usage_kb;
        
        // Cache is healthy if performance endpoint responds and has reasonable metrics
        this.results.cache.healthy = 
          cacheData.hit_rate_percent >= 0 &&
          cacheData.total_requests >= 0;
        
        console.log(`  Hit rate: ${cacheData.hit_rate_percent?.toFixed(1) || 'N/A'}%`);
        console.log(`  Total requests: ${cacheData.total_requests || 0}`);
        console.log(`  Memory usage: ${cacheData.memory_usage_kb?.toFixed(1) || 'N/A'}KB`);
        
      } else {
        this.results.cache.healthy = false;
        this.results.cache.details.error = `Performance endpoint returned ${response.status}`;
      }
      
    } catch (error) {
      console.log(`  ❌ Cache check failed: ${error.message}`);
      this.results.cache.details.error = error.message;
      this.results.cache.healthy = false;
    }
  }

  evaluateOverallHealth() {
    const criticalServices = [
      this.results.api.healthy,
      this.results.database.healthy
    ];
    
    const allServices = [
      ...criticalServices,
      this.results.frontend.healthy,
      this.results.cache.healthy
    ];
    
    // Overall healthy if all critical services are healthy
    this.results.overall.healthy = criticalServices.every(healthy => healthy);
    
    // Ready for testing if all services are healthy
    this.results.overall.readyForTesting = allServices.every(healthy => healthy);
    
    // Calculate health score
    const healthyCount = allServices.filter(healthy => healthy).length;
    this.results.overall.healthScore = (healthyCount / allServices.length) * 100;
    
    // Performance readiness indicators
    this.results.overall.performanceReadiness = {
      apiResponseTime: this.results.api.responseTime < 500,
      frontendResponseTime: this.results.frontend.responseTime < 2000,
      databaseResponseTime: this.results.database.responseTime < 1000,
      allEndpointsAccessible: this.results.api.healthy && this.results.frontend.healthy
    };
  }

  printResults() {
    console.log('\n🏥 Health Check Results');
    console.log('='.repeat(50));
    
    const services = [
      { name: 'API', result: this.results.api },
      { name: 'Frontend', result: this.results.frontend },
      { name: 'Database', result: this.results.database },
      { name: 'Cache', result: this.results.cache }
    ];
    
    services.forEach(({ name, result }) => {
      const status = result.healthy ? '✅' : '❌';
      const responseTime = result.responseTime ? ` (${result.responseTime.toFixed(2)}ms)` : '';
      console.log(`${status} ${name}${responseTime}`);
      
      if (!result.healthy && result.details.error) {
        console.log(`    Error: ${result.details.error}`);
      }
    });
    
    console.log('\n📊 Overall Status:');
    console.log(`Health Score: ${this.results.overall.healthScore.toFixed(1)}%`);
    console.log(`Ready for Testing: ${this.results.overall.readyForTesting ? '✅' : '❌'}`);
    
    if (this.results.overall.readyForTesting) {
      console.log('\n🚀 System is ready for performance testing!');
    } else {
      console.log('\n⚠️  System not ready for performance testing. Address the issues above.');
      
      // Provide specific recommendations
      const recommendations = [];
      
      if (!this.results.api.healthy) {
        recommendations.push('- Check API service is running on port 8000');
        recommendations.push('- Verify API health endpoint returns valid response');
      }
      
      if (!this.results.frontend.healthy) {
        recommendations.push('- Check frontend service is running on port 3000');
        recommendations.push('- Verify frontend build completed successfully');
      }
      
      if (!this.results.database.healthy) {
        recommendations.push('- Check database connection and data availability');
        recommendations.push('- Verify forecast data is properly loaded');
      }
      
      if (!this.results.cache.healthy) {
        recommendations.push('- Check cache configuration and performance endpoint');
      }
      
      if (recommendations.length > 0) {
        console.log('\n💡 Recommendations:');
        recommendations.forEach(rec => console.log(rec));
      }
    }
    
    // Performance readiness details
    const perfReadiness = this.results.overall.performanceReadiness;
    console.log('\n⚡ Performance Readiness:');
    console.log(`API Response Time: ${perfReadiness.apiResponseTime ? '✅' : '❌'} (< 500ms)`);
    console.log(`Frontend Response Time: ${perfReadiness.frontendResponseTime ? '✅' : '❌'} (< 2000ms)`);
    console.log(`Database Response Time: ${perfReadiness.databaseResponseTime ? '✅' : '❌'} (< 1000ms)`);
    console.log(`All Endpoints Accessible: ${perfReadiness.allEndpointsAccessible ? '✅' : '❌'}`);
  }

  async saveResults() {
    const fs = require('fs');
    const path = require('path');
    
    try {
      const reportsDir = path.join(__dirname, '..', 'reports');
      
      if (!fs.existsSync(reportsDir)) {
        fs.mkdirSync(reportsDir, { recursive: true });
      }
      
      const filename = `health-check-${Date.now()}.json`;
      const filepath = path.join(reportsDir, filename);
      
      const reportData = {
        timestamp: new Date().toISOString(),
        ...this.results
      };
      
      fs.writeFileSync(filepath, JSON.stringify(reportData, null, 2));
      console.log(`💾 Health check results saved to: ${filepath}`);
      
      return filepath;
      
    } catch (error) {
      console.error('Error saving health check results:', error.message);
    }
  }
}

// CLI execution
async function main() {
  const config = {
    apiUrl: process.env.API_URL || 'http://localhost:8000',
    frontendUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
    timeout: parseInt(process.env.TIMEOUT) || 10000,
    retries: parseInt(process.env.RETRIES) || 3
  };
  
  console.log('🏥 Adelaide Weather System Health Checker');
  console.log('=========================================');
  
  const checker = new HealthChecker(config);
  
  try {
    const results = await checker.checkAllServices();
    await checker.saveResults();
    
    // Exit with appropriate code
    if (results.overall.readyForTesting) {
      console.log('\n✅ Health check passed - system ready for performance testing');
      process.exit(0);
    } else if (results.overall.healthy) {
      console.log('\n⚠️  Health check passed with warnings - some non-critical issues detected');
      process.exit(0);
    } else {
      console.log('\n❌ Health check failed - critical issues detected');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('\n💥 Health check failed with error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = HealthChecker;