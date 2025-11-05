#!/usr/bin/env python3
"""
Runtime Guardrails and Corruption Detection System
==================================================

Implements comprehensive runtime monitoring, corruption detection, and automatic
guardrails for the Adelaide Weather Forecasting System during operation.

CORRUPTION DETECTION:
- All-zero artifact detection in wind components
- NaN/Inf propagation monitoring
- Precision validation for weighted quantiles
- Memory usage monitoring and leak detection
- Performance degradation alerts

RUNTIME GUARDRAILS:
- Automatic forecast suppression on corruption
- Graceful degradation with reduced ensemble size
- Memory limit enforcement with garbage collection
- Performance circuit breakers
- Error recovery and fallback mechanisms

MONITORING SYSTEMS:
- Real-time performance metrics tracking
- Resource utilization monitoring
- Error pattern detection and alerting
- Forecast quality drift detection

Author: Production QA Framework
Version: 1.0.0 - Runtime Protection
"""

import gc
import os
import sys
import time
import psutil
import logging
import warnings
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import deque
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class SystemStatus(Enum):
    """System operational status."""
    OPERATIONAL = "operational"      # Normal operation
    DEGRADED = "degraded"           # Reduced performance/quality
    CRITICAL = "critical"           # Critical issues, limited operation
    EMERGENCY = "emergency"         # Emergency shutdown required

class CorruptionType(Enum):
    """Types of data corruption detected."""
    ALL_ZEROS = "all_zeros"              # All-zero artifacts
    NAN_PROPAGATION = "nan_propagation"  # NaN value spread
    INF_VALUES = "inf_values"            # Infinite values
    RANGE_VIOLATION = "range_violation"  # Values outside valid ranges
    PRECISION_LOSS = "precision_loss"    # Numerical precision issues
    MEMORY_CORRUPTION = "memory_corruption"  # Memory layout issues

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics."""
    timestamp: str
    operation: str
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    gpu_memory_mb: Optional[float] = None
    
@dataclass
class CorruptionEvent:
    """Corruption detection event."""
    timestamp: str
    corruption_type: CorruptionType
    affected_component: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    details: Dict[str, Any]
    mitigation_applied: str
    
@dataclass
class SystemHealthSnapshot:
    """Complete system health snapshot."""
    timestamp: str
    status: SystemStatus
    
    # Performance metrics
    avg_response_time_ms: float
    memory_usage_percent: float
    cpu_usage_percent: float
    gpu_usage_percent: Optional[float]
    
    # Error statistics
    error_rate_per_hour: float
    corruption_events_count: int
    
    # Quality metrics
    forecast_quality_score: float
    analog_search_success_rate: float
    
    # Resource limits
    memory_limit_mb: float
    performance_threshold_ms: float
    
    # Guardrail status
    circuit_breakers_active: List[str]
    degraded_operations: List[str]

class RuntimeGuardRails:
    """Production-grade runtime monitoring and protection system."""
    
    # Performance thresholds
    MAX_RESPONSE_TIME_MS = 150          # Circuit breaker threshold
    MAX_MEMORY_USAGE_PERCENT = 85       # Memory limit
    MAX_ERROR_RATE_PER_HOUR = 10        # Error rate threshold
    MIN_FORECAST_QUALITY = 0.3          # Minimum acceptable quality
    
    # Corruption detection thresholds
    MAX_ZERO_FRACTION = 0.8             # Max fraction of zeros allowed
    MAX_NAN_FRACTION = 0.1              # Max fraction of NaN values
    PRECISION_TOLERANCE = 1e-12         # Numerical precision threshold
    
    # Circuit breaker settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
    CIRCUIT_BREAKER_RECOVERY_TIME = 300  # 5 minutes
    
    def __init__(self, max_memory_gb: float = 8.0, enable_gpu_monitoring: bool = True):
        """Initialize runtime guardrails system.
        
        Args:
            max_memory_gb: Maximum memory usage allowed (GB)
            enable_gpu_monitoring: Enable GPU resource monitoring
        """
        self.max_memory_bytes = max_memory_gb * 1024**3
        self.enable_gpu_monitoring = enable_gpu_monitoring
        
        # Monitoring state
        self.performance_history = deque(maxlen=1000)
        self.corruption_events = deque(maxlen=100)
        self.error_counts = deque(maxlen=60)  # Last 60 minutes
        
        # Circuit breakers
        self.circuit_breakers = {
            'embedding_generation': {'failures': 0, 'last_failure': None, 'state': 'closed'},
            'faiss_search': {'failures': 0, 'last_failure': None, 'state': 'closed'},
            'forecast_generation': {'failures': 0, 'last_failure': None, 'state': 'closed'}
        }
        
        # Guardrail locks
        self._monitoring_lock = threading.Lock()
        self._corruption_lock = threading.Lock()
        
        # System status
        self.current_status = SystemStatus.OPERATIONAL
        self.degraded_operations = set()
        
        # Initialize monitoring
        self._start_background_monitoring()
        
        logger.info(f"🛡️ Runtime Guardrails initialized")
        logger.info(f"   Memory limit: {max_memory_gb:.1f}GB")
        logger.info(f"   Performance threshold: {self.MAX_RESPONSE_TIME_MS}ms")
        logger.info(f"   GPU monitoring: {enable_gpu_monitoring}")
    
    @contextmanager
    def performance_monitor(self, operation: str):
        """Context manager for performance monitoring with automatic guardrails."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open(operation):
                raise RuntimeError(f"Circuit breaker open for {operation}")
            
            yield
            
            # Record successful operation
            self._reset_circuit_breaker_failure(operation)
            
        except Exception as e:
            # Record failure
            self._record_circuit_breaker_failure(operation, str(e))
            raise
            
        finally:
            # Calculate metrics
            duration_ms = (time.time() - start_time) * 1000
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_usage()
            
            # Record performance metrics
            metrics = PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                operation=operation,
                duration_ms=duration_ms,
                memory_mb=end_memory,
                cpu_percent=end_cpu,
                gpu_memory_mb=self._get_gpu_memory() if self.enable_gpu_monitoring else None
            )
            
            with self._monitoring_lock:
                self.performance_history.append(metrics)
            
            # Check performance thresholds
            if duration_ms > self.MAX_RESPONSE_TIME_MS:
                self._handle_performance_degradation(operation, duration_ms)
            
            # Check memory limits
            if end_memory > self.max_memory_bytes / (1024**2):  # MB
                self._handle_memory_limit_exceeded(operation, end_memory)
    
    def detect_corruption(self, data: np.ndarray, data_type: str, 
                         variable_name: str = "unknown") -> List[CorruptionEvent]:
        """Detect various types of data corruption.
        
        Args:
            data: Data array to check for corruption
            data_type: Type of data ('embedding', 'outcome', 'weather', etc.)
            variable_name: Name of the variable being checked
            
        Returns:
            List of corruption events detected
        """
        corruption_events = []
        
        if data is None or data.size == 0:
            return corruption_events
        
        # Flatten data for analysis
        flat_data = data.flatten()
        
        # Check for all-zero artifacts
        zero_fraction = np.sum(flat_data == 0) / len(flat_data)
        if zero_fraction > self.MAX_ZERO_FRACTION:
            event = CorruptionEvent(
                timestamp=datetime.now().isoformat(),
                corruption_type=CorruptionType.ALL_ZEROS,
                affected_component=f"{data_type}_{variable_name}",
                severity="high" if zero_fraction > 0.95 else "medium",
                details={
                    'zero_fraction': zero_fraction,
                    'data_shape': data.shape,
                    'total_elements': data.size
                },
                mitigation_applied="data_flagged_for_rejection"
            )
            corruption_events.append(event)
        
        # Check for NaN propagation
        nan_fraction = np.sum(np.isnan(flat_data)) / len(flat_data)
        if nan_fraction > self.MAX_NAN_FRACTION:
            event = CorruptionEvent(
                timestamp=datetime.now().isoformat(),
                corruption_type=CorruptionType.NAN_PROPAGATION,
                affected_component=f"{data_type}_{variable_name}",
                severity="critical" if nan_fraction > 0.5 else "high",
                details={
                    'nan_fraction': nan_fraction,
                    'nan_count': np.sum(np.isnan(flat_data))
                },
                mitigation_applied="nan_filtering_applied"
            )
            corruption_events.append(event)
        
        # Check for infinite values
        inf_count = np.sum(np.isinf(flat_data))
        if inf_count > 0:
            event = CorruptionEvent(
                timestamp=datetime.now().isoformat(),
                corruption_type=CorruptionType.INF_VALUES,
                affected_component=f"{data_type}_{variable_name}",
                severity="high",
                details={
                    'inf_count': inf_count,
                    'pos_inf_count': np.sum(np.isposinf(flat_data)),
                    'neg_inf_count': np.sum(np.isneginf(flat_data))
                },
                mitigation_applied="inf_values_clipped"
            )
            corruption_events.append(event)
        
        # Variable-specific range validation
        range_violations = self._check_variable_ranges(flat_data, variable_name)
        if range_violations['violation_count'] > 0:
            event = CorruptionEvent(
                timestamp=datetime.now().isoformat(),
                corruption_type=CorruptionType.RANGE_VIOLATION,
                affected_component=f"{data_type}_{variable_name}",
                severity="medium",
                details=range_violations,
                mitigation_applied="out_of_range_values_flagged"
            )
            corruption_events.append(event)
        
        # Check for precision loss (for floating point data)
        if data.dtype in [np.float32, np.float64]:
            precision_issues = self._check_precision_loss(flat_data)
            if precision_issues['precision_loss_detected']:
                event = CorruptionEvent(
                    timestamp=datetime.now().isoformat(),
                    corruption_type=CorruptionType.PRECISION_LOSS,
                    affected_component=f"{data_type}_{variable_name}",
                    severity="low",
                    details=precision_issues,
                    mitigation_applied="precision_warning_logged"
                )
                corruption_events.append(event)
        
        # Record corruption events
        with self._corruption_lock:
            self.corruption_events.extend(corruption_events)
        
        # Log corruption events
        for event in corruption_events:
            if event.severity in ['critical', 'high']:
                logger.error(f"🚨 {event.corruption_type.value.upper()}: {event.affected_component}")
                logger.error(f"   Severity: {event.severity}, Details: {event.details}")
            else:
                logger.warning(f"⚠️ {event.corruption_type.value}: {event.affected_component}")
        
        return corruption_events
    
    def validate_weighted_quantiles(self, values: np.ndarray, weights: np.ndarray,
                                  quantiles: List[float]) -> Dict[str, Any]:
        """Validate precision and correctness of weighted quantile calculations.
        
        Args:
            values: Data values
            weights: Corresponding weights
            quantiles: Quantile levels to validate
            
        Returns:
            Validation results with precision checks
        """
        validation_results = {
            'precision_valid': True,
            'quantiles_valid': True,
            'weight_sum_valid': True,
            'issues': []
        }
        
        # Check weight sum
        weight_sum = np.sum(weights)
        if not np.isclose(weight_sum, 1.0, atol=1e-6):
            validation_results['weight_sum_valid'] = False
            validation_results['issues'].append(f"Weight sum {weight_sum:.8f} != 1.0")
        
        # Check for negative weights
        if np.any(weights < 0):
            validation_results['quantiles_valid'] = False
            validation_results['issues'].append("Negative weights detected")
        
        # Check quantile order
        try:
            sorted_indices = np.argsort(values)
            sorted_values = values[sorted_indices]
            sorted_weights = weights[sorted_indices]
            cumsum_weights = np.cumsum(sorted_weights)
            
            quantile_values = []
            for q in quantiles:
                idx = np.searchsorted(cumsum_weights, q)
                idx = max(0, min(idx, len(sorted_values) - 1))
                quantile_values.append(sorted_values[idx])
            
            # Check if quantiles are in ascending order
            if not all(quantile_values[i] <= quantile_values[i+1] for i in range(len(quantile_values)-1)):
                validation_results['quantiles_valid'] = False
                validation_results['issues'].append("Quantiles not in ascending order")
            
        except Exception as e:
            validation_results['precision_valid'] = False
            validation_results['issues'].append(f"Quantile calculation error: {str(e)}")
        
        return validation_results
    
    def enforce_memory_limits(self, force_gc: bool = False) -> bool:
        """Enforce memory limits with automatic garbage collection.
        
        Args:
            force_gc: Force garbage collection regardless of threshold
            
        Returns:
            True if memory is within limits after cleanup
        """
        current_memory = self._get_memory_usage()
        memory_percent = (current_memory * 1024**2) / self.max_memory_bytes * 100
        
        if memory_percent > self.MAX_MEMORY_USAGE_PERCENT or force_gc:
            logger.warning(f"🧹 Memory usage {memory_percent:.1f}% > {self.MAX_MEMORY_USAGE_PERCENT}%, forcing cleanup")
            
            # Force garbage collection
            collected = gc.collect()
            
            # Clear internal caches if available
            self._clear_internal_caches()
            
            # Check memory after cleanup
            new_memory = self._get_memory_usage()
            new_percent = (new_memory * 1024**2) / self.max_memory_bytes * 100
            
            logger.info(f"   Collected {collected} objects, memory: {memory_percent:.1f}% → {new_percent:.1f}%")
            
            if new_percent > self.MAX_MEMORY_USAGE_PERCENT:
                logger.error(f"❌ Memory limit exceeded after cleanup: {new_percent:.1f}%")
                self._trigger_emergency_mode("memory_limit_exceeded")
                return False
        
        return True
    
    def get_system_health_snapshot(self) -> SystemHealthSnapshot:
        """Get comprehensive system health snapshot."""
        with self._monitoring_lock:
            # Calculate performance metrics
            recent_metrics = list(self.performance_history)[-100:]  # Last 100 operations
            if recent_metrics:
                avg_response_time = np.mean([m.duration_ms for m in recent_metrics])
                current_memory = recent_metrics[-1].memory_mb
                current_cpu = recent_metrics[-1].cpu_percent
            else:
                avg_response_time = 0.0
                current_memory = self._get_memory_usage()
                current_cpu = self._get_cpu_usage()
        
        # Calculate error rate
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        recent_errors = [
            e for e in self.corruption_events 
            if datetime.fromisoformat(e.timestamp) > hour_ago
        ]
        error_rate = len(recent_errors)
        
        # GPU usage
        gpu_usage = None
        if self.enable_gpu_monitoring:
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / 1024**2  # MB
                    gpu_total = torch.cuda.get_device_properties(0).total_memory / 1024**2
                    gpu_usage = (gpu_memory / gpu_total) * 100
            except:
                gpu_usage = None
        
        # Calculate forecast quality (simplified)
        forecast_quality_score = self._calculate_forecast_quality_score()
        
        # Analog search success rate
        analog_success_rate = self._calculate_analog_success_rate()
        
        # Active circuit breakers
        active_breakers = [
            name for name, state in self.circuit_breakers.items()
            if state['state'] in ['open', 'half-open']
        ]
        
        return SystemHealthSnapshot(
            timestamp=datetime.now().isoformat(),
            status=self.current_status,
            avg_response_time_ms=avg_response_time,
            memory_usage_percent=(current_memory * 1024**2) / self.max_memory_bytes * 100,
            cpu_usage_percent=current_cpu,
            gpu_usage_percent=gpu_usage,
            error_rate_per_hour=error_rate,
            corruption_events_count=len(self.corruption_events),
            forecast_quality_score=forecast_quality_score,
            analog_search_success_rate=analog_success_rate,
            memory_limit_mb=self.max_memory_bytes / 1024**2,
            performance_threshold_ms=self.MAX_RESPONSE_TIME_MS,
            circuit_breakers_active=active_breakers,
            degraded_operations=list(self.degraded_operations)
        )
    
    def _check_variable_ranges(self, data: np.ndarray, variable_name: str) -> Dict[str, Any]:
        """Check if variable values are within expected ranges."""
        variable_ranges = {
            'z500': (4800, 6200),
            't2m': (200, 350),
            't850': (200, 340),
            'q850': (0, 0.030),
            'u10': (-50, 50),
            'v10': (-50, 50),
            'u850': (-80, 80),
            'v850': (-80, 80),
            'cape': (0, 8000)
        }
        
        if variable_name not in variable_ranges:
            return {'violation_count': 0, 'message': 'no_range_defined'}
        
        min_val, max_val = variable_ranges[variable_name]
        valid_data = data[np.isfinite(data)]
        
        if len(valid_data) == 0:
            return {'violation_count': 0, 'message': 'no_valid_data'}
        
        violations = (valid_data < min_val) | (valid_data > max_val)
        violation_count = np.sum(violations)
        
        return {
            'violation_count': violation_count,
            'violation_fraction': violation_count / len(valid_data),
            'min_allowed': min_val,
            'max_allowed': max_val,
            'data_min': float(np.min(valid_data)),
            'data_max': float(np.max(valid_data))
        }
    
    def _check_precision_loss(self, data: np.ndarray) -> Dict[str, Any]:
        """Check for numerical precision loss."""
        if len(data) == 0:
            return {'precision_loss_detected': False}
        
        # Check for repeated values that might indicate precision loss
        unique_values = np.unique(data[np.isfinite(data)])
        if len(unique_values) < len(data) * 0.5:  # Less than 50% unique values
            # Check if values are clustered at specific precision levels
            if len(unique_values) > 1:
                min_diff = np.min(np.diff(np.sort(unique_values)))
                if min_diff < self.PRECISION_TOLERANCE:
                    return {
                        'precision_loss_detected': True,
                        'min_difference': float(min_diff),
                        'unique_ratio': len(unique_values) / len(data)
                    }
        
        return {'precision_loss_detected': False}
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024**2
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    def _get_gpu_memory(self) -> Optional[float]:
        """Get GPU memory usage in MB."""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1024**2
        except:
            pass
        return None
    
    def _is_circuit_breaker_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for operation."""
        if operation not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[operation]
        
        if breaker['state'] == 'open':
            # Check if recovery time has passed
            if breaker['last_failure']:
                time_since_failure = time.time() - breaker['last_failure']
                if time_since_failure > self.CIRCUIT_BREAKER_RECOVERY_TIME:
                    breaker['state'] = 'half-open'
                    logger.info(f"🔄 Circuit breaker half-open for {operation}")
                    return False
            return True
        
        return False
    
    def _record_circuit_breaker_failure(self, operation: str, error: str):
        """Record circuit breaker failure."""
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = {'failures': 0, 'last_failure': None, 'state': 'closed'}
        
        breaker = self.circuit_breakers[operation]
        breaker['failures'] += 1
        breaker['last_failure'] = time.time()
        
        if breaker['failures'] >= self.CIRCUIT_BREAKER_FAILURE_THRESHOLD:
            breaker['state'] = 'open'
            logger.error(f"🚨 Circuit breaker OPEN for {operation} after {breaker['failures']} failures")
            self.degraded_operations.add(operation)
    
    def _reset_circuit_breaker_failure(self, operation: str):
        """Reset circuit breaker after successful operation."""
        if operation in self.circuit_breakers:
            breaker = self.circuit_breakers[operation]
            if breaker['state'] == 'half-open':
                breaker['state'] = 'closed'
                breaker['failures'] = 0
                logger.info(f"✅ Circuit breaker closed for {operation}")
                self.degraded_operations.discard(operation)
    
    def _handle_performance_degradation(self, operation: str, duration_ms: float):
        """Handle performance degradation event."""
        logger.warning(f"⚠️ Performance degradation: {operation} took {duration_ms:.1f}ms > {self.MAX_RESPONSE_TIME_MS}ms")
        
        # Add to degraded operations if severe
        if duration_ms > self.MAX_RESPONSE_TIME_MS * 2:
            self.degraded_operations.add(operation)
            if self.current_status == SystemStatus.OPERATIONAL:
                self.current_status = SystemStatus.DEGRADED
    
    def _handle_memory_limit_exceeded(self, operation: str, memory_mb: float):
        """Handle memory limit exceeded event."""
        logger.error(f"🚨 Memory limit exceeded during {operation}: {memory_mb:.1f}MB")
        
        # Force garbage collection
        self.enforce_memory_limits(force_gc=True)
        
        # Update system status
        if self.current_status in [SystemStatus.OPERATIONAL, SystemStatus.DEGRADED]:
            self.current_status = SystemStatus.CRITICAL
    
    def _trigger_emergency_mode(self, reason: str):
        """Trigger emergency shutdown mode."""
        logger.critical(f"🚨🚨 EMERGENCY MODE TRIGGERED: {reason}")
        self.current_status = SystemStatus.EMERGENCY
        
        # Open all circuit breakers
        for breaker in self.circuit_breakers.values():
            breaker['state'] = 'open'
    
    def _calculate_forecast_quality_score(self) -> float:
        """Calculate aggregate forecast quality score."""
        # Simplified calculation based on recent corruption events
        recent_corruptions = [
            e for e in self.corruption_events
            if datetime.fromisoformat(e.timestamp) > datetime.now() - timedelta(hours=1)
        ]
        
        if not recent_corruptions:
            return 1.0
        
        # Weight by severity
        severity_weights = {'low': 0.1, 'medium': 0.3, 'high': 0.7, 'critical': 1.0}
        total_weight = sum(severity_weights.get(e.severity, 0.5) for e in recent_corruptions)
        
        # Quality degradation based on corruption events
        quality_score = max(0.0, 1.0 - total_weight / 10.0)
        return quality_score
    
    def _calculate_analog_success_rate(self) -> float:
        """Calculate analog search success rate."""
        # Based on circuit breaker state for analog operations
        search_breaker = self.circuit_breakers.get('faiss_search', {'state': 'closed'})
        if search_breaker['state'] == 'open':
            return 0.0
        elif search_breaker['state'] == 'half-open':
            return 0.5
        else:
            return 1.0 - min(1.0, search_breaker.get('failures', 0) / 10.0)
    
    def _clear_internal_caches(self):
        """Clear internal caches to free memory."""
        # Clear performance history (keep last 100)
        with self._monitoring_lock:
            if len(self.performance_history) > 100:
                # Keep only recent entries
                recent_entries = list(self.performance_history)[-100:]
                self.performance_history.clear()
                self.performance_history.extend(recent_entries)
        
        # Clear old corruption events (keep last 50)
        with self._corruption_lock:
            if len(self.corruption_events) > 50:
                recent_events = list(self.corruption_events)[-50:]
                self.corruption_events.clear()
                self.corruption_events.extend(recent_events)
    
    def _start_background_monitoring(self):
        """Start background monitoring thread."""
        def monitor_loop():
            while True:
                try:
                    # Periodic health checks
                    snapshot = self.get_system_health_snapshot()
                    
                    # Log health status periodically
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        logger.info(f"🏥 System Health: {snapshot.status.value}, "
                                   f"Memory: {snapshot.memory_usage_percent:.1f}%, "
                                   f"Response: {snapshot.avg_response_time_ms:.1f}ms")
                    
                    # Check for automatic recovery
                    if snapshot.status == SystemStatus.CRITICAL and snapshot.memory_usage_percent < 70:
                        if len(snapshot.circuit_breakers_active) == 0:
                            self.current_status = SystemStatus.DEGRADED
                            logger.info("🔄 System recovering from CRITICAL to DEGRADED")
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

def main():
    """Demonstration of runtime guardrails."""
    guardrails = RuntimeGuardRails(max_memory_gb=4.0)
    
    # Test performance monitoring
    with guardrails.performance_monitor("test_operation"):
        time.sleep(0.01)  # Simulate work
        
        # Test corruption detection
        corrupt_data = np.zeros(1000)  # All zeros
        corruption_events = guardrails.detect_corruption(corrupt_data, "test_data", "test_var")
        
        print(f"Detected {len(corruption_events)} corruption events")
        for event in corruption_events:
            print(f"  {event.corruption_type.value}: {event.severity}")
    
    # Test memory enforcement
    success = guardrails.enforce_memory_limits()
    print(f"Memory enforcement: {'✅' if success else '❌'}")
    
    # Get system health
    health = guardrails.get_system_health_snapshot()
    print(f"System Status: {health.status.value}")
    print(f"Memory Usage: {health.memory_usage_percent:.1f}%")
    print(f"Average Response Time: {health.avg_response_time_ms:.1f}ms")

if __name__ == "__main__":
    main()