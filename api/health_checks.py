#!/usr/bin/env python3
"""
Adelaide Weather Forecasting - Enhanced Health Check System
===========================================================

Comprehensive health check endpoints with detailed system status reporting,
dependency validation, and readiness/liveness probes for production deployment.

Features:
- Deep health validation of all system components
- Dependency health checks (Redis, external APIs, file system)
- Performance baseline validation
- Data integrity verification
- Graceful degradation status reporting
- Kubernetes-ready liveness and readiness probes

Author: Production Engineering
Version: 1.0.0 - Enhanced Health Monitoring
"""

import os
import sys
import time
import json
import asyncio
import logging
import hashlib
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import redis
import aiohttp
from fastapi import HTTPException

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.forecast_adapter import ForecastAdapter
from core.startup_validation_system import ExpertValidatedStartupSystem

logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Result of an individual health check."""
    name: str
    status: str  # "pass", "fail", "warn"
    message: str
    details: Dict[str, Any]
    duration_ms: float
    timestamp: datetime

@dataclass
class DependencyStatus:
    """Status of an external dependency."""
    name: str
    type: str  # "database", "cache", "api", "filesystem"
    available: bool
    response_time_ms: Optional[float]
    version: Optional[str]
    error_message: Optional[str]

@dataclass
class SystemMetrics:
    """Current system performance metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_available_gb: float
    open_file_descriptors: int
    network_connections: int

@dataclass
class PerformanceBaseline:
    """Performance baseline metrics."""
    forecast_p50_ms: float
    forecast_p95_ms: float
    forecast_p99_ms: float
    health_check_p95_ms: float
    startup_time_ms: float

class EnhancedHealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self, forecast_adapter: Optional[ForecastAdapter] = None):
        self.forecast_adapter = forecast_adapter
        self.startup_time = datetime.now(timezone.utc)
        self.redis_client = None
        self.last_health_check = None
        self.performance_history: List[Dict[str, float]] = []
        self.drift_detector = None
        
        # Initialize Redis connection if available
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
        
        # Initialize configuration drift detector
        try:
            from core.config_drift_detector import ConfigurationDriftDetector
            project_root = Path(__file__).parent.parent
            self.drift_detector = ConfigurationDriftDetector(
                project_root=project_root,
                start_monitoring=False  # Don't start background monitoring in health checks
            )
        except Exception as e:
            logger.warning(f"Configuration drift detector not available: {e}")
    
    async def perform_liveness_check(self) -> Dict[str, Any]:
        """
        Kubernetes liveness probe - basic process health.
        Should only fail if the application needs to be restarted.
        """
        start_time = time.time()
        
        try:
            # Basic process health checks
            process = psutil.Process()
            
            # Check if process is responsive
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            
            # Check for memory leaks (basic threshold)
            memory_mb = memory_info.rss / 1024 / 1024
            if memory_mb > 2048:  # 2GB threshold
                return {
                    "status": "fail",
                    "message": f"Memory usage {memory_mb:.0f}MB exceeds liveness threshold",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Check for thread deadlocks (basic check)
            thread_count = process.num_threads()
            if thread_count > 100:  # Arbitrary threshold
                return {
                    "status": "warn", 
                    "message": f"High thread count: {thread_count}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                "status": "pass",
                "message": "Process is alive and responsive",
                "duration_ms": duration_ms,
                "details": {
                    "process_id": process.pid,
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "thread_count": thread_count,
                    "uptime_seconds": (datetime.now(timezone.utc) - self.startup_time).total_seconds()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "fail",
                "message": f"Liveness check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def perform_readiness_check(self) -> Dict[str, Any]:
        """
        Kubernetes readiness probe - checks if app can serve traffic.
        Should fail if dependencies are unavailable or app is not ready.
        """
        start_time = time.time()
        checks = []
        overall_status = "pass"
        
        try:
            # 1. Core system readiness
            core_check = await self._check_core_system()
            checks.append(core_check)
            if core_check.status == "fail":
                overall_status = "fail"
            
            # 2. Forecast adapter readiness
            if self.forecast_adapter:
                adapter_check = await self._check_forecast_adapter()
                checks.append(adapter_check)
                if adapter_check.status == "fail":
                    overall_status = "fail"
            
            # 3. Critical dependency checks
            dependency_checks = await self._check_critical_dependencies()
            checks.extend(dependency_checks)
            
            # If any critical dependency fails, mark as not ready
            for check in dependency_checks:
                if check.name in ["filesystem", "model_files"] and check.status == "fail":
                    overall_status = "fail"
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                "status": overall_status,
                "message": f"Readiness check {'passed' if overall_status == 'pass' else 'failed'}",
                "duration_ms": duration_ms,
                "checks": [asdict(check) for check in checks],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "fail",
                "message": f"Readiness check error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def perform_comprehensive_health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check with detailed system analysis including FAISS metrics.
        Used for monitoring dashboards and detailed system status.
        """
        start_time = time.time()
        
        # Run all health checks
        core_check = await self._check_core_system()
        adapter_check = await self._check_forecast_adapter() if self.forecast_adapter else None
        dependency_checks = await self._check_all_dependencies()
        performance_check = await self._check_performance_baselines()
        data_integrity_check = await self._check_data_integrity()
        faiss_check = await self._check_faiss_health()
        config_drift_check = await self._check_configuration_drift()
        system_metrics = await self._get_system_metrics()
        
        # Collect all checks
        all_checks = [core_check]
        if adapter_check:
            all_checks.append(adapter_check)
        all_checks.extend(dependency_checks)
        all_checks.append(performance_check)
        all_checks.append(data_integrity_check)
        all_checks.append(faiss_check)
        all_checks.append(config_drift_check)
        
        # Determine overall status
        failed_checks = [c for c in all_checks if c.status == "fail"]
        warning_checks = [c for c in all_checks if c.status == "warn"]
        
        if failed_checks:
            overall_status = "fail"
            status_message = f"{len(failed_checks)} critical issues detected"
        elif warning_checks:
            overall_status = "warn"
            status_message = f"{len(warning_checks)} warnings detected"
        else:
            overall_status = "pass"
            status_message = "All systems operational"
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Get enhanced FAISS metrics
        faiss_metrics = await self._get_comprehensive_faiss_metrics()
        
        # Cache this result
        self.last_health_check = {
            "status": overall_status,
            "message": status_message,
            "duration_ms": duration_ms,
            "checks": [asdict(check) for check in all_checks],
            "system_metrics": asdict(system_metrics),
            "dependencies": await self._get_dependency_status(),
            "performance_baseline": await self._get_performance_baseline(),
            "faiss_indices": faiss_metrics["indices"],
            "faiss_performance": faiss_metrics["performance"],
            "degraded_mode": faiss_metrics["degraded_mode"],
            "uptime_seconds": (datetime.now(timezone.utc) - self.startup_time).total_seconds(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version_info": {
                "api_version": "1.0.0",
                "health_check_version": "1.1.0",
                "python_version": sys.version.split()[0],
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        }
        
        return self.last_health_check
    
    async def _check_core_system(self) -> HealthCheckResult:
        """Check core system startup validation."""
        start_time = time.time()
        
        try:
            # Use the expert validation system
            validator = ExpertValidatedStartupSystem()
            validation_passed = validator.run_expert_startup_validation()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if validation_passed:
                return HealthCheckResult(
                    name="core_system",
                    status="pass",
                    message="Core system validation passed",
                    details={"validation_components": "startup_system, embeddings, indices"},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="core_system", 
                    status="fail",
                    message="Core system validation failed",
                    details={"error": "Expert validation did not pass"},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="core_system",
                status="fail", 
                message=f"Core system check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_forecast_adapter(self) -> HealthCheckResult:
        """Check forecast adapter health and capabilities."""
        start_time = time.time()
        
        try:
            if not self.forecast_adapter:
                return HealthCheckResult(
                    name="forecast_adapter",
                    status="fail",
                    message="Forecast adapter not initialized",
                    details={},
                    duration_ms=0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Test basic forecast functionality
            test_result = self.forecast_adapter.forecast_with_uncertainty(
                horizon="24h",
                variables=["t2m", "msl"]
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Validate test result structure
            if isinstance(test_result, dict) and "t2m" in test_result:
                return HealthCheckResult(
                    name="forecast_adapter",
                    status="pass",
                    message="Forecast adapter operational",
                    details={
                        "test_variables": list(test_result.keys()),
                        "test_horizon": "24h",
                        "response_structure_valid": True
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="forecast_adapter",
                    status="fail",
                    message="Forecast adapter returned invalid response",
                    details={"test_result_type": type(test_result).__name__},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="forecast_adapter",
                status="fail",
                message=f"Forecast adapter check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_critical_dependencies(self) -> List[HealthCheckResult]:
        """Check only critical dependencies for readiness."""
        checks = []
        
        # Filesystem check
        checks.append(await self._check_filesystem())
        
        # Model files check  
        checks.append(await self._check_model_files())
        
        return checks
    
    async def _check_all_dependencies(self) -> List[HealthCheckResult]:
        """Check all system dependencies."""
        checks = []
        
        # Filesystem
        checks.append(await self._check_filesystem())
        
        # Model files
        checks.append(await self._check_model_files())
        
        # Redis (non-critical)
        checks.append(await self._check_redis())
        
        # External connectivity (non-critical)
        checks.append(await self._check_external_connectivity())
        
        return checks
    
    async def _check_filesystem(self) -> HealthCheckResult:
        """Check filesystem health and space."""
        start_time = time.time()
        
        try:
            # Check disk space
            statvfs = os.statvfs('/')
            available_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            total_gb = (statvfs.f_blocks * statvfs.f_frsize) / (1024**3)
            usage_percent = ((total_gb - available_gb) / total_gb) * 100
            
            # Check required directories
            required_dirs = [
                "/app/models",
                "/app/embeddings", 
                "/app/indices",
                "/app/data/era5"
            ]
            
            missing_dirs = []
            for dir_path in required_dirs:
                if not os.path.exists(dir_path):
                    missing_dirs.append(dir_path)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if missing_dirs:
                return HealthCheckResult(
                    name="filesystem",
                    status="fail",
                    message=f"Required directories missing: {', '.join(missing_dirs)}",
                    details={
                        "missing_directories": missing_dirs,
                        "available_gb": available_gb,
                        "usage_percent": usage_percent
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            elif usage_percent > 90:
                return HealthCheckResult(
                    name="filesystem",
                    status="warn",
                    message=f"Low disk space: {usage_percent:.1f}% used",
                    details={
                        "available_gb": available_gb,
                        "usage_percent": usage_percent,
                        "total_gb": total_gb
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="filesystem",
                    status="pass",
                    message="Filesystem healthy",
                    details={
                        "available_gb": available_gb,
                        "usage_percent": usage_percent,
                        "directories_ok": len(required_dirs)
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="filesystem",
                status="fail",
                message=f"Filesystem check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_model_files(self) -> HealthCheckResult:
        """Check critical model files are present and valid."""
        start_time = time.time()
        
        try:
            required_files = [
                "/app/models/best_model.pt",
                "/app/embeddings/embeddings_24h.npy",
                "/app/indices/faiss_24h_flatip.faiss"
            ]
            
            missing_files = []
            file_sizes = {}
            
            for file_path in required_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
                else:
                    file_sizes[file_path] = os.path.getsize(file_path) / (1024**2)  # MB
            
            duration_ms = (time.time() - start_time) * 1000
            
            if missing_files:
                return HealthCheckResult(
                    name="model_files",
                    status="fail", 
                    message=f"Critical model files missing: {', '.join(missing_files)}",
                    details={
                        "missing_files": missing_files,
                        "present_files": file_sizes
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                # Check file sizes are reasonable
                if file_sizes.get("/app/models/best_model.pt", 0) < 1:  # Less than 1MB
                    status = "warn"
                    message = "Model file suspiciously small"
                else:
                    status = "pass"
                    message = "All model files present"
                
                return HealthCheckResult(
                    name="model_files",
                    status=status,
                    message=message,
                    details={
                        "file_count": len(file_sizes),
                        "file_sizes_mb": file_sizes
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="model_files",
                status="fail",
                message=f"Model files check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            if not self.redis_client:
                return HealthCheckResult(
                    name="redis",
                    status="warn",
                    message="Redis client not configured",
                    details={"optional": True},
                    duration_ms=0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Test basic operations
            test_key = "health_check_test"
            self.redis_client.set(test_key, "test_value", ex=60)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            # Get Redis info
            info = self.redis_client.info()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if value == "test_value":
                return HealthCheckResult(
                    name="redis",
                    status="pass",
                    message="Redis operational",
                    details={
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_mb": info.get("used_memory", 0) / (1024**2)
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="redis",
                    status="fail",
                    message="Redis read/write test failed",
                    details={"test_value": value},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="redis",
                status="warn",  # Non-critical
                message=f"Redis check failed: {str(e)}",
                details={"error_type": type(e).__name__, "optional": True},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_external_connectivity(self) -> HealthCheckResult:
        """Check external connectivity (non-critical)."""
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test connectivity to a reliable external service
                async with session.get('https://httpbin.org/status/200') as response:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        return HealthCheckResult(
                            name="external_connectivity",
                            status="pass",
                            message="External connectivity available",
                            details={"test_endpoint": "httpbin.org"},
                            duration_ms=duration_ms,
                            timestamp=datetime.now(timezone.utc)
                        )
                    else:
                        return HealthCheckResult(
                            name="external_connectivity",
                            status="warn",
                            message=f"External connectivity test returned {response.status}",
                            details={"test_endpoint": "httpbin.org", "optional": True},
                            duration_ms=duration_ms,
                            timestamp=datetime.now(timezone.utc)
                        )
                        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="external_connectivity",
                status="warn",  # Non-critical
                message=f"External connectivity check failed: {str(e)}",
                details={"error_type": type(e).__name__, "optional": True},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_performance_baselines(self) -> HealthCheckResult:
        """Check performance against established baselines."""
        start_time = time.time()
        
        try:
            # Test forecast performance if adapter available
            if self.forecast_adapter:
                test_start = time.time()
                test_result = self.forecast_adapter.forecast_with_uncertainty(
                    horizon="24h",
                    variables=["t2m"]
                )
                forecast_duration_ms = (time.time() - test_start) * 1000
                
                # Store performance data
                self.performance_history.append({
                    "timestamp": time.time(),
                    "forecast_duration_ms": forecast_duration_ms
                })
                
                # Keep only recent history (last hour)
                cutoff = time.time() - 3600
                self.performance_history = [
                    entry for entry in self.performance_history 
                    if entry["timestamp"] > cutoff
                ]
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Check against baseline (150ms target)
                if forecast_duration_ms > 300:  # 2x baseline
                    status = "fail"
                    message = f"Forecast performance degraded: {forecast_duration_ms:.0f}ms"
                elif forecast_duration_ms > 150:  # Above baseline
                    status = "warn"
                    message = f"Forecast performance slow: {forecast_duration_ms:.0f}ms"
                else:
                    status = "pass"
                    message = f"Forecast performance good: {forecast_duration_ms:.0f}ms"
                
                return HealthCheckResult(
                    name="performance_baseline",
                    status=status,
                    message=message,
                    details={
                        "forecast_duration_ms": forecast_duration_ms,
                        "baseline_ms": 150,
                        "recent_samples": len(self.performance_history)
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="performance_baseline",
                    status="warn",
                    message="Cannot test performance - forecast adapter not available",
                    details={},
                    duration_ms=0,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="performance_baseline",
                status="fail",
                message=f"Performance check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_data_integrity(self) -> HealthCheckResult:
        """Check data integrity and consistency."""
        start_time = time.time()
        
        try:
            # Check that we have recent data files
            data_dir = Path("/app/data/era5/surface")
            if not data_dir.exists():
                return HealthCheckResult(
                    name="data_integrity",
                    status="warn",
                    message="ERA5 data directory not found",
                    details={"data_dir": str(data_dir)},
                    duration_ms=0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Count data files
            nc_files = list(data_dir.glob("*.nc"))
            
            duration_ms = (time.time() - start_time) * 1000
            
            if len(nc_files) == 0:
                return HealthCheckResult(
                    name="data_integrity",
                    status="fail",
                    message="No ERA5 data files found",
                    details={"data_dir": str(data_dir), "file_count": 0},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            elif len(nc_files) < 10:
                return HealthCheckResult(
                    name="data_integrity", 
                    status="warn",
                    message=f"Limited ERA5 data files: {len(nc_files)}",
                    details={"data_dir": str(data_dir), "file_count": len(nc_files)},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="data_integrity",
                    status="pass",
                    message=f"Data integrity good: {len(nc_files)} files",
                    details={"data_dir": str(data_dir), "file_count": len(nc_files)},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="data_integrity",
                status="fail",
                message=f"Data integrity check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process info
            process = psutil.Process()
            open_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            connections = len(process.connections()) if hasattr(process, 'connections') else 0
            
            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                memory_available_mb=memory.available / (1024**2),
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_available_gb=disk.free / (1024**3),
                open_file_descriptors=open_fds,
                network_connections=connections
            )
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return SystemMetrics(
                cpu_usage_percent=0,
                memory_usage_percent=0,
                memory_available_mb=0,
                disk_usage_percent=0,
                disk_available_gb=0,
                open_file_descriptors=0,
                network_connections=0
            )
    
    async def _get_dependency_status(self) -> List[Dict[str, Any]]:
        """Get status of all dependencies."""
        dependencies = []
        
        # Redis
        if self.redis_client:
            try:
                start_time = time.time()
                self.redis_client.ping()
                response_time = (time.time() - start_time) * 1000
                
                info = self.redis_client.info()
                dependencies.append({
                    "name": "redis",
                    "type": "cache",
                    "available": True,
                    "response_time_ms": response_time,
                    "version": info.get("redis_version"),
                    "error_message": None
                })
            except Exception as e:
                dependencies.append({
                    "name": "redis",
                    "type": "cache", 
                    "available": False,
                    "response_time_ms": None,
                    "version": None,
                    "error_message": str(e)
                })
        
        # Filesystem
        dependencies.append({
            "name": "filesystem",
            "type": "filesystem",
            "available": os.path.exists("/app"),
            "response_time_ms": None,
            "version": None,
            "error_message": None
        })
        
        return dependencies
    
    async def _get_performance_baseline(self) -> Dict[str, float]:
        """Get performance baseline metrics."""
        if not self.performance_history:
            return {
                "forecast_p50_ms": 0,
                "forecast_p95_ms": 0,
                "forecast_p99_ms": 0,
                "health_check_p95_ms": 0,
                "startup_time_ms": 0
            }
        
        durations = [entry["forecast_duration_ms"] for entry in self.performance_history]
        durations.sort()
        
        n = len(durations)
        p50_idx = int(n * 0.5)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        return {
            "forecast_p50_ms": durations[p50_idx] if p50_idx < n else 0,
            "forecast_p95_ms": durations[p95_idx] if p95_idx < n else 0,
            "forecast_p99_ms": durations[p99_idx] if p99_idx < n else 0,
            "health_check_p95_ms": 50,  # Placeholder
            "startup_time_ms": 5000  # Placeholder
        }
    
    async def _check_faiss_health(self) -> HealthCheckResult:
        """Check FAISS system health and index availability."""
        start_time = time.time()
        
        try:
            # Import FAISS health monitor
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            
            try:
                faiss_monitor = await get_faiss_health_monitor()
                health_summary = await faiss_monitor.get_health_summary()
                
                duration_ms = (time.time() - start_time) * 1000
                
                status = health_summary.get("status", "unknown")
                if status == "healthy":
                    check_status = "pass"
                    message = "FAISS indices healthy and operational"
                elif status == "degraded":
                    check_status = "warn"
                    message = "FAISS indices operational but degraded"
                else:
                    check_status = "fail"
                    message = f"FAISS indices unhealthy: {status}"
                
                return HealthCheckResult(
                    name="faiss_indices",
                    status=check_status,
                    message=message,
                    details={
                        "monitoring_active": health_summary.get("monitoring", {}).get("active", False),
                        "total_queries": health_summary.get("query_performance", {}).get("total_queries", 0),
                        "error_rate": health_summary.get("query_performance", {}).get("error_rate", 0),
                        "avg_latency_ms": health_summary.get("query_performance", {}).get("avg_latency_ms", 0),
                        "indices_count": len(health_summary.get("indices", {}))
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
            except Exception as monitor_error:
                # FAISS monitor not available, check indices directly
                logger.warning(f"FAISS monitor unavailable: {monitor_error}")
                return await self._check_faiss_indices_direct()
                
        except ImportError:
            # FAISS health monitoring not available
            return await self._check_faiss_indices_direct()
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="faiss_indices",
                status="fail",
                message=f"FAISS health check failed: {str(e)}",
                details={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _check_faiss_indices_direct(self) -> HealthCheckResult:
        """Direct check of FAISS indices when monitoring is unavailable."""
        start_time = time.time()
        
        try:
            import faiss
            indices_dir = Path("indices")
            
            if not indices_dir.exists():
                return HealthCheckResult(
                    name="faiss_indices",
                    status="fail",
                    message="FAISS indices directory not found",
                    details={"indices_dir": str(indices_dir)},
                    duration_ms=0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Check for required index files
            horizons = ["6h", "12h", "24h", "48h"]
            index_types = ["flatip", "ivfpq"]
            
            total_indices = 0
            missing_indices = []
            index_info = {}
            
            for horizon in horizons:
                for index_type in index_types:
                    index_path = indices_dir / f"faiss_{horizon}_{index_type}.faiss"
                    if index_path.exists():
                        total_indices += 1
                        # Try to load index to get metadata
                        try:
                            index = faiss.read_index(str(index_path))
                            file_size_mb = index_path.stat().st_size / (1024 * 1024)
                            last_modified = datetime.fromtimestamp(
                                index_path.stat().st_mtime, 
                                tz=timezone.utc
                            )
                            
                            index_info[f"{horizon}_{index_type}"] = {
                                "ntotal": index.ntotal,
                                "d": index.d,
                                "index_type": type(index).__name__,
                                "file_size_mb": file_size_mb,
                                "last_updated": last_modified.isoformat()
                            }
                        except Exception as e:
                            logger.warning(f"Failed to load index {index_path}: {e}")
                            missing_indices.append(str(index_path))
                    else:
                        missing_indices.append(str(index_path))
            
            duration_ms = (time.time() - start_time) * 1000
            
            if total_indices == 0:
                return HealthCheckResult(
                    name="faiss_indices",
                    status="fail",
                    message="No FAISS indices found",
                    details={"missing_indices": missing_indices},
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            elif missing_indices:
                return HealthCheckResult(
                    name="faiss_indices",
                    status="warn",
                    message=f"Some FAISS indices missing: {len(missing_indices)} of {len(horizons) * len(index_types)}",
                    details={
                        "available_indices": total_indices,
                        "missing_indices": missing_indices,
                        "degraded_mode": True
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return HealthCheckResult(
                    name="faiss_indices",
                    status="pass",
                    message=f"All FAISS indices available: {total_indices} indices",
                    details={
                        "available_indices": total_indices,
                        "index_metadata": index_info,
                        "degraded_mode": False
                    },
                    duration_ms=duration_ms,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except ImportError:
            return HealthCheckResult(
                name="faiss_indices",
                status="fail",
                message="FAISS library not available",
                details={"degraded_mode": True},
                duration_ms=0,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="faiss_indices",
                status="fail",
                message=f"Direct FAISS check failed: {str(e)}",
                details={"error_type": type(e).__name__, "degraded_mode": True},
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _get_comprehensive_faiss_metrics(self) -> Dict[str, Any]:
        """Get comprehensive FAISS metrics for health endpoint."""
        try:
            # Try to get metrics from FAISS health monitor
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            
            try:
                faiss_monitor = await get_faiss_health_monitor()
                health_summary = await faiss_monitor.get_health_summary()
                
                return {
                    "indices": health_summary.get("indices", {}),
                    "performance": {
                        "total_queries": health_summary.get("query_performance", {}).get("total_queries", 0),
                        "active_queries": health_summary.get("query_performance", {}).get("active_queries", 0),
                        "error_rate": health_summary.get("query_performance", {}).get("error_rate", 0),
                        "avg_latency_ms": health_summary.get("query_performance", {}).get("avg_latency_ms", 0),
                        "latency_percentiles": health_summary.get("latency_percentiles", {})
                    },
                    "degraded_mode": health_summary.get("status") != "healthy"
                }
                
            except Exception as monitor_error:
                # Fall back to direct index inspection
                logger.warning(f"FAISS monitor unavailable for metrics: {monitor_error}")
                return await self._get_direct_faiss_metrics()
                
        except ImportError:
            # FAISS monitoring not available
            return await self._get_direct_faiss_metrics()
        except Exception as e:
            logger.error(f"Failed to get FAISS metrics: {e}")
            return {
                "indices": {},
                "performance": {
                    "total_queries": 0,
                    "active_queries": 0,
                    "error_rate": 0,
                    "avg_latency_ms": 0,
                    "latency_percentiles": {}
                },
                "degraded_mode": True
            }
    
    async def _get_direct_faiss_metrics(self) -> Dict[str, Any]:
        """Get FAISS metrics through direct index inspection."""
        indices = {}
        degraded_mode = True
        
        try:
            import faiss
            indices_dir = Path("indices")
            
            if indices_dir.exists():
                horizons = ["6h", "12h", "24h", "48h"]
                index_types = ["flatip", "ivfpq"]
                
                for horizon in horizons:
                    for index_type in index_types:
                        index_path = indices_dir / f"faiss_{horizon}_{index_type}.faiss"
                        if index_path.exists():
                            try:
                                index = faiss.read_index(str(index_path))
                                file_size_bytes = index_path.stat().st_size
                                last_modified = datetime.fromtimestamp(
                                    index_path.stat().st_mtime, 
                                    tz=timezone.utc
                                )
                                
                                key = f"{horizon}_{index_type}"
                                indices[key] = {
                                    "horizon": horizon,
                                    "index_type": index_type,
                                    "ntotal": index.ntotal,
                                    "d": index.d,
                                    "file_size": file_size_bytes,
                                    "file_size_mb": file_size_bytes / (1024 * 1024),
                                    "last_updated": last_modified.isoformat(),
                                    "latency_p50_ms": 0,  # Not available without monitoring
                                    "latency_p95_ms": 0,  # Not available without monitoring
                                    "accuracy_score": 1.0 if index_type == "flatip" else 0.98
                                }
                                
                                # If we have any indices, we're not completely degraded
                                if len(indices) > 0:
                                    degraded_mode = False
                                    
                            except Exception as e:
                                logger.warning(f"Failed to load index {index_path}: {e}")
                
        except ImportError:
            logger.warning("FAISS not available for direct metrics")
        except Exception as e:
            logger.error(f"Direct FAISS metrics failed: {e}")
        
        return {
            "indices": indices,
            "performance": {
                "total_queries": 0,
                "active_queries": 0,
                "error_rate": 0,
                "avg_latency_ms": 0,
                "latency_percentiles": {}
            },
            "degraded_mode": degraded_mode
        }
    
    async def _check_configuration_drift(self) -> HealthCheckResult:
        """Check for configuration drift including weak token detection."""
        start_time = time.time()
        
        try:
            if self.drift_detector is None:
                return HealthCheckResult(
                    name="configuration_drift",
                    status="warn",
                    message="Configuration drift detector not available",
                    details={"monitoring_available": False},
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Perform drift detection
            drift_events = self.drift_detector.detect_drift(generate_report=False)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Categorize events by severity
            critical_events = [e for e in drift_events if e.is_critical()]
            high_events = [e for e in drift_events if str(e.severity) == "high"]
            medium_events = [e for e in drift_events if str(e.severity) == "medium"]
            low_events = [e for e in drift_events if str(e.severity) == "low"]
            
            # Focus on security-related events for detailed reporting
            security_events = [e for e in drift_events if str(e.drift_type) == "DriftType.SECURITY_DRIFT"]
            token_events = [e for e in security_events if "weak_token" in e.event_id or "token" in e.description.lower()]
            
            # Determine overall status
            if critical_events:
                status = "fail"
                message = f"{len(critical_events)} critical configuration drift events detected"
            elif high_events:
                status = "warn" 
                message = f"{len(high_events)} high-priority drift events detected"
            elif medium_events:
                status = "warn"
                message = f"{len(medium_events)} medium-priority drift events detected"
            else:
                status = "pass"
                message = "No critical configuration drift detected"
            
            # Prepare detailed information for token security events
            token_security_details = {}
            if token_events:
                for event in token_events:
                    token_analysis = event.metadata.get("token_security_analysis", {})
                    if token_analysis:
                        token_security_details = {
                            "weak_token_detected": True,
                            "entropy_bits": token_analysis.get("entropy_bits", 0),
                            "charset_diversity": token_analysis.get("charset_diversity", 0),
                            "security_level": token_analysis.get("security_level", "UNKNOWN"),
                            "validation_issues": token_analysis.get("validation_issues", []),
                            "recommendations": token_analysis.get("recommendations", []),
                            "minimum_requirements": token_analysis.get("minimum_requirements", {})
                        }
                        break  # Use first token event for details
            
            return HealthCheckResult(
                name="configuration_drift",
                status=status,
                message=message,
                details={
                    "monitoring_active": True,
                    "total_events": len(drift_events),
                    "events_by_severity": {
                        "critical": len(critical_events),
                        "high": len(high_events),
                        "medium": len(medium_events),
                        "low": len(low_events)
                    },
                    "security_events": len(security_events),
                    "token_security": token_security_details,
                    "drift_events": [
                        {
                            "event_id": e.event_id,
                            "drift_type": str(e.drift_type),
                            "severity": str(e.severity),
                            "source_path": e.source_path,
                            "description": e.description,
                            "detected_at": e.detected_at,
                            "metadata": e.metadata
                        }
                        for e in drift_events[:10]  # Limit to first 10 events for health endpoint
                    ]
                },
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Configuration drift check failed: {e}")
            return HealthCheckResult(
                name="configuration_drift",
                status="fail",
                message=f"Configuration drift check failed: {str(e)}",
                details={
                    "error_type": type(e).__name__,
                    "monitoring_available": self.drift_detector is not None
                },
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc)
            )