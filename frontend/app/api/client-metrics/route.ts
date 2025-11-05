import { NextRequest, NextResponse } from 'next/server';

/**
 * Client-side metrics collection endpoint
 * Accepts metrics data from the frontend for server-side processing
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // In a production system, this would send metrics to a monitoring system
    // For now, we'll just log them and return success
    console.log('Client metrics received:', {
      timestamp: new Date().toISOString(),
      metrics: body
    });

    return NextResponse.json({ 
      success: true, 
      message: 'Metrics received' 
    });
  } catch (error) {
    console.error('Error processing client metrics:', error);
    return NextResponse.json(
      { error: 'Failed to process metrics' }, 
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}