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

@health_router.get("/faiss")
@limiter.limit("30/minute")
async def faiss_health_check(request: Request):
    """
    FAISS-specific health endpoint for detailed FAISS monitoring.
    
    Provides comprehensive FAISS system health including:
    - Index readiness status for all horizons (6h, 12h, 24h, 48h)
    - Last successful search timestamp per horizon
    - Fallback counter metrics and degraded mode status
    - FAISS dimension and ntotal validation
    - Search performance metrics (latency, throughput)
    - Index file integrity and last update timestamps
    - Memory usage and system resource consumption
    """
    try:
        checker = get_health_checker()
        
        # Get comprehensive FAISS health data
        faiss_check_result = await checker._check_faiss_health()
        faiss_metrics = await checker._get_comprehensive_faiss_metrics()
        
        # Get FAISS health monitor if available
        faiss_monitor = None
        faiss_detailed_health = {}
        try:
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            faiss_monitor = await get_faiss_health_monitor()
            faiss_detailed_health = await faiss_monitor.get_health_summary()
        except Exception as monitor_error:
            # Monitor not available, use basic metrics
            pass
        
        # Determine overall FAISS health status
        if faiss_check_result.status == "fail":
            overall_status = "unhealthy"
            status_message = f"FAISS system critical issues: {faiss_check_result.message}"
        elif faiss_check_result.status == "warn":
            overall_status = "degraded"
            status_message = f"FAISS system degraded: {faiss_check_result.message}"
        else:
            overall_status = "healthy"
            status_message = "FAISS system operational"
        
        # Build comprehensive response
        response_data = {
            "faiss_status": overall_status,
            "message": status_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_duration_ms": faiss_check_result.duration_ms,
            
            # Index readiness by horizon
            "index_readiness": {
                "6h": {
                    "flatip_ready": "6h_flatip" in faiss_metrics["indices"],
                    "ivfpq_ready": "6h_ivfpq" in faiss_metrics["indices"],
                    "last_successful_search": faiss_detailed_health.get("latency_percentiles", {}).get("6h", {}).get("last_successful_search"),
                    "last_search_age_seconds": faiss_detailed_health.get("latency_percentiles", {}).get("6h", {}).get("last_search_age_seconds"),
                    "search_samples": faiss_detailed_health.get("latency_percentiles", {}).get("6h", {}).get("sample_count", 0)
                },
                "12h": {
                    "flatip_ready": "12h_flatip" in faiss_metrics["indices"],
                    "ivfpq_ready": "12h_ivfpq" in faiss_metrics["indices"],
                    "last_successful_search": faiss_detailed_health.get("latency_percentiles", {}).get("12h", {}).get("last_successful_search"),
                    "last_search_age_seconds": faiss_detailed_health.get("latency_percentiles", {}).get("12h", {}).get("last_search_age_seconds"),
                    "search_samples": faiss_detailed_health.get("latency_percentiles", {}).get("12h", {}).get("sample_count", 0)
                },
                "24h": {
                    "flatip_ready": "24h_flatip" in faiss_metrics["indices"],
                    "ivfpq_ready": "24h_ivfpq" in faiss_metrics["indices"],
                    "last_successful_search": faiss_detailed_health.get("latency_percentiles", {}).get("24h", {}).get("last_successful_search"),
                    "last_search_age_seconds": faiss_detailed_health.get("latency_percentiles", {}).get("24h", {}).get("last_search_age_seconds"),
                    "search_samples": faiss_detailed_health.get("latency_percentiles", {}).get("24h", {}).get("sample_count", 0)
                },
                "48h": {
                    "flatip_ready": "48h_flatip" in faiss_metrics["indices"],
                    "ivfpq_ready": "48h_ivfpq" in faiss_metrics["indices"],
                    "last_successful_search": faiss_detailed_health.get("latency_percentiles", {}).get("48h", {}).get("last_successful_search"),
                    "last_search_age_seconds": faiss_detailed_health.get("latency_percentiles", {}).get("48h", {}).get("last_search_age_seconds"),
                    "search_samples": faiss_detailed_health.get("latency_percentiles", {}).get("48h", {}).get("sample_count", 0)
                }
            },
            
            # Index validation metrics
            "index_validation": {
                "total_indices_available": len(faiss_metrics["indices"]),
                "expected_indices": 8,  # 4 horizons × 2 index types
                "indices_metadata": faiss_metrics["indices"],
                "dimension_validation": {
                    horizon: {
                        index_type: {
                            "dimension": idx_data.get("d", 0),
                            "expected_dimension": 768,  # Expected embedding dimension
                            "dimension_valid": idx_data.get("d", 0) == 768,
                            "ntotal": idx_data.get("ntotal", 0),
                            "ntotal_valid": idx_data.get("ntotal", 0) > 0
                        }
                        for index_type in ["flatip", "ivfpq"]
                        for idx_data in [faiss_metrics["indices"].get(f"{horizon}_{index_type}", {})]
                        if idx_data
                    }
                    for horizon in ["6h", "12h", "24h", "48h"]
                }
            },
            
            # Performance metrics
            "performance_metrics": {
                "query_performance": faiss_metrics["performance"],
                "latency_by_horizon": faiss_detailed_health.get("latency_percentiles", {}),
                "error_rate": faiss_detailed_health.get("query_performance", {}).get("error_rate", 0),
                "throughput_qps": faiss_detailed_health.get("query_performance", {}).get("total_queries", 0) / 60 if faiss_detailed_health.get("monitoring", {}).get("uptime_seconds", 0) > 60 else 0,
                "active_queries": faiss_detailed_health.get("query_performance", {}).get("active_queries", 0)
            },
            
            # Degraded mode and fallback tracking
            "degraded_mode": {
                "active": faiss_metrics["degraded_mode"],
                "fallback_counters": faiss_detailed_health.get("fallback_metrics", {
                    "total_fallbacks": 0,
                    "fallback_by_horizon": {"6h": 0, "12h": 0, "24h": 0, "48h": 0},
                    "fallback_by_reason": {},
                    "last_fallback_time": None,
                    "degraded_mode": {"active": False, "since": None, "reasons": []}
                })
            },
            
            # System resource metrics
            "system_resources": faiss_detailed_health.get("system", {}),
            
            # Monitoring status
            "monitoring": {
                "active": faiss_detailed_health.get("monitoring", {}).get("active", False),
                "uptime_seconds": faiss_detailed_health.get("monitoring", {}).get("uptime_seconds", 0),
                "last_health_update": faiss_check_result.timestamp.isoformat()
            }
        }
        
        # Determine appropriate HTTP status code
        if overall_status == "unhealthy":
            status_code = 503  # Service unavailable
        elif overall_status == "degraded":
            status_code = 200  # Service available but degraded
        else:
            status_code = 200  # Service healthy
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "faiss_status": "error",
                "message": f"FAISS health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "degraded_mode": {"active": True, "reason": "health_check_failure"}
            }
        )

@health_router.get("/security")
@limiter.limit("30/minute")
async def security_status_check(request: Request):
    """
    Security-focused health check including configuration drift detection.
    
    Provides:
    - Configuration drift status including weak token detection
    - Security-related drift events with detailed analysis
    - Token security metrics and recommendations
    - Overall security posture assessment
    """
    try:
        checker = get_health_checker()
        
        # Run configuration drift check
        config_drift_result = await checker._check_configuration_drift()
        
        # Extract security-specific information
        details = config_drift_result.details
        token_security = details.get("token_security", {})
        security_events = details.get("security_events", 0)
        critical_events = details.get("events_by_severity", {}).get("critical", 0)
        
        # Determine security status
        if config_drift_result.status == "fail":
            security_status = "critical"
            status_message = f"Critical security issues detected: {config_drift_result.message}"
        elif config_drift_result.status == "warn":
            security_status = "warning"
            status_message = f"Security warnings detected: {config_drift_result.message}"
        else:
            security_status = "secure"
            status_message = "No critical security drift detected"
        
        response_data = {
            "security_status": security_status,
            "message": status_message,
            "configuration_drift": {
                "status": config_drift_result.status,
                "message": config_drift_result.message,
                "monitoring_active": details.get("monitoring_active", False),
                "total_events": details.get("total_events", 0),
                "events_by_severity": details.get("events_by_severity", {}),
                "security_events": security_events
            },
            "token_security_analysis": token_security,
            "drift_events": details.get("drift_events", []),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "check_duration_ms": config_drift_result.duration_ms
        }
        
        # Return appropriate status code based on security status
        status_code = 200
        if security_status == "critical":
            status_code = 503  # Service unavailable due to security issues
        elif security_status == "warning":
            status_code = 200  # Service available but with warnings
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "security_status": "error",
                "message": f"Security check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )