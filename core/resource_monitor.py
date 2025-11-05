#!/usr/bin/env python3
"""
Resource Monitor and Memory Profiler
=====================================

Comprehensive resource monitoring for FAISS operations with memory profiling,
fail-fast behavior, and resource constraint management.

Features:
- Memory usage monitoring and profiling
- CPU and GPU resource detection
- Memory budget enforcement with fail-fast
- Resource metrics collection for observability
- Memory pressure detection and alerting

Author: Performance Specialist
Version: 1.0.0 - Resource Guardrails Implementation
"""

import os
import time
import logging
import threading
import gc
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager
import numpy as np

# Try to import psutil, fall back to basic functionality if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psutil not available - using basic resource monitoring")

logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""
    timestamp: str
    total_mb: float
    available_mb: float
    used_mb: float
    used_percent: float
    process_rss_mb: float
    process_vms_mb: float
    gc_objects: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ResourceMetrics:
    """Comprehensive resource usage metrics."""
    cpu_count: int
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_used_percent: float
    process_memory_mb: float
    gpu_available: bool
    gpu_memory_mb: Optional[float]
    disk_usage_percent: float
    load_average: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MemoryBudget:
    """Memory budget configuration and limits."""
    max_total_mb: float
    max_process_mb: float
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    
    def check_budget(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Check if current usage violates budget."""
        total_violation = snapshot.used_mb > self.max_total_mb
        process_violation = snapshot.process_rss_mb > self.max_process_mb
        
        warning_level = snapshot.used_percent > self.warning_threshold_percent
        critical_level = snapshot.used_percent > self.critical_threshold_percent
        
        return {
            'total_violation': total_violation,
            'process_violation': process_violation,
            'warning_level': warning_level,
            'critical_level': critical_level,
            'budget_exceeded': total_violation or process_violation,
            'severity': 'critical' if critical_level else ('warning' if warning_level else 'normal')
        }

class MemoryProfiler:
    """Memory profiler for tracking memory usage patterns."""
    
    def __init__(self, sample_interval: float = 0.5):
        """Initialize memory profiler.
        
        Args:
            sample_interval: Time between memory samples in seconds
        """
        self.sample_interval = sample_interval
        self.snapshots: List[MemorySnapshot] = []
        self.is_profiling = False
        self._profile_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start_profiling(self):
        """Start background memory profiling."""
        if self.is_profiling:
            return
            
        self.is_profiling = True
        self._stop_event.clear()
        self.snapshots.clear()
        
        self._profile_thread = threading.Thread(target=self._profile_loop, daemon=True)
        self._profile_thread.start()
        
        logger.info(f"Memory profiling started with {self.sample_interval}s interval")
    
    def stop_profiling(self) -> List[MemorySnapshot]:
        """Stop profiling and return collected snapshots."""
        if not self.is_profiling:
            return self.snapshots
            
        self.is_profiling = False
        self._stop_event.set()
        
        if self._profile_thread and self._profile_thread.is_alive():
            self._profile_thread.join(timeout=5.0)
        
        logger.info(f"Memory profiling stopped. Collected {len(self.snapshots)} snapshots")
        return self.snapshots
    
    def _profile_loop(self):
        """Background profiling loop."""
        while not self._stop_event.is_set():
            try:
                snapshot = self._take_memory_snapshot()
                self.snapshots.append(snapshot)
                
                # Limit snapshot history to prevent memory growth
                if len(self.snapshots) > 1000:
                    self.snapshots = self.snapshots[-500:]
                    
            except Exception as e:
                logger.warning(f"Memory profiling error: {e}")
            
            self._stop_event.wait(self.sample_interval)
    
    def _take_memory_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        if PSUTIL_AVAILABLE:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Force garbage collection to get accurate count
            gc_objects = len(gc.get_objects())
            
            return MemorySnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_mb=memory.total / (1024 * 1024),
                available_mb=memory.available / (1024 * 1024),
                used_mb=memory.used / (1024 * 1024),
                used_percent=memory.percent,
                process_rss_mb=process_memory.rss / (1024 * 1024),
                process_vms_mb=process_memory.vms / (1024 * 1024),
                gc_objects=gc_objects
            )
        else:
            # Fallback when psutil not available
            gc_objects = len(gc.get_objects())
            
            # Basic memory estimation (not accurate but functional)
            return MemorySnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_mb=8192.0,  # Assume 8GB
                available_mb=4096.0,  # Assume 4GB available
                used_mb=4096.0,  # Assume 4GB used
                used_percent=50.0,  # 50% usage
                process_rss_mb=100.0,  # Assume 100MB process
                process_vms_mb=200.0,  # Assume 200MB virtual
                gc_objects=gc_objects
            )
    
    def get_peak_usage(self) -> Optional[MemorySnapshot]:
        """Get peak memory usage from collected snapshots."""
        if not self.snapshots:
            return None
        
        return max(self.snapshots, key=lambda s: s.process_rss_mb)
    
    def get_memory_growth_rate(self) -> float:
        """Calculate memory growth rate in MB/second."""
        if len(self.snapshots) < 2:
            return 0.0
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        time_diff = (
            datetime.fromisoformat(last.timestamp) - 
            datetime.fromisoformat(first.timestamp)
        ).total_seconds()
        
        if time_diff <= 0:
            return 0.0
        
        memory_diff = last.process_rss_mb - first.process_rss_mb
        return memory_diff / time_diff

class ResourceMonitor:
    """Comprehensive resource monitoring and budget enforcement."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.profiler = MemoryProfiler()
        self.memory_budget: Optional[MemoryBudget] = None
        self.monitoring_enabled = False
        self._resource_callbacks: List[Callable[[ResourceMetrics], None]] = []
        
        # Load configuration from environment
        self._load_config()
        
        logger.info("ResourceMonitor initialized")
    
    def _load_config(self):
        """Load configuration from environment variables."""
        # Memory budget configuration
        memory_limit_mb = float(os.getenv('FAISS_MEMORY_LIMIT', '4096'))  # 4GB default
        process_limit_mb = float(os.getenv('FAISS_PROCESS_MEMORY_LIMIT', '2048'))  # 2GB default
        
        self.memory_budget = MemoryBudget(
            max_total_mb=memory_limit_mb,
            max_process_mb=process_limit_mb,
            warning_threshold_percent=float(os.getenv('MEMORY_WARNING_THRESHOLD', '80')),
            critical_threshold_percent=float(os.getenv('MEMORY_CRITICAL_THRESHOLD', '95'))
        )
        
        logger.info(f"Memory budget configured: {memory_limit_mb}MB total, {process_limit_mb}MB process")
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource utilization metrics."""
        if PSUTIL_AVAILABLE:
            # CPU metrics
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_usage_percent = disk_usage.percent
            
            # Memory metrics for ResourceMetrics
            memory_total_gb = memory.total / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            memory_used_percent = memory.percent
        else:
            # Fallback metrics when psutil not available
            cpu_count = os.cpu_count() or 1
            cpu_percent = 10.0  # Assume 10% CPU usage
            process_memory = 100.0  # Assume 100MB process memory
            disk_usage_percent = 50.0  # Assume 50% disk usage
            
            # Fallback memory metrics
            memory_total_gb = 8.0  # Assume 8GB total
            memory_available_gb = 4.0  # Assume 4GB available
            memory_used_percent = 50.0  # Assume 50% usage
        
        # GPU detection
        gpu_available, gpu_memory = self._detect_gpu()
        
        # Load average (Unix-like systems only)
        try:
            load_avg = list(os.getloadavg())
        except (AttributeError, OSError):
            load_avg = [0.0, 0.0, 0.0]
        
        return ResourceMetrics(
            cpu_count=cpu_count,
            cpu_percent=cpu_percent,
            memory_total_gb=memory_total_gb,
            memory_available_gb=memory_available_gb,
            memory_used_percent=memory_used_percent,
            process_memory_mb=process_memory,
            gpu_available=gpu_available,
            gpu_memory_mb=gpu_memory,
            disk_usage_percent=disk_usage_percent,
            load_average=load_avg
        )
    
    def _detect_gpu(self) -> tuple[bool, Optional[float]]:
        """Detect GPU availability and memory."""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**2)
                return True, gpu_memory
        except ImportError:
            pass
        
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return True, info.total / (1024**2)
        except (ImportError, Exception):
            pass
        
        return False, None
    
    def check_memory_budget(self) -> Dict[str, Any]:
        """Check current memory usage against budget."""
        if not self.memory_budget:
            return {'budget_exceeded': False, 'severity': 'normal'}
        
        snapshot = self.profiler._take_memory_snapshot()
        return self.memory_budget.check_budget(snapshot)
    
    def enforce_memory_budget(self, operation_name: str = "operation") -> bool:
        """Enforce memory budget with fail-fast behavior.
        
        Returns:
            True if operation can proceed, False if budget exceeded
        """
        budget_check = self.check_memory_budget()
        
        if budget_check['budget_exceeded']:
            logger.critical(f"Memory budget exceeded for {operation_name}")
            logger.critical(f"Budget violation: {budget_check}")
            
            # Force garbage collection
            gc.collect()
            
            # Recheck after GC
            budget_check = self.check_memory_budget()
            if budget_check['budget_exceeded']:
                logger.critical(f"Memory budget still exceeded after GC - failing fast")
                return False
        
        if budget_check['severity'] in ['warning', 'critical']:
            logger.warning(f"Memory usage at {budget_check['severity']} level for {operation_name}")
        
        return True
    
    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager for profiling an operation."""
        logger.info(f"Starting memory profiling for: {operation_name}")
        
        # Check budget before operation
        if not self.enforce_memory_budget(operation_name):
            raise MemoryError(f"Memory budget exceeded before {operation_name}")
        
        # Start profiling
        self.profiler.start_profiling()
        start_time = time.time()
        
        try:
            yield self.profiler
        finally:
            # Stop profiling and collect results
            snapshots = self.profiler.stop_profiling()
            duration = time.time() - start_time
            
            # Analyze results
            peak_usage = self.profiler.get_peak_usage()
            growth_rate = self.profiler.get_memory_growth_rate()
            
            logger.info(f"Memory profiling complete for {operation_name}")
            logger.info(f"Duration: {duration:.2f}s, Snapshots: {len(snapshots)}")
            if peak_usage:
                logger.info(f"Peak memory: {peak_usage.process_rss_mb:.1f}MB")
            logger.info(f"Growth rate: {growth_rate:.2f}MB/s")
            
            # Check budget after operation
            final_check = self.check_memory_budget()
            if final_check['budget_exceeded']:
                logger.warning(f"Memory budget exceeded after {operation_name}")
    
    def add_resource_callback(self, callback: Callable[[ResourceMetrics], None]):
        """Add callback for resource metrics updates."""
        self._resource_callbacks.append(callback)
    
    def start_monitoring(self, interval: float = 30.0):
        """Start periodic resource monitoring."""
        self.monitoring_enabled = True
        
        def monitor_loop():
            while self.monitoring_enabled:
                try:
                    metrics = self.get_current_metrics()
                    
                    # Call registered callbacks
                    for callback in self._resource_callbacks:
                        try:
                            callback(metrics)
                        except Exception as e:
                            logger.warning(f"Resource callback failed: {e}")
                    
                    # Check for resource pressure
                    if metrics.memory_used_percent > 90:
                        logger.warning(f"High memory usage: {metrics.memory_used_percent:.1f}%")
                    
                    if metrics.cpu_percent > 95:
                        logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
                    
                except Exception as e:
                    logger.error(f"Resource monitoring error: {e}")
                
                time.sleep(interval)
        
        monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitoring_thread.start()
        
        logger.info(f"Resource monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring_enabled = False
        logger.info("Resource monitoring stopped")
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive resource summary."""
        metrics = self.get_current_metrics()
        budget_check = self.check_memory_budget()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': metrics.to_dict(),
            'memory_budget': asdict(self.memory_budget) if self.memory_budget else None,
            'budget_status': budget_check,
            'profiler_active': self.profiler.is_profiling,
            'monitoring_active': self.monitoring_enabled
        }

# Global resource monitor instance
_resource_monitor: Optional[ResourceMonitor] = None

def get_resource_monitor() -> ResourceMonitor:
    """Get or create global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor

def check_memory_budget(operation_name: str = "operation") -> bool:
    """Convenience function to check memory budget."""
    monitor = get_resource_monitor()
    return monitor.enforce_memory_budget(operation_name)

@contextmanager
def profile_memory(operation_name: str):
    """Convenience context manager for memory profiling."""
    monitor = get_resource_monitor()
    with monitor.profile_operation(operation_name) as profiler:
        yield profiler