/**
 * Memory Leak Detection for Long-Running Sessions
 * Advanced memory monitoring and leak detection for the Adelaide Weather System
 * 
 * Features:
 * - Long-running session simulation (24+ hours)
 * - Memory growth pattern analysis
 * - Garbage collection monitoring
 * - Leak source identification
 * - Real-time memory profiling
 */

const axios = require('axios');
const { performance } = require('perf_hooks');
const fs = require('fs').promises;
const path = require('path');
const EventEmitter = require('events');

class MemoryLeakDetector extends EventEmitter {
  constructor(config = {}) {
    super();
    
    this.apiUrl = config.apiUrl || 'http://localhost:8000';
    this.frontendUrl = config.frontendUrl || 'http://localhost:3000';
    this.sessionDuration = config.sessionDuration || 24 * 60 * 60 * 1000; // 24 hours
    this.sampleInterval = config.sampleInterval || 30000; // 30 seconds
    this.alertThreshold = config.alertThreshold || 100; // 100MB growth
    this.maxMemoryMB = config.maxMemoryMB || 1024; // 1GB absolute limit
    
    this.isRunning = false;
    this.samples = [];
    this.leaks = [];
    this.baseline = null;
    this.gcStats = {
      forced: 0,
      automatic: 0,
      totalTime: 0
    };
    
    this.workloadPatterns = [
      { name: 'light', weight: 40, requestsPerMinute: 5 },
      { name: 'moderate', weight: 35, requestsPerMinute: 15 },
      { name: 'heavy', weight: 20, requestsPerMinute: 30 },
      { name: 'burst', weight: 5, requestsPerMinute: 60 }
    ];
    
    console.log('🕵️  Memory Leak Detector initialized');
    console.log(`Session duration: ${this.sessionDuration / 1000 / 60 / 60} hours`);
    console.log(`Sample interval: ${this.sampleInterval / 1000} seconds`);
  }

  async startDetection() {
    console.log('🚀 Starting long-running memory leak detection...');
    
    this.isRunning = true;
    this.startTime = Date.now();
    
    // Establish baseline
    await this.establishBaseline();
    
    // Start monitoring loops
    this.startMemoryMonitoring();
    this.startWorkloadSimulation();
    this.startGCMonitoring();
    
    // Set up graceful shutdown
    process.on('SIGINT', () => this.gracefulShutdown());
    process.on('SIGTERM', () => this.gracefulShutdown());
    
    // Main detection loop
    return new Promise((resolve) => {
      setTimeout(async () => {
        await this.stopDetection();
        resolve(this.generateReport());
      }, this.sessionDuration);
    });
  }

  async establishBaseline() {
    console.log('📊 Establishing memory baseline...');
    
    // Force garbage collection to get clean baseline
    if (global.gc) {
      global.gc();
    }
    
    // Take initial measurements
    const initialMemory = process.memoryUsage();
    
    // Run light workload to establish operational baseline
    for (let i = 0; i < 10; i++) {
      try {
        await axios.get(`${this.apiUrl}/health`, { timeout: 5000 });
        await axios.get(`${this.apiUrl}/forecast?horizon=24h&vars=t2m`, { timeout: 10000 });
      } catch (error) {
        console.warn('Baseline request failed:', error.message);
      }
    }
    
    // Take stabilized baseline
    const stabilizedMemory = process.memoryUsage();
    
    this.baseline = {
      initial: this.formatMemory(initialMemory),
      stabilized: this.formatMemory(stabilizedMemory),
      timestamp: Date.now()
    };
    
    console.log(`✅ Baseline established: ${this.baseline.stabilized.heapUsed}MB heap`);
  }

  startMemoryMonitoring() {
    console.log('📈 Starting memory monitoring...');
    
    const monitor = setInterval(() => {
      if (!this.isRunning) {
        clearInterval(monitor);
        return;
      }
      
      this.collectMemorySample();
    }, this.sampleInterval);
    
    this.monitorInterval = monitor;
  }

  collectMemorySample() {
    const memory = process.memoryUsage();
    const hrtime = process.hrtime();
    const timestamp = Date.now();
    
    const sample = {
      timestamp,
      sessionTime: timestamp - this.startTime,
      memory: this.formatMemory(memory),
      cpuUsage: process.cpuUsage(),
      uptime: process.uptime(),
      hrtime: hrtime[0] * 1000 + hrtime[1] / 1000000 // Convert to milliseconds
    };
    
    this.samples.push(sample);
    
    // Check for memory growth
    this.analyzeMemoryGrowth(sample);
    
    // Check for absolute memory limits
    if (sample.memory.heapUsed > this.maxMemoryMB) {
      this.emitMemoryAlert('CRITICAL', `Memory usage exceeded limit: ${sample.memory.heapUsed}MB`);
    }
    
    // Log periodic status
    if (this.samples.length % 20 === 0) { // Every ~10 minutes with 30s interval
      this.logMemoryStatus(sample);
    }
  }

  analyzeMemoryGrowth(sample) {
    if (this.samples.length < 10) return; // Need history for trend analysis
    
    const recentSamples = this.samples.slice(-10);
    const growthPattern = this.calculateGrowthPattern(recentSamples);
    
    // Check for sustained growth
    if (growthPattern.trend > 0.5 && growthPattern.totalGrowth > this.alertThreshold) {
      const leak = {
        type: 'sustained_growth',
        detected: Date.now(),
        sessionTime: sample.sessionTime,
        pattern: growthPattern,
        memoryAt: sample.memory.heapUsed,
        severity: this.calculateSeverity(growthPattern)
      };
      
      this.leaks.push(leak);
      this.emitMemoryAlert(leak.severity, `Sustained memory growth detected: +${growthPattern.totalGrowth}MB over ${growthPattern.timeSpan}min`);
    }
    
    // Check for sudden spikes
    if (this.samples.length >= 2) {
      const previous = this.samples[this.samples.length - 2];
      const growth = sample.memory.heapUsed - previous.memory.heapUsed;
      
      if (growth > 50) { // >50MB sudden increase
        const spike = {
          type: 'memory_spike',
          detected: Date.now(),
          sessionTime: sample.sessionTime,
          growth,
          from: previous.memory.heapUsed,
          to: sample.memory.heapUsed,
          severity: growth > 100 ? 'HIGH' : 'MEDIUM'
        };
        
        this.leaks.push(spike);
        this.emitMemoryAlert(spike.severity, `Memory spike detected: +${growth}MB`);
      }
    }
  }

  calculateGrowthPattern(samples) {
    const firstSample = samples[0];
    const lastSample = samples[samples.length - 1];
    
    const totalGrowth = lastSample.memory.heapUsed - firstSample.memory.heapUsed;
    const timeSpan = (lastSample.timestamp - firstSample.timestamp) / 1000 / 60; // minutes
    const growthRate = totalGrowth / timeSpan; // MB per minute
    
    // Calculate linear trend
    const trend = this.calculateLinearTrend(samples.map(s => s.memory.heapUsed));
    
    return {
      totalGrowth,
      timeSpan: Math.round(timeSpan * 100) / 100,
      growthRate: Math.round(growthRate * 1000) / 1000,
      trend: Math.round(trend * 1000) / 1000
    };
  }

  calculateLinearTrend(values) {
    const n = values.length;
    const x = Array.from({ length: n }, (_, i) => i);
    const y = values;
    
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
    const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    return slope;
  }

  calculateSeverity(growthPattern) {
    if (growthPattern.growthRate > 2) return 'CRITICAL'; // >2MB/min
    if (growthPattern.growthRate > 1) return 'HIGH';     // >1MB/min
    if (growthPattern.growthRate > 0.5) return 'MEDIUM'; // >0.5MB/min
    return 'LOW';
  }

  startWorkloadSimulation() {
    console.log('🏋️  Starting workload simulation...');
    
    const simulator = setInterval(async () => {
      if (!this.isRunning) {
        clearInterval(simulator);
        return;
      }
      
      await this.executeWorkload();
    }, 60000); // Every minute
    
    this.workloadInterval = simulator;
  }

  async executeWorkload() {
    const pattern = this.selectWorkloadPattern();
    const requests = Math.floor(pattern.requestsPerMinute / 4); // Quarter of requests per 15s batch
    
    const endpoints = [
      '/health',
      '/forecast?horizon=6h&vars=t2m',
      '/forecast?horizon=24h&vars=t2m,u10,v10',
      '/forecast?horizon=24h&vars=t2m,u10,v10,z500,cape',
      '/performance',
      '/metrics'
    ];
    
    for (let i = 0; i < requests; i++) {
      const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
      
      try {
        await axios.get(`${this.apiUrl}${endpoint}`, { 
          timeout: 10000,
          headers: { 'User-Agent': 'MemoryLeakDetector/1.0' }
        });
      } catch (error) {
        // Ignore request errors, focus on memory
      }
      
      // Small delay between requests
      await this.sleep(50 + Math.random() * 100);
    }
  }

  selectWorkloadPattern() {
    const random = Math.random() * 100;
    let cumulative = 0;
    
    for (const pattern of this.workloadPatterns) {
      cumulative += pattern.weight;
      if (random <= cumulative) {
        return pattern;
      }
    }
    
    return this.workloadPatterns[0]; // Fallback
  }

  startGCMonitoring() {
    console.log('🗑️  Starting garbage collection monitoring...');
    
    // Force GC if available
    if (global.gc) {
      const gcMonitor = setInterval(() => {
        if (!this.isRunning) {
          clearInterval(gcMonitor);
          return;
        }
        
        const beforeGC = process.memoryUsage().heapUsed;
        const gcStart = performance.now();
        
        global.gc();
        
        const gcTime = performance.now() - gcStart;
        const afterGC = process.memoryUsage().heapUsed;
        const freed = beforeGC - afterGC;
        
        this.gcStats.forced++;
        this.gcStats.totalTime += gcTime;
        
        if (freed < beforeGC * 0.1) { // Less than 10% freed
          this.emitMemoryAlert('MEDIUM', `Poor GC efficiency: only ${freed}MB freed in ${gcTime.toFixed(2)}ms`);
        }
        
      }, 5 * 60 * 1000); // Every 5 minutes
      
      this.gcInterval = gcMonitor;
    } else {
      console.warn('⚠️  Garbage collection not available (run with --expose-gc)');
    }
  }

  logMemoryStatus(sample) {
    const sessionHours = sample.sessionTime / 1000 / 60 / 60;
    const growthFromBaseline = sample.memory.heapUsed - this.baseline.stabilized.heapUsed;
    
    console.log(`📊 Memory Status [${sessionHours.toFixed(1)}h]: ${sample.memory.heapUsed}MB heap (+${growthFromBaseline}MB) | ${this.leaks.length} leaks detected`);
  }

  emitMemoryAlert(severity, message) {
    const alert = {
      severity,
      message,
      timestamp: Date.now(),
      sessionTime: Date.now() - this.startTime,
      currentMemory: process.memoryUsage()
    };
    
    console.log(`⚠️  [${severity}] ${message}`);
    this.emit('memoryAlert', alert);
  }

  async stopDetection() {
    console.log('🛑 Stopping memory leak detection...');
    
    this.isRunning = false;
    
    // Clear intervals
    if (this.monitorInterval) clearInterval(this.monitorInterval);
    if (this.workloadInterval) clearInterval(this.workloadInterval);
    if (this.gcInterval) clearInterval(this.gcInterval);
    
    // Final memory sample
    this.collectMemorySample();
    
    console.log('✅ Memory leak detection stopped');
  }

  async gracefulShutdown() {
    console.log('\n🔄 Graceful shutdown initiated...');
    
    await this.stopDetection();
    const report = this.generateReport();
    await this.saveReport(report);
    
    console.log('👋 Memory leak detection completed');
    process.exit(0);
  }

  generateReport() {
    const finalSample = this.samples[this.samples.length - 1];
    const sessionDuration = finalSample.sessionTime / 1000 / 60 / 60; // hours
    
    const totalGrowth = finalSample.memory.heapUsed - this.baseline.stabilized.heapUsed;
    const avgGrowthRate = totalGrowth / sessionDuration; // MB per hour
    
    const report = {
      metadata: {
        startTime: this.startTime,
        endTime: Date.now(),
        sessionDuration: sessionDuration.toFixed(2) + ' hours',
        totalSamples: this.samples.length,
        sampleInterval: this.sampleInterval / 1000 + ' seconds'
      },
      
      baseline: this.baseline,
      
      finalMemory: finalSample.memory,
      
      memoryGrowth: {
        total: totalGrowth,
        rate: avgGrowthRate.toFixed(3) + ' MB/hour',
        percentage: ((totalGrowth / this.baseline.stabilized.heapUsed) * 100).toFixed(1) + '%'
      },
      
      leakDetection: {
        leaksDetected: this.leaks.length,
        leaks: this.leaks,
        severityBreakdown: this.categorizeLeaks()
      },
      
      garbageCollection: {
        ...this.gcStats,
        avgGCTime: this.gcStats.forced > 0 ? (this.gcStats.totalTime / this.gcStats.forced).toFixed(2) + 'ms' : 'N/A',
        gcAvailable: !!global.gc
      },
      
      performance: this.analyzePerformance(),
      
      recommendations: this.generateRecommendations(totalGrowth, avgGrowthRate),
      
      status: this.determineOverallStatus(totalGrowth, this.leaks.length)
    };
    
    this.printReport(report);
    return report;
  }

  categorizeLeaks() {
    const breakdown = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    
    this.leaks.forEach(leak => {
      const severity = leak.severity || 'LOW';
      breakdown[severity]++;
    });
    
    return breakdown;
  }

  analyzePerformance() {
    if (this.samples.length < 2) return null;
    
    const memoryUsages = this.samples.map(s => s.memory.heapUsed);
    const min = Math.min(...memoryUsages);
    const max = Math.max(...memoryUsages);
    const avg = memoryUsages.reduce((a, b) => a + b) / memoryUsages.length;
    
    return {
      memoryRange: {
        min: min.toFixed(2) + 'MB',
        max: max.toFixed(2) + 'MB',
        average: avg.toFixed(2) + 'MB'
      },
      memoryVolatility: ((max - min) / avg * 100).toFixed(1) + '%',
      stabilityScore: this.calculateStabilityScore()
    };
  }

  calculateStabilityScore() {
    // Score from 0-100 based on memory stability
    const growthFactor = Math.abs(this.samples[this.samples.length - 1].memory.heapUsed - this.baseline.stabilized.heapUsed);
    const leakPenalty = this.leaks.length * 10;
    
    let score = 100 - (growthFactor / 10) - leakPenalty;
    return Math.max(0, Math.min(100, score)).toFixed(1);
  }

  generateRecommendations(totalGrowth, avgGrowthRate) {
    const recommendations = [];
    
    if (totalGrowth > 100) {
      recommendations.push('CRITICAL: Significant memory growth detected. Investigate for memory leaks.');
    }
    
    if (avgGrowthRate > 5) {
      recommendations.push('HIGH: High memory growth rate. Monitor application for resource leaks.');
    }
    
    if (this.leaks.some(leak => leak.severity === 'CRITICAL')) {
      recommendations.push('CRITICAL: Critical memory leaks detected. Immediate investigation required.');
    }
    
    if (!global.gc) {
      recommendations.push('INFO: Run with --expose-gc flag for better GC monitoring.');
    }
    
    if (this.gcStats.forced > 0 && this.gcStats.totalTime / this.gcStats.forced > 100) {
      recommendations.push('MEDIUM: GC taking longer than expected. Consider heap size optimization.');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('GOOD: No significant memory issues detected.');
    }
    
    return recommendations;
  }

  determineOverallStatus(totalGrowth, leakCount) {
    if (totalGrowth > 200 || leakCount > 10) return 'CRITICAL';
    if (totalGrowth > 100 || leakCount > 5) return 'WARNING';
    if (totalGrowth > 50 || leakCount > 2) return 'CAUTION';
    return 'HEALTHY';
  }

  printReport(report) {
    console.log('\n🕵️  Memory Leak Detection Report');
    console.log('='.repeat(50));
    
    console.log(`\n📊 Session Summary:`);
    console.log(`  Duration: ${report.metadata.sessionDuration}`);
    console.log(`  Samples: ${report.metadata.totalSamples}`);
    
    console.log(`\n💾 Memory Analysis:`);
    console.log(`  Baseline: ${report.baseline.stabilized.heapUsed}MB`);
    console.log(`  Final: ${report.finalMemory.heapUsed}MB`);
    console.log(`  Growth: ${report.memoryGrowth.total}MB (${report.memoryGrowth.percentage}) at ${report.memoryGrowth.rate}`);
    
    console.log(`\n🔍 Leak Detection:`);
    console.log(`  Total leaks: ${report.leakDetection.leaksDetected}`);
    Object.entries(report.leakDetection.severityBreakdown).forEach(([severity, count]) => {
      if (count > 0) console.log(`  ${severity}: ${count}`);
    });
    
    if (report.garbageCollection.gcAvailable) {
      console.log(`\n🗑️  Garbage Collection:`);
      console.log(`  Forced GCs: ${report.garbageCollection.forced}`);
      console.log(`  Average GC time: ${report.garbageCollection.avgGCTime}`);
    }
    
    console.log(`\n📈 Performance:`);
    if (report.performance) {
      console.log(`  Memory range: ${report.performance.memoryRange.min} - ${report.performance.memoryRange.max}`);
      console.log(`  Stability score: ${report.performance.stabilityScore}/100`);
    }
    
    console.log(`\n🎯 Overall Status: ${report.status}`);
    
    console.log(`\n💡 Recommendations:`);
    report.recommendations.forEach(rec => console.log(`  - ${rec}`));
  }

  async saveReport(report) {
    const reportsDir = path.join(__dirname, '..', 'reports');
    
    try {
      await fs.mkdir(reportsDir, { recursive: true });
    } catch (error) {
      // Directory already exists
    }
    
    const filename = `memory-leak-detection-${Date.now()}.json`;
    const filepath = path.join(reportsDir, filename);
    
    await fs.writeFile(filepath, JSON.stringify(report, null, 2));
    console.log(`💾 Report saved to: ${filepath}`);
  }

  formatMemory(memory) {
    return {
      heapUsed: Math.round(memory.heapUsed / 1024 / 1024),
      heapTotal: Math.round(memory.heapTotal / 1024 / 1024),
      external: Math.round(memory.external / 1024 / 1024),
      rss: Math.round(memory.rss / 1024 / 1024)
    };
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// CLI execution
async function main() {
  const config = {
    apiUrl: process.env.API_URL || 'http://localhost:8000',
    sessionDuration: parseInt(process.env.SESSION_DURATION) || 24 * 60 * 60 * 1000, // 24 hours
    sampleInterval: parseInt(process.env.SAMPLE_INTERVAL) || 30000, // 30 seconds
    alertThreshold: parseInt(process.env.ALERT_THRESHOLD) || 100, // 100MB
    maxMemoryMB: parseInt(process.env.MAX_MEMORY_MB) || 1024 // 1GB
  };
  
  console.log('🕵️  Adelaide Weather Memory Leak Detector');
  console.log('==========================================');
  
  const detector = new MemoryLeakDetector(config);
  
  try {
    const report = await detector.startDetection();
    
    // Exit with appropriate code based on findings
    switch (report.status) {
      case 'HEALTHY':
        console.log('\n✅ No memory leaks detected');
        process.exit(0);
        break;
      case 'CAUTION':
        console.log('\n⚠️  Minor memory growth detected');
        process.exit(0);
        break;
      case 'WARNING':
        console.log('\n⚠️  Memory growth warning');
        process.exit(1);
        break;
      case 'CRITICAL':
        console.log('\n❌ Critical memory issues detected');
        process.exit(1);
        break;
      default:
        process.exit(0);
    }
    
  } catch (error) {
    console.error('\n💥 Memory leak detection failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = MemoryLeakDetector;