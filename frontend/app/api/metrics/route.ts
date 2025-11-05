import { NextRequest, NextResponse } from 'next/server';
import { getMetrics } from '@/lib/metrics';

/**
 * Prometheus Metrics Endpoint for Frontend
 *
 * Exposes UI interaction metrics, forecast quality metrics, and ensemble spread metrics
 * in Prometheus format for scraping by monitoring systems.
 */

export async function GET(request: NextRequest) {
  try {
    // Get all metrics in Prometheus format
    const metrics = await getMetrics();

    // Return metrics with proper content type
    return new NextResponse(metrics, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; version=0.0.4; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
        Expires: '0'
      }
    });
  } catch (error) {
    console.error('Error generating metrics:', error);

    return NextResponse.json(
      { error: 'Failed to generate metrics' },
      { status: 500 }
    );
  }
}

// Handle preflight requests for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}
