#!/usr/bin/env python3
"""
Minimal FastAPI server for load testing
==========================================

Simple mock weather API for load testing purposes.
Simulates real API endpoints with realistic response times and data.
"""

import time
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import random
import asyncio

# Security
security = HTTPBearer(auto_error=False)

# App initialization
app = FastAPI(
    title="Adelaide Weather Load Test API",
    version="1.0.0",
    description="Mock weather API for comprehensive load testing"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request counter for metrics
request_count = 0
error_count = 0
response_times = []

# Valid configurations
VALID_HORIZONS = ['6h', '12h', '24h', '48h']
VALID_VARIABLES = ['t2m', 'u10', 'v10', 'msl', 'z500', 't850', 'q850', 'u850', 'v850', 'cape']

class HealthResponse(BaseModel):
    status: str
    ready: bool
    timestamp: str
    version: str
    services: Dict[str, str]
    metrics: Optional[Dict[str, Any]] = None

class ForecastResponse(BaseModel):
    forecast: Dict[str, Any]
    metadata: Dict[str, Any]
    performance: Dict[str, float]

# Authentication mock
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    if not credentials:
        return False
    # Accept any token for load testing - very permissive
    token = credentials.credentials
    return len(token) > 3  # Any token longer than 3 chars

def require_auth(authenticated: bool = Depends(verify_token)) -> bool:
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    return True

# Simulate analog search with realistic timing
async def simulate_analog_search(horizon: str, variables: List[str]) -> Dict[str, Any]:
    """Simulate FAISS analog search with realistic timing"""
    
    # Simulate search complexity based on horizon and variables
    base_time = 10  # Base 10ms
    horizon_multiplier = {'6h': 1.0, '12h': 1.2, '24h': 1.8, '48h': 2.5}
    variable_overhead = len(variables) * 2
    
    search_time = base_time * horizon_multiplier.get(horizon, 1.0) + variable_overhead
    search_time += random.uniform(-5, 15)  # Add realistic variance
    search_time = max(5, search_time)  # Minimum 5ms
    
    # Simulate actual processing time
    await asyncio.sleep(search_time / 1000)
    
    # Generate mock analog results
    num_analogs = 25
    analogs = []
    
    for i in range(num_analogs):
        analog = {
            'index': i,
            'distance': round(random.uniform(0.01, 0.25), 6),
            'timestamp': '2023-01-01T12:00:00Z',
            'variables': {}
        }
        
        for var in variables:
            if var == 't2m':
                analog['variables'][var] = round(random.uniform(280, 310), 2)
            elif var in ['u10', 'v10']:
                analog['variables'][var] = round(random.uniform(-20, 20), 2)
            elif var == 'msl':
                analog['variables'][var] = round(random.uniform(980, 1030), 2)
            elif var == 'cape':
                analog['variables'][var] = round(random.uniform(0, 4000), 2)
            else:
                analog['variables'][var] = round(random.uniform(-50, 50), 2)
        
        analogs.append(analog)
    
    return {
        'analogs': analogs,
        'search_metadata': {
            'search_time_ms': round(search_time, 2),
            'total_candidates': 50000,
            'k_neighbors': num_analogs,
            'distance_metric': 'euclidean',
            'horizon': horizon,
            'variables_count': len(variables)
        }
    }

# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global request_count
    request_count += 1
    
    # Simulate occasional health check delay
    if random.random() < 0.1:  # 10% chance
        await asyncio.sleep(0.05)  # 50ms delay
    
    avg_response_time = sum(response_times[-100:]) / len(response_times[-100:]) if response_times else 0
    error_rate = error_count / max(1, request_count)
    
    return HealthResponse(
        status="healthy",
        ready=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        services={
            "analog_search": "healthy",
            "forecast_generator": "healthy",
            "database": "healthy"
        },
        metrics={
            "total_requests": request_count,
            "error_count": error_count,
            "error_rate": round(error_rate * 100, 2),
            "avg_response_time_ms": round(avg_response_time, 2)
        }
    )

@app.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    horizon: str,
    vars: str,
    authenticated: bool = Depends(require_auth)
):
    """Weather forecast endpoint with analog search"""
    global request_count, error_count, response_times
    start_time = time.time()
    request_count += 1
    
    # Validate inputs
    if horizon not in VALID_HORIZONS:
        error_count += 1
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid horizon '{horizon}'. Must be one of: {VALID_HORIZONS}"
        )
    
    # Parse variables
    variables = [v.strip() for v in vars.split(',') if v.strip()]
    invalid_vars = [v for v in variables if v not in VALID_VARIABLES]
    
    if invalid_vars:
        error_count += 1
        raise HTTPException(
            status_code=400,
            detail=f"Invalid variables: {invalid_vars}. Valid: {VALID_VARIABLES}"
        )
    
    if len(variables) > 10:
        error_count += 1
        raise HTTPException(
            status_code=400,
            detail="Too many variables requested. Maximum 10 allowed."
        )
    
    # Simulate occasional errors (1% rate)
    if random.random() < 0.01:
        error_count += 1
        await asyncio.sleep(0.1)  # Simulate slow error response
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Simulate variable processing overhead
    processing_delay = len(variables) * 2 + random.uniform(5, 15)
    await asyncio.sleep(processing_delay / 1000)
    
    # Get analog search results
    analog_results = await simulate_analog_search(horizon, variables)
    
    # Generate forecast from analogs
    forecast_data = {}
    confidence_intervals = {}
    
    for var in variables:
        analog_values = [a['variables'][var] for a in analog_results['analogs']]
        
        # Calculate ensemble statistics
        mean_val = sum(analog_values) / len(analog_values)
        std_val = (sum((x - mean_val) ** 2 for x in analog_values) / len(analog_values)) ** 0.5
        
        forecast_data[var] = {
            'value': round(mean_val, 3),
            'confidence_interval': {
                'lower': round(mean_val - 1.96 * std_val, 3),
                'upper': round(mean_val + 1.96 * std_val, 3)
            },
            'ensemble_std': round(std_val, 3),
            'unit': get_variable_unit(var)
        }
        
        confidence_intervals[var] = round(std_val * 1.96, 3)
    
    # Response timing
    response_time = (time.time() - start_time) * 1000
    response_times.append(response_time)
    
    return ForecastResponse(
        forecast=forecast_data,
        metadata={
            'horizon': horizon,
            'variables': variables,
            'analog_search': analog_results['search_metadata'],
            'ensemble_size': len(analog_results['analogs']),
            'forecast_time': datetime.now(timezone.utc).isoformat(),
            'correlation_id': f"load-test-{int(time.time())}-{random.randint(1000, 9999)}"
        },
        performance={
            'total_time_ms': round(response_time, 2),
            'search_time_ms': analog_results['search_metadata']['search_time_ms'],
            'processing_time_ms': round(processing_delay, 2)
        }
    )

@app.get("/metrics")
async def get_metrics(authenticated: bool = Depends(require_auth)):
    """Prometheus-style metrics endpoint"""
    global request_count, error_count, response_times
    
    avg_response_time = sum(response_times[-100:]) / len(response_times[-100:]) if response_times else 0
    error_rate = error_count / max(1, request_count)
    p95_response_time = sorted(response_times[-100:])[-5] if len(response_times) >= 5 else 0
    
    metrics = f"""# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total {request_count}

# HELP api_errors_total Total number of API errors
# TYPE api_errors_total counter
api_errors_total {error_count}

# HELP api_response_time_ms Response time in milliseconds
# TYPE api_response_time_ms histogram
api_response_time_ms_avg {avg_response_time:.2f}
api_response_time_ms_p95 {p95_response_time:.2f}

# HELP api_error_rate API error rate
# TYPE api_error_rate gauge
api_error_rate {error_rate:.4f}
"""
    
    return JSONResponse(
        content=metrics,
        media_type="text/plain"
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Adelaide Weather Load Test API",
        "version": "1.0.0",
        "endpoints": [
            "/health - Health check",
            "/forecast - Weather forecast with analog search",
            "/metrics - Performance metrics",
            "/docs - API documentation"
        ]
    }

def get_variable_unit(variable: str) -> str:
    """Get unit for a weather variable"""
    units = {
        't2m': 'K',
        'u10': 'm/s',
        'v10': 'm/s',
        'msl': 'Pa',
        'z500': 'm²/s²',
        't850': 'K',
        'q850': 'kg/kg',
        'u850': 'm/s',
        'v850': 'm/s',
        'cape': 'J/kg'
    }
    return units.get(variable, '')

if __name__ == "__main__":
    print("🚀 Starting Adelaide Weather Load Test API Server")
    print("📡 Server will be available at: http://localhost:8000")
    print("📊 Metrics endpoint: http://localhost:8000/metrics")
    print("🏥 Health endpoint: http://localhost:8000/health")
    print("📚 API docs: http://localhost:8000/docs")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )