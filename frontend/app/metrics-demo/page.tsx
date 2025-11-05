/**
 * Metrics Dashboard Demo Page
 * 
 * Demonstrates the comprehensive metrics dashboard with live data
 * showing forecast accuracy, performance indicators, and system health.
 */

'use client';

import React from 'react';
import { MetricsDashboard } from '@/components';
import '@/styles/metrics-dashboard.css';

export default function MetricsDemoPage() {
  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Weather Forecast Metrics Dashboard
          </h1>
          <p className="text-gray-400 text-lg">
            Comprehensive monitoring of forecast accuracy, system performance, and health indicators
          </p>
        </div>

        {/* Dashboard */}
        <MetricsDashboard 
          className="metrics-dashboard"
          autoRefresh={true}
          refreshInterval={30}
        />

        {/* Features Overview */}
        <div className="mt-12 bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">Dashboard Features</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-blue-400">Forecast Accuracy</h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Accuracy percentages by horizon (6h, 12h, 24h, 48h)</li>
                <li>• Mean Absolute Error (MAE) trends</li>
                <li>• Bias indicators for all weather variables</li>
                <li>• Visual accuracy trend charts</li>
                <li>• Real-time accuracy monitoring</li>
              </ul>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-emerald-400">Performance Insights</h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• API response time monitoring</li>
                <li>• Model inference performance</li>
                <li>• Data freshness indicators</li>
                <li>• Cache hit rate metrics</li>
                <li>• Request rate and error tracking</li>
              </ul>
            </div>
            
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-amber-400">Interactive Features</h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Time range selection (1h to 30d)</li>
                <li>• Variable filtering and customization</li>
                <li>• Real-time updates every 30 seconds</li>
                <li>• Export capabilities (JSON, CSV)</li>
                <li>• Responsive design for all devices</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Technical Information */}
        <div className="mt-8 bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">Technical Implementation</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-purple-400 mb-2">Metrics Collection</h3>
              <p className="text-gray-300 text-sm mb-3">
                The dashboard integrates with Prometheus metrics collection system to provide real-time 
                monitoring of forecast accuracy, system performance, and component health.
              </p>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Prometheus metrics integration</li>
                <li>• Real-time data aggregation</li>
                <li>• Historical trend analysis</li>
                <li>• Automated alerting thresholds</li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-cyan-400 mb-2">User Experience</h3>
              <p className="text-gray-300 text-sm mb-3">
                Built with React and TypeScript for type safety, the dashboard provides 
                an intuitive interface with accessibility features and responsive design.
              </p>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Accessible keyboard navigation</li>
                <li>• High contrast mode support</li>
                <li>• Mobile-optimized layouts</li>
                <li>• Tooltips explaining technical terms</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Integration Notes */}
        <div className="mt-8 bg-blue-950/20 border border-blue-700 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-blue-400 mb-2">Integration with T-007</h2>
          <p className="text-blue-300 text-sm">
            This dashboard leverages the enhanced Prometheus metrics configuration from T-007, 
            providing comprehensive observability for the Adelaide Weather Forecasting System. 
            It displays real metrics collected from the monitoring infrastructure including 
            forecast accuracy tracking, performance monitoring, and system health indicators.
          </p>
        </div>
      </div>
    </div>
  );
}