/**
 * Lighthouse CI Configuration for Adelaide Weather Forecasting System
 * Comprehensive Web Performance Audit with Core Web Vitals Monitoring
 * 
 * Performance Targets:
 * - First Contentful Paint (FCP) < 1.5s
 * - Largest Contentful Paint (LCP) < 2.5s  
 * - First Input Delay (FID) < 100ms
 * - Cumulative Layout Shift (CLS) < 0.1
 * - Time to Interactive (TTI) < 3.5s
 */

module.exports = {
  ci: {
    collect: {
      numberOfRuns: 5,
      url: [
        'http://localhost:3000/',
        'http://localhost:3000/metrics-demo',
        'http://localhost:3000/analog-demo',
        'http://localhost:3000/cape-demo'
      ],
      settings: {
        chromeFlags: '--no-sandbox --disable-dev-shm-usage --disable-gpu',
        preset: 'desktop',
        throttling: {
          rttMs: 40,
          throughputKbps: 10240,
          cpuSlowdownMultiplier: 1,
          requestLatencyMs: 0,
          downloadThroughputKbps: 0,
          uploadThroughputKbps: 0
        },
        screenEmulation: {
          mobile: false,
          width: 1350,
          height: 940,
          deviceScaleFactor: 1,
          disabled: false
        },
        formFactor: 'desktop',
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
        skipAudits: []
      }
    },
    assert: {
      preset: 'lighthouse:recommended',
      assertions: {
        // Core Web Vitals - Critical Performance Metrics
        'first-contentful-paint': ['error', { maxNumericValue: 1500 }], // < 1.5s
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }], // < 2.5s
        'first-meaningful-paint': ['warn', { maxNumericValue: 2000 }], // < 2s
        'speed-index': ['warn', { maxNumericValue: 3000 }], // < 3s
        'interactive': ['error', { maxNumericValue: 3500 }], // < 3.5s TTI
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }], // < 0.1 CLS
        
        // Performance Budget Enforcement
        'total-byte-weight': ['warn', { maxNumericValue: 1600000 }], // < 1.6MB
        'dom-size': ['warn', { maxNumericValue: 1500 }], // < 1500 DOM nodes
        'bootup-time': ['warn', { maxNumericValue: 2500 }], // < 2.5s JS execution time
        'mainthread-work-breakdown': ['warn', { maxNumericValue: 4000 }], // < 4s main thread
        
        // Resource Optimization
        'unused-javascript': ['warn', { maxNumericValue: 40000 }], // < 40KB unused JS
        'unused-css-rules': ['warn', { maxNumericValue: 20000 }], // < 20KB unused CSS
        'unminified-javascript': 'error',
        'unminified-css': 'error',
        'uses-text-compression': 'error',
        'uses-responsive-images': 'warn',
        'modern-image-formats': 'warn',
        'efficient-animated-content': 'warn',
        
        // Caching & Network Optimization
        'uses-long-cache-ttl': 'warn',
        'uses-rel-preconnect': 'warn',
        'uses-rel-preload': 'warn',
        'render-blocking-resources': 'warn',
        'redirects': 'error',
        
        // Accessibility Requirements
        'color-contrast': 'error',
        'heading-order': 'error',
        'alt-text': 'error',
        'aria-labels': 'error',
        'keyboard-navigation': 'error',
        
        // Best Practices
        'uses-https': 'error',
        'no-vulnerable-libraries': 'error',
        'csp-xss': 'warn',
        
        // SEO Basics
        'meta-description': 'warn',
        'document-title': 'error',
        'robots-txt': 'warn'
      }
    },
    upload: {
      target: 'temporary-public-storage',
      githubAppToken: process.env.LHCI_GITHUB_APP_TOKEN,
      githubToken: process.env.GITHUB_TOKEN
    },
    server: {
      port: 9001,
      storage: {
        storageMethod: 'sql',
        sqlDialect: 'sqlite',
        sqlDatabasePath: './tests/performance/reports/lighthouse-results.db'
      }
    },
    wizard: {
      preset: 'desktop'
    }
  },
  
  // Custom performance budgets for different page types
  budgets: [
    {
      path: '/',
      resourceSizes: [
        { resourceType: 'document', budget: 50 },
        { resourceType: 'stylesheet', budget: 100 },
        { resourceType: 'script', budget: 400 },
        { resourceType: 'image', budget: 200 },
        { resourceType: 'font', budget: 100 },
        { resourceType: 'other', budget: 50 },
        { resourceType: 'total', budget: 900 }
      ],
      resourceCounts: [
        { resourceType: 'document', budget: 1 },
        { resourceType: 'stylesheet', budget: 6 },
        { resourceType: 'script', budget: 15 },
        { resourceType: 'image', budget: 20 },
        { resourceType: 'font', budget: 4 },
        { resourceType: 'other', budget: 10 },
        { resourceType: 'total', budget: 56 }
      ],
      timings: [
        { metric: 'first-contentful-paint', budget: 1500 },
        { metric: 'largest-contentful-paint', budget: 2500 },
        { metric: 'interactive', budget: 3500 },
        { metric: 'cumulative-layout-shift', budget: 0.1 }
      ]
    },
    {
      path: '/metrics-demo',
      resourceSizes: [
        { resourceType: 'total', budget: 1200 } // Metrics page allows more for charts
      ],
      timings: [
        { metric: 'interactive', budget: 4000 }, // Chart rendering may take longer
        { metric: 'largest-contentful-paint', budget: 3000 }
      ]
    }
  ],
  
  // Mobile performance configuration
  mobile: {
    collect: {
      settings: {
        preset: 'mobile',
        throttling: {
          rttMs: 150,
          throughputKbps: 1600,
          cpuSlowdownMultiplier: 4
        },
        screenEmulation: {
          mobile: true,
          width: 375,
          height: 667,
          deviceScaleFactor: 2
        }
      }
    },
    assert: {
      assertions: {
        // Stricter mobile performance targets
        'first-contentful-paint': ['error', { maxNumericValue: 2000 }], // < 2s on mobile
        'largest-contentful-paint': ['error', { maxNumericValue: 3000 }], // < 3s on mobile
        'interactive': ['error', { maxNumericValue: 5000 }], // < 5s on mobile
        'speed-index': ['warn', { maxNumericValue: 4000 }], // < 4s on mobile
        'total-byte-weight': ['error', { maxNumericValue: 1000000 }] // < 1MB on mobile
      }
    }
  }
};