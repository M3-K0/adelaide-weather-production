#!/usr/bin/env python3
"""
Adelaide Weather Forecasting - Health Check Integration Example
==============================================================

Example showing how to integrate the enhanced health checks into the main API.
This demonstrates adding new health endpoints without breaking existing functionality.

Usage:
1. Import the enhanced_health_endpoints router
2. Include it in your FastAPI app
3. Initialize the health checker during startup

Author: Integration Example
Version: 1.0.0 - Health Check Integration
"""

from fastapi import FastAPI
from api.enhanced_health_endpoints import health_router, initialize_health_checker

# Example of how to integrate enhanced health checks into main.py
def add_enhanced_health_checks(app: FastAPI, forecast_adapter):
    """
    Add enhanced health check endpoints to the FastAPI application.
    
    Args:
        app: FastAPI application instance
        forecast_adapter: Initialized ForecastAdapter instance
    """
    
    # Initialize the health checker with the forecast adapter
    initialize_health_checker(forecast_adapter)
    
    # Include the health router
    app.include_router(health_router)
    
    # The following endpoints will now be available:
    # - GET /health/live     - Kubernetes liveness probe
    # - GET /health/ready    - Kubernetes readiness probe  
    # - GET /health/detailed - Comprehensive health report
    # - GET /health/dependencies - Dependency status
    # - GET /health/performance - Performance metrics
    # - GET /health/status   - Simple status check

# Example integration in startup event
async def enhanced_startup_event(app: FastAPI, forecast_adapter):
    """
    Enhanced startup event that includes health check initialization.
    
    This would replace or extend the existing startup_event in main.py
    """
    
    # ... existing startup code ...
    
    # Add enhanced health checks
    add_enhanced_health_checks(app, forecast_adapter)
    
    # ... rest of startup code ...

# Example showing how to modify the existing main.py startup event:
"""
In main.py, modify the startup_event function:

@app.on_event("startup")
async def startup_event():
    global forecast_adapter, system_health
    
    # ... existing initialization code ...
    
    # After forecast_adapter is initialized:
    if forecast_adapter:
        # Initialize enhanced health checks
        from api.enhanced_health_endpoints import initialize_health_checker
        initialize_health_checker(forecast_adapter)
        
        # Include enhanced health endpoints
        from api.enhanced_health_endpoints import health_router
        app.include_router(health_router)
    
    # ... rest of existing code ...
"""

# For Kubernetes deployment, you would update your deployment.yaml:
"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adelaide-weather-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: adelaide-weather-api:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
"""