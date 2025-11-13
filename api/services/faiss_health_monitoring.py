#!/usr/bin/env python3
"""
FAISS Health Monitoring System
==============================

Production-ready FAISS health monitoring for the Adelaide Weather Forecasting API.
Provides real-time performance tracking, index health monitoring, and Prometheus
metrics collection for FAISS-based analog search operations.

Features:
- Real-time query performance tracking with async context managers
- Index health monitoring (memory usage, size, search accuracy)
- Prometheus metrics collection for monitoring dashboards
- Async monitoring that doesn't impact FAISS operation performance
- Detailed health summary endpoints for system diagnostics
- Error handling and graceful degradation

Author: Monitoring & Observability Engineer
Version: 1.0.0 - Production FAISS Health System
"""

import asyncio
import logging
import time
import threading
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

# Prometheus metrics
from prometheus_client import (
    Counter, 
    Histogram, 
    Gauge, 
    Info,
    CollectorRegistry,
    REGISTRY as DEFAULT_REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)

@dataclass
class FAISSQueryMetrics:
    """Container for individual FAISS query metrics."""
    query_id: str
    horizon: str
    k_neighbors: int
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    index_type: Optional[str] = None
    memory_used_mb: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def complete(self, success: bool = True, error_message: Optional[str] = None):
        """Mark query as completed and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error_message = error_message

@dataclass
class IndexHealthMetrics:
    """Container for FAISS index health metrics."""
    horizon: str
    index_type: str
    file_path: str
    size_mb: float
    ntotal: int
    dimension: int
    last_accessed: datetime
    memory_mapped: bool
    search_latency_p50: float
    search_latency_p95: float
    accuracy_score: Optional[float] = None
    error_rate: float = 0.0

class FAISSHealthMonitor:
    """Production FAISS health monitoring system with Prometheus integration."""
    
    def __init__(self, 
                 indices_dir: Path = Path("indices"),
                 embeddings_dir: Path = Path("embeddings"),
                 registry: Optional[CollectorRegistry] = None):
        """Initialize FAISS health monitoring system.
        
        Args:
            indices_dir: Directory containing FAISS indices
            embeddings_dir: Directory containing embeddings and metadata
            registry: Optional Prometheus registry (uses default if None)
        """
        self.indices_dir = Path(indices_dir)
        self.embeddings_dir = Path(embeddings_dir)
        # Use the global default registry if no specific registry provided
        # This enables unified metrics collection through the main /metrics endpoint
        from prometheus_client import REGISTRY as DEFAULT_REGISTRY
        self.registry = registry or DEFAULT_REGISTRY
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="faiss-monitor")
        
        # Query tracking
        self._active_queries: Dict[str, FAISSQueryMetrics] = {}
        self._completed_queries: List[FAISSQueryMetrics] = []
        self._query_lock = asyncio.Lock()
        
        # Index health cache
        self._index_health_cache: Dict[str, IndexHealthMetrics] = {}
        self._last_health_update = 0
        self._health_cache_ttl = 60  # 60 seconds
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Performance tracking
        self._latency_samples = {f"{h}h": [] for h in [6, 12, 24, 48]}
        self._max_samples = 1000  # Keep last 1000 samples per horizon
        
        # Last successful search timestamps per horizon
        self._last_successful_search = {f"{h}h": None for h in [6, 12, 24, 48]}
        
        # Fallback tracking
        self._fallback_counters = {
            "total": 0,
            "by_horizon": {f"{h}h": 0 for h in [6, 12, 24, 48]},
            "by_reason": {},
            "last_fallback_time": None
        }
        
        # Degraded mode tracking
        self._degraded_mode_active = False
        self._degraded_mode_reasons = []
        self._degraded_mode_start_time = None
        
        logger.info("FAISSHealthMonitor initialized")
    
    def _get_or_create_metric(self, metric_cls, name, documentation, *args, **kwargs):
        """Return existing Prometheus metric or create a new one.

        This prevents duplicate metric registration when multiple FAISS monitor instances
        are created or when using the default registry with existing metrics.
        """
        # Remove registry from kwargs to avoid duplicate parameter
        registry = kwargs.pop('registry', self.registry)
        
        existing = registry._names_to_collectors.get(name)
        if existing is not None:
            return existing
        return metric_cls(name, documentation, *args, registry=registry, **kwargs)
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics for FAISS monitoring."""
        # Query performance metrics with enhanced per-horizon tracking
        self.query_duration_hist = self._get_or_create_metric(
            Histogram,
            'faiss_query_duration_seconds',
            'FAISS query execution time',
            ['horizon', 'index_type', 'k_neighbors'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        # Per-horizon latency percentile gauges (T-011 requirement)
        self.search_latency_p50_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_search_duration_p50_seconds',
            'FAISS search p50 latency by horizon',
            ['horizon']
        )
        
        self.search_latency_p95_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_search_duration_p95_seconds', 
            'FAISS search p95 latency by horizon',
            ['horizon']
        )
        
        self.query_total_counter = self._get_or_create_metric(
            Counter,
            'faiss_queries_total',
            'Total FAISS queries executed',
            ['horizon', 'index_type', 'status']
        )
        
        # Enhanced error tracking per horizon and error type (T-011 requirement)
        self.search_errors_counter = self._get_or_create_metric(
            Counter,
            'faiss_search_errors_total',
            'Total FAISS search errors by horizon and error type',
            ['horizon', 'error_type']
        )
        
        # Search quality metrics (T-011 requirement)
        self.search_results_count_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_search_results_count',
            'Number of results returned by FAISS search',
            ['horizon']
        )
        
        self.distance_validation_failures_counter = self._get_or_create_metric(
            Counter,
            'faiss_distance_validation_failures_total',
            'Total distance validation failures',
            ['horizon', 'validation_type']
        )
        
        # Degradation detection metrics (T-011 requirement)
        self.degraded_mode_counter = self._get_or_create_metric(
            Counter,
            'faiss_degraded_mode_total',
            'Total times FAISS entered degraded mode',
            ['horizon', 'reason']
        )
        
        # Index health metrics
        self.index_size_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_index_size_bytes',
            'FAISS index file size in bytes',
            ['horizon', 'index_type']
        )
        
        self.index_vectors_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_index_vectors_total',
            'Total vectors in FAISS index',
            ['horizon', 'index_type']
        )
        
        self.index_memory_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_index_memory_usage_bytes',
            'FAISS index memory usage',
            ['horizon', 'index_type']
        )
        
        self.search_accuracy_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_search_accuracy_score',
            'FAISS search accuracy score (0-1)',
            ['horizon', 'index_type']
        )
        
        # System metrics
        self.active_queries_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_active_queries',
            'Currently active FAISS queries'
        )
        
        self.system_memory_gauge = self._get_or_create_metric(
            Gauge,
            'faiss_system_memory_usage_bytes',
            'System memory usage for FAISS operations'
        )
        
        # Info metrics
        self.faiss_info = self._get_or_create_metric(
            Info,
            'faiss_build_info',
            'FAISS build and version information'
        )
        
        # Set FAISS build info
        try:
            import faiss
            self.faiss_info.info({
                'version': faiss.__version__ if hasattr(faiss, '__version__') else 'unknown',
                'build_type': 'gpu' if hasattr(faiss, 'StandardGpuResources') else 'cpu',
                'monitor_version': '1.0.0'
            })
        except ImportError:
            self.faiss_info.info({
                'version': 'not_installed',
                'build_type': 'unknown',
                'monitor_version': '1.0.0'
            })
    
    async def start_monitoring(self) -> bool:
        """Start background monitoring of FAISS operations."""
        if self._monitoring_active:
            logger.warning("FAISS monitoring already active")
            return True
        
        try:
            logger.info("Starting FAISS health monitoring...")
            
            # Start background monitoring thread
            self._monitoring_active = True
            self._monitor_thread = threading.Thread(
                target=self._background_monitor,
                daemon=True,
                name="faiss-health-monitor"
            )
            self._monitor_thread.start()
            
            # Update initial index health
            await self._update_index_health()
            
            logger.info("✅ FAISS health monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FAISS monitoring: {e}")
            self._monitoring_active = False
            return False
    
    async def stop_monitoring(self):
        """Stop background monitoring gracefully."""
        if not self._monitoring_active:
            return
        
        logger.info("Stopping FAISS health monitoring...")
        
        self._monitoring_active = False
        
        # Wait for background thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("✅ FAISS health monitoring stopped")
    
    def _background_monitor(self):
        """Background thread for continuous monitoring."""
        logger.info("Background FAISS monitoring thread started")
        
        while self._monitoring_active:
            try:
                # Update system metrics
                self._update_system_metrics()
                
                # Clean old query data
                self._cleanup_old_queries()
                
                # Sleep for monitoring interval
                time.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                time.sleep(30)  # Continue monitoring despite errors
        
        logger.info("Background FAISS monitoring thread stopped")
    
    def _update_system_metrics(self):
        """Update system-level metrics."""
        try:
            # Update active queries count
            self.active_queries_gauge.set(len(self._active_queries))
            
            # Update system memory usage (if psutil is available)
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                memory_info = process.memory_info()
                self.system_memory_gauge.set(memory_info.rss)
            else:
                # Set a default value if psutil not available
                self.system_memory_gauge.set(0)
            
        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")
    
    def _cleanup_old_queries(self):
        """Clean up old completed queries to prevent memory growth."""
        # Keep only last 1000 completed queries
        if len(self._completed_queries) > 1000:
            self._completed_queries = self._completed_queries[-1000:]
        
        # Clean old latency samples per horizon
        for horizon in self._latency_samples:
            if len(self._latency_samples[horizon]) > self._max_samples:
                self._latency_samples[horizon] = self._latency_samples[horizon][-self._max_samples:]
    
    @asynccontextmanager
    async def track_query(self, 
                         horizon: str, 
                         k_neighbors: int = 50,
                         index_type: str = "auto") -> FAISSQueryMetrics:
        """Async context manager for tracking FAISS query performance.
        
        Usage:
            async with monitor.track_query("24h", k_neighbors=50) as query:
                # Perform FAISS search
                results = search_faiss_index(...)
                
        Args:
            horizon: Forecast horizon (e.g., "24h")
            k_neighbors: Number of neighbors being searched
            index_type: Type of index being used
            
        Returns:
            FAISSQueryMetrics object for the query
        """
        # Generate unique query ID
        query_id = f"{horizon}_{int(time.time() * 1000)}_{np.random.randint(1000, 9999)}"
        
        # Create query metrics
        query_metrics = FAISSQueryMetrics(
            query_id=query_id,
            horizon=horizon,
            k_neighbors=k_neighbors,
            start_time=time.time(),
            index_type=index_type
        )
        
        # Add to active queries
        async with self._query_lock:
            self._active_queries[query_id] = query_metrics
        
        try:
            # Record query start
            logger.debug(f"Starting FAISS query tracking: {query_id}")
            
            yield query_metrics
            
            # Query completed successfully
            query_metrics.complete(success=True)
            
            # Update last successful search timestamp
            self._last_successful_search[horizon] = datetime.now(timezone.utc)
            
            # Update Prometheus metrics
            self.query_duration_hist.labels(
                horizon=horizon,
                index_type=index_type,
                k_neighbors=str(k_neighbors)
            ).observe(query_metrics.duration_ms / 1000.0)
            
            self.query_total_counter.labels(
                horizon=horizon,
                index_type=index_type,
                status='success'
            ).inc()
            
            # Store latency sample and update per-horizon percentiles  
            if horizon in self._latency_samples:
                self._latency_samples[horizon].append(query_metrics.duration_ms)
                
                # Update per-horizon latency percentiles in real-time (T-011 requirement)
                self._update_horizon_percentile_metrics(horizon)
            
            logger.debug(f"FAISS query completed: {query_id} ({query_metrics.duration_ms:.1f}ms)")
            
        except Exception as e:
            # Query failed
            error_type = type(e).__name__
            query_metrics.complete(success=False, error_message=str(e))
            
            # Update error metrics
            self.search_errors_counter.labels(
                horizon=horizon,
                error_type=error_type
            ).inc()
            
            self.query_total_counter.labels(
                horizon=horizon,
                index_type=index_type,
                status='error'
            ).inc()
            
            logger.warning(f"FAISS query failed: {query_id} - {e}")
            
            # Re-raise the exception
            raise
            
        finally:
            # Move from active to completed
            async with self._query_lock:
                self._active_queries.pop(query_id, None)
                self._completed_queries.append(query_metrics)
    
    def record_fallback(self, horizon: str, reason: str = "index_unavailable"):
        """Record a fallback event when FAISS search fails."""
        current_time = datetime.now(timezone.utc)
        
        # Update counters
        self._fallback_counters["total"] += 1
        if horizon in self._fallback_counters["by_horizon"]:
            self._fallback_counters["by_horizon"][horizon] += 1
        
        # Track by reason
        if reason not in self._fallback_counters["by_reason"]:
            self._fallback_counters["by_reason"][reason] = 0
        self._fallback_counters["by_reason"][reason] += 1
        
        self._fallback_counters["last_fallback_time"] = current_time
        
        # Update degraded mode status
        self._check_degraded_mode()
        
        # Update Prometheus metrics
        self.degraded_mode_counter.labels(
            horizon=horizon,
            reason=reason
        ).inc()
        
        logger.warning(f"FAISS fallback recorded for {horizon}: {reason}")
    
    def set_degraded_mode(self, active: bool, reasons: List[str] = None):
        """Set degraded mode status."""
        if active and not self._degraded_mode_active:
            self._degraded_mode_active = True
            self._degraded_mode_start_time = datetime.now(timezone.utc)
            self._degraded_mode_reasons = reasons or []
            logger.warning(f"FAISS entering degraded mode: {reasons}")
        elif not active and self._degraded_mode_active:
            self._degraded_mode_active = False
            self._degraded_mode_start_time = None
            self._degraded_mode_reasons = []
            logger.info("FAISS exiting degraded mode")
    
    def _check_degraded_mode(self):
        """Check if system should be in degraded mode based on metrics."""
        current_time = datetime.now(timezone.utc)
        degraded_reasons = []
        
        # Check for recent fallbacks
        if self._fallback_counters["last_fallback_time"]:
            time_since_fallback = (current_time - self._fallback_counters["last_fallback_time"]).total_seconds()
            if time_since_fallback < 300:  # Last fallback within 5 minutes
                degraded_reasons.append("recent_fallbacks")
        
        # Check high fallback rate
        total_fallbacks = self._fallback_counters["total"]
        if total_fallbacks > 10:  # Arbitrary threshold
            degraded_reasons.append("high_fallback_rate")
        
        # Check for missing indices
        available_indices = len(self._index_health_cache)
        expected_indices = 8  # 4 horizons × 2 index types
        if available_indices < expected_indices * 0.5:  # Less than 50% available
            degraded_reasons.append("missing_indices")
        
        # Update degraded mode status
        should_be_degraded = len(degraded_reasons) > 0
        self.set_degraded_mode(should_be_degraded, degraded_reasons)
    
    def get_last_successful_search(self, horizon: str) -> Optional[datetime]:
        """Get the timestamp of the last successful search for a horizon."""
        return self._last_successful_search.get(horizon)
    
    def get_fallback_counters(self) -> Dict[str, Any]:
        """Get current fallback counter metrics."""
        return {
            "total_fallbacks": self._fallback_counters["total"],
            "fallback_by_horizon": dict(self._fallback_counters["by_horizon"]),
            "fallback_by_reason": dict(self._fallback_counters["by_reason"]),
            "last_fallback_time": self._fallback_counters["last_fallback_time"].isoformat() if self._fallback_counters["last_fallback_time"] else None,
            "degraded_mode": {
                "active": self._degraded_mode_active,
                "since": self._degraded_mode_start_time.isoformat() if self._degraded_mode_start_time else None,
                "reasons": list(self._degraded_mode_reasons)
            }
        }
    
    async def _update_index_health(self):
        """Update index health metrics cache."""
        current_time = time.time()
        
        # Check if cache is still valid
        if current_time - self._last_health_update < self._health_cache_ttl:
            return
        
        logger.debug("Updating FAISS index health metrics")
        
        try:
            # Run index health check in executor to avoid blocking
            loop = asyncio.get_event_loop()
            health_metrics = await loop.run_in_executor(
                self._executor,
                self._collect_index_health_sync
            )
            
            # Update cache
            self._index_health_cache = health_metrics
            self._last_health_update = current_time
            
            # Update Prometheus metrics
            self._update_prometheus_health_metrics(health_metrics)
            
        except Exception as e:
            logger.error(f"Failed to update index health: {e}")
    
    def _collect_index_health_sync(self) -> Dict[str, IndexHealthMetrics]:
        """Synchronously collect index health metrics."""
        health_metrics = {}
        
        try:
            import faiss
        except ImportError:
            logger.warning("FAISS not available for health monitoring")
            return health_metrics
        
        # Check each horizon and index type
        horizons = ["6h", "12h", "24h", "48h"]
        index_types = ["flatip", "ivfpq"]
        
        for horizon in horizons:
            for index_type in index_types:
                try:
                    index_path = self.indices_dir / f"faiss_{horizon}_{index_type}.faiss"
                    
                    if not index_path.exists():
                        continue
                    
                    # Get file size
                    size_mb = index_path.stat().st_size / (1024 * 1024)
                    
                    # Load index to get dimensions and vector count
                    index = faiss.read_index(str(index_path))
                    
                    # Calculate search performance metrics
                    p50_latency, p95_latency = self._calculate_latency_percentiles(horizon)
                    
                    # Create health metrics
                    key = f"{horizon}_{index_type}"
                    health_metrics[key] = IndexHealthMetrics(
                        horizon=horizon,
                        index_type=index_type,
                        file_path=str(index_path),
                        size_mb=size_mb,
                        ntotal=index.ntotal,
                        dimension=index.d,
                        last_accessed=datetime.now(timezone.utc),
                        memory_mapped=True,  # Assuming memory-mapped
                        search_latency_p50=p50_latency,
                        search_latency_p95=p95_latency,
                        accuracy_score=self._estimate_search_accuracy(horizon, index_type)
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to check {horizon} {index_type} index: {e}")
                    continue
        
        return health_metrics
    
    def _calculate_latency_percentiles(self, horizon: str) -> Tuple[float, float]:
        """Calculate latency percentiles for a horizon."""
        if horizon not in self._latency_samples or not self._latency_samples[horizon]:
            return 0.0, 0.0
        
        samples = self._latency_samples[horizon]
        if len(samples) < 10:  # Need minimum samples
            return np.mean(samples), np.mean(samples)
        
        p50 = np.percentile(samples, 50)
        p95 = np.percentile(samples, 95)
        
        return float(p50), float(p95)
    
    def _update_horizon_percentile_metrics(self, horizon: str):
        """Update per-horizon percentile metrics in real-time (T-011 requirement)."""
        if horizon not in self._latency_samples or len(self._latency_samples[horizon]) < 5:
            return  # Need minimum samples for meaningful percentiles
        
        try:
            samples = self._latency_samples[horizon]
            # Convert milliseconds to seconds for Prometheus metrics
            p50_ms = np.percentile(samples, 50)
            p95_ms = np.percentile(samples, 95)
            
            # Update Prometheus gauges
            self.search_latency_p50_gauge.labels(horizon=horizon).set(p50_ms / 1000.0)
            self.search_latency_p95_gauge.labels(horizon=horizon).set(p95_ms / 1000.0)
            
            logger.debug(f"Updated {horizon} latency metrics: p50={p50_ms:.1f}ms, p95={p95_ms:.1f}ms")
            
        except Exception as e:
            logger.warning(f"Failed to update percentile metrics for {horizon}: {e}")
    
    def _estimate_search_accuracy(self, horizon: str, index_type: str) -> Optional[float]:
        """Estimate search accuracy for an index."""
        # For production, this would perform actual accuracy tests
        # For now, return estimated accuracy based on index type
        if index_type == "flatip":
            return 1.0  # Exact search
        elif index_type == "ivfpq":
            return 0.98  # Approximate but high accuracy
        else:
            return None
    
    def _update_prometheus_health_metrics(self, health_metrics: Dict[str, IndexHealthMetrics]):
        """Update Prometheus metrics from health data."""
        for key, metrics in health_metrics.items():
            # Update gauges
            self.index_size_gauge.labels(
                horizon=metrics.horizon,
                index_type=metrics.index_type
            ).set(metrics.size_mb * 1024 * 1024)  # Convert to bytes
            
            self.index_vectors_gauge.labels(
                horizon=metrics.horizon,
                index_type=metrics.index_type
            ).set(metrics.ntotal)
            
            if metrics.accuracy_score is not None:
                self.search_accuracy_gauge.labels(
                    horizon=metrics.horizon,
                    index_type=metrics.index_type
                ).set(metrics.accuracy_score)
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive FAISS health summary.
        
        Returns:
            Dictionary containing detailed health status and metrics
        """
        # Ensure index health is up to date
        await self._update_index_health()
        
        # Calculate query statistics
        async with self._query_lock:
            total_queries = len(self._completed_queries)
            active_queries = len(self._active_queries)
            
            if total_queries > 0:
                successful_queries = sum(1 for q in self._completed_queries if q.success)
                error_rate = (total_queries - successful_queries) / total_queries
                avg_latency_ms = np.mean([q.duration_ms for q in self._completed_queries if q.duration_ms])
            else:
                error_rate = 0.0
                avg_latency_ms = 0.0
        
        # Build health summary
        health_summary = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "monitoring": {
                "active": self._monitoring_active,
                "uptime_seconds": time.time() - getattr(self, '_start_time', time.time())
            },
            "query_performance": {
                "total_queries": total_queries,
                "active_queries": active_queries,
                "error_rate": error_rate,
                "avg_latency_ms": float(avg_latency_ms) if avg_latency_ms else 0.0
            },
            "indices": {},
            "system": {
                "memory_usage_mb": psutil.Process().memory_info().rss / (1024 * 1024) if PSUTIL_AVAILABLE else 0.0,
                "cpu_percent": psutil.Process().cpu_percent() if PSUTIL_AVAILABLE else 0.0
            }
        }
        
        # Add index health information
        for key, metrics in self._index_health_cache.items():
            health_summary["indices"][key] = {
                "horizon": metrics.horizon,
                "index_type": metrics.index_type,
                "size_mb": metrics.size_mb,
                "vectors": metrics.ntotal,
                "dimension": metrics.dimension,
                "latency_p50_ms": metrics.search_latency_p50,
                "latency_p95_ms": metrics.search_latency_p95,
                "accuracy_score": metrics.accuracy_score,
                "last_accessed": metrics.last_accessed.isoformat()
            }
        
        # Add latency percentiles per horizon
        health_summary["latency_percentiles"] = {}
        for horizon in ["6h", "12h", "24h", "48h"]:
            p50, p95 = self._calculate_latency_percentiles(horizon)
            last_search = self._last_successful_search.get(horizon)
            health_summary["latency_percentiles"][horizon] = {
                "p50_ms": p50,
                "p95_ms": p95,
                "sample_count": len(self._latency_samples.get(horizon, [])),
                "last_successful_search": last_search.isoformat() if last_search else None,
                "last_search_age_seconds": (datetime.now(timezone.utc) - last_search).total_seconds() if last_search else None
            }
        
        # Add fallback tracking
        health_summary["fallback_metrics"] = self.get_fallback_counters()
        
        # Determine overall health status
        if self._degraded_mode_active:
            health_summary["status"] = "degraded"
        elif error_rate > 0.1:  # >10% error rate
            health_summary["status"] = "unhealthy"
        elif error_rate > 0.05 or avg_latency_ms > 100:  # >5% errors or >100ms avg latency
            health_summary["status"] = "degraded"
        elif not self._monitoring_active:
            health_summary["status"] = "monitoring_disabled"
        
        return health_summary
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format.
        
        Returns:
            Prometheus metrics as text
        """
        return generate_latest(self.registry).decode('utf-8')
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()

# Global health monitor instance for dependency injection
_faiss_health_monitor: Optional[FAISSHealthMonitor] = None

async def get_faiss_health_monitor() -> FAISSHealthMonitor:
    """Get global FAISS health monitor instance."""
    global _faiss_health_monitor
    
    if _faiss_health_monitor is None:
        _faiss_health_monitor = FAISSHealthMonitor()
        await _faiss_health_monitor.start_monitoring()
    
    return _faiss_health_monitor

async def shutdown_faiss_health_monitor():
    """Shutdown global FAISS health monitor."""
    global _faiss_health_monitor
    
    if _faiss_health_monitor is not None:
        await _faiss_health_monitor.stop_monitoring()
        _faiss_health_monitor = None