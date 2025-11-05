#!/usr/bin/env python3
"""
Adelaide Weather Forecasting - Enhanced Health Endpoints
========================================================

Additional health check endpoints for comprehensive monitoring, SLO tracking,
and Kubernetes deployment support. These endpoints complement the existing
health endpoint with more detailed monitoring capabilities.

Features:
- /health/live: Kubernetes liveness probe
- /health/ready: Kubernetes readiness probe  
- /health/detailed: Comprehensive health report
- /health/dependencies: Dependency status
- /health/performance: Performance metrics

Author: Production Engineering  
Version: 1.0.0 - Enhanced Health Monitoring
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.health_checks import EnhancedHealthChecker

# Create router for health endpoints
health_router = APIRouter(prefix="/health", tags=["health"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global health checker instance
health_checker: Optional[EnhancedHealthChecker] = None

def get_health_checker() -> EnhancedHealthChecker:
    """Get the global health checker instance."""
    global health_checker
    if health_checker is None:
        raise HTTPException(503, "Health checker not initialized")
    return health_checker

def initialize_health_checker(forecast_adapter=None):
    """Initialize the global health checker."""
    global health_checker
    health_checker = EnhancedHealthChecker(forecast_adapter)

@health_router.get("/live")
@limiter.limit("60/minute")
async def liveness_probe(request: Request):
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the application process is alive and responsive.
    Should only return 503/500 if the application needs to be restarted.
    
    This endpoint is called frequently by Kubernetes and should be fast.
    """
    try:
        checker = get_health_checker()
        result = await checker.perform_liveness_check()
        
        if result["status"] == "pass":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "alive",
                    "timestamp": result["timestamp"],
                    "uptime_seconds": result.get("details", {}).get("uptime_seconds", 0)
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "failing",
                    "message": result["message"],
                    "timestamp": result["timestamp"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Liveness check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@health_router.get("/ready")
@limiter.limit("60/minute") 
async def readiness_probe(request: Request):
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the application is ready to serve traffic.
    Returns 503 if the application is alive but not ready to serve requests.
    
    This controls whether the pod receives traffic from the service.
    """
    try:
        checker = get_health_checker()
        result = await checker.perform_readiness_check()
        
        if result["status"] == "pass":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ready",
                    "timestamp": result["timestamp"],
                    "checks_passed": len([c for c in result.get("checks", []) if c["status"] == "pass"])
                }
            )
        else:
            failed_checks = [c["name"] for c in result.get("checks", []) if c["status"] == "fail"]
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "message": result["message"],
                    "failed_checks": failed_checks,
                    "timestamp": result["timestamp"]
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Readiness check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@health_router.get("/detailed")
@limiter.limit("20/minute")
async def detailed_health_check(request: Request):
    """
    Comprehensive health check with full system analysis.
    
    Provides detailed information about all system components,
    dependencies, performance metrics, and historical data.
    
    Use this endpoint for monitoring dashboards and operational visibility.
    """
    try:
        checker = get_health_checker()
        result = await checker.perform_comprehensive_health_check()
        
        # Always return 200 for detailed checks, status is in the response
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Detailed health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@health_router.get("/dependencies")
@limiter.limit("30/minute")
async def dependency_status(request: Request):
    """
    Get status of all external dependencies.
    
    Provides detailed information about:
    - Redis cache connectivity
    - File system access
    - External API connectivity
    - Database connections (if applicable)
    """
    try:
        checker = get_health_checker()
        
        # Run dependency checks
        dependency_checks = await checker._check_all_dependencies()
        
        dependencies = []
        overall_status = "healthy"
        
        for check in dependency_checks:
            dep_status = {
                "name": check.name,
                "status": check.status,
                "message": check.message,
                "response_time_ms": check.duration_ms,
                "details": check.details,
                "last_checked": check.timestamp.isoformat()
            }
            dependencies.append(dep_status)
            
            # Update overall status
            if check.status == "fail":
                overall_status = "degraded"
            elif check.status == "warn" and overall_status == "healthy":
                overall_status = "partial"
        
        return JSONResponse(
            status_code=200,
            content={
                "overall_status": overall_status,
                "dependencies": dependencies,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "overall_status": "error",
                "message": f"Dependency check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@health_router.get("/performance")
@limiter.limit("30/minute")
async def performance_metrics(request: Request):
    """
    Get current performance metrics and baselines.
    
    Provides:
    - Response time percentiles
    - System resource usage
    - Performance trends
    - SLO compliance status
    """
    try:
        checker = get_health_checker()
        
        # Get system metrics
        system_metrics = await checker._get_system_metrics()
        performance_baseline = await checker._get_performance_baseline()
        
        return JSONResponse(
            status_code=200,
            content={
                "system_metrics": {
                    "cpu_usage_percent": system_metrics.cpu_usage_percent,
                    "memory_usage_percent": system_metrics.memory_usage_percent,
                    "memory_available_mb": system_metrics.memory_available_mb,
                    "disk_usage_percent": system_metrics.disk_usage_percent,
                    "disk_available_gb": system_metrics.disk_available_gb,
                    "open_file_descriptors": system_metrics.open_file_descriptors,
                    "network_connections": system_metrics.network_connections
                },
                "performance_baseline": performance_baseline,
                "performance_history_samples": len(checker.performance_history),
                "measured_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Performance metrics failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@health_router.get("/status") 
@limiter.limit("60/minute")
async def simple_status_check(request: Request):
    """
    Simple status check for load balancers and basic monitoring.
    
    Returns a minimal response indicating if the service is up.
    This is the fastest health check endpoint.
    """
    try:
        # Just check if we can get the health checker
        get_health_checker()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "UP",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "DOWN",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )