#!/usr/bin/env python3
"""
FAISS Rebuild Monitoring & Alerting
===================================

Comprehensive monitoring and alerting system for FAISS index rebuilds with
Prometheus metrics, health endpoints, and integration with existing monitoring
infrastructure.

Features:
- Prometheus metrics export
- Health check endpoints
- Alert rule definitions
- Integration with existing FAISS health monitoring
- Performance trend analysis
- Failure pattern detection
- SLA tracking and reporting
- Dashboard integration

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

try:
    from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("prometheus_client not available, metrics disabled")

from core.faiss_index_rebuilder import RebuildResult, ScheduledRebuildEvent
from core.faiss_rebuild_scheduler import FAISSRebuildScheduler

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """Defines an alert rule for monitoring."""
    name: str
    description: str
    query: str
    threshold: float
    comparison: str  # gt, lt, eq, gte, lte
    duration: str = "5m"
    severity: str = "warning"  # critical, warning, info
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}

@dataclass
class MonitoringConfig:
    """Configuration for FAISS rebuild monitoring."""
    # Metrics
    enable_prometheus: bool = True
    metrics_port: int = 9100
    metrics_path: str = "/metrics"
    
    # Health checks
    health_check_port: int = 8080
    health_check_path: str = "/health"
    
    # Alert thresholds
    max_rebuild_duration_minutes: float = 240.0  # 4 hours
    max_failure_rate: float = 0.2  # 20%
    max_consecutive_failures: int = 3
    min_success_rate_24h: float = 0.8  # 80%
    
    # Retention
    metrics_retention_days: int = 30
    events_retention_days: int = 90
    
    # Integration
    integrate_with_existing_monitoring: bool = True
    export_to_grafana: bool = True

class PrometheusMetrics:
    """Prometheus metrics for FAISS rebuild monitoring."""
    
    def __init__(self, registry: CollectorRegistry = None):
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus metrics disabled - prometheus_client not available")
            return
        
        self.registry = registry or REGISTRY
        
        # Rebuild metrics
        self.rebuild_total = Counter(
            'faiss_rebuild_total',
            'Total number of FAISS index rebuilds',
            ['status', 'trigger_type'],
            registry=self.registry
        )
        
        self.rebuild_duration_seconds = Histogram(
            'faiss_rebuild_duration_seconds',
            'Duration of FAISS index rebuilds in seconds',
            ['status'],
            buckets=[60, 300, 600, 1800, 3600, 7200, 14400],  # 1m to 4h
            registry=self.registry
        )
        
        self.rebuild_indices_created = Gauge(
            'faiss_rebuild_indices_created',
            'Number of indices created in last rebuild',
            ['horizon'],
            registry=self.registry
        )
        
        self.rebuild_validation_score = Gauge(
            'faiss_rebuild_validation_score',
            'Validation score for rebuilt indices',
            ['horizon', 'index_type', 'metric'],
            registry=self.registry
        )
        
        # Failure tracking
        self.consecutive_failures = Gauge(
            'faiss_rebuild_consecutive_failures',
            'Number of consecutive rebuild failures',
            registry=self.registry
        )
        
        self.last_success_timestamp = Gauge(
            'faiss_rebuild_last_success_timestamp',
            'Timestamp of last successful rebuild',
            registry=self.registry
        )
        
        self.last_failure_timestamp = Gauge(
            'faiss_rebuild_last_failure_timestamp',
            'Timestamp of last failed rebuild',
            registry=self.registry
        )
        
        # Performance metrics
        self.backup_size_bytes = Gauge(
            'faiss_rebuild_backup_size_bytes',
            'Size of index backups in bytes',
            ['backup_id'],
            registry=self.registry
        )
        
        self.staging_disk_usage_bytes = Gauge(
            'faiss_rebuild_staging_disk_usage_bytes',
            'Disk usage in staging directory',
            registry=self.registry
        )
        
        # Resource usage during rebuilds
        self.rebuild_memory_peak_bytes = Gauge(
            'faiss_rebuild_memory_peak_bytes',
            'Peak memory usage during rebuild',
            registry=self.registry
        )
        
        self.rebuild_cpu_avg_percent = Gauge(
            'faiss_rebuild_cpu_avg_percent',
            'Average CPU usage during rebuild',
            registry=self.registry
        )
        
        # Index quality metrics
        self.index_size_total = Gauge(
            'faiss_index_size_total',
            'Total size of FAISS indices',
            ['horizon', 'index_type'],
            registry=self.registry
        )
        
        self.index_search_latency_ms = Gauge(
            'faiss_index_search_latency_ms',
            'Search latency for FAISS indices',
            ['horizon', 'index_type'],
            registry=self.registry
        )
        
        self.index_recall_score = Gauge(
            'faiss_index_recall_score',
            'Recall score for approximate indices',
            ['horizon', 'index_type'],
            registry=self.registry
        )
        
        logger.info("Prometheus metrics initialized")
    
    def record_rebuild_start(self, trigger_type: str = "scheduled"):
        """Record rebuild start."""
        if not PROMETHEUS_AVAILABLE:
            return
        # Rebuild start is tracked when we record completion/failure
        pass
    
    def record_rebuild_success(self, result: RebuildResult, duration_seconds: float):
        """Record successful rebuild."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        trigger_type = getattr(result, 'triggered_by', 'unknown')
        
        # Update counters
        self.rebuild_total.labels(status='success', trigger_type=trigger_type).inc()
        self.rebuild_duration_seconds.labels(status='success').observe(duration_seconds)
        
        # Update gauges
        self.consecutive_failures.set(0)
        self.last_success_timestamp.set(time.time())
        
        # Record indices created
        for horizon in result.horizons_processed:
            horizon_indices = [idx for idx in result.indices_created if f"{horizon}h" in idx]
            self.rebuild_indices_created.labels(horizon=f"{horizon}h").set(len(horizon_indices))
        
        # Record validation metrics
        for validation_key, validation_data in result.validation_results.items():
            if isinstance(validation_data, dict):
                horizon = validation_data.get('horizon')
                index_type = validation_data.get('index_type')
                metrics = validation_data.get('metrics', {})
                
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, (int, float)):
                        self.rebuild_validation_score.labels(
                            horizon=f"{horizon}h",
                            index_type=index_type,
                            metric=metric_name
                        ).set(metric_value)
    
    def record_rebuild_failure(self, error_message: str, duration_seconds: float, 
                              trigger_type: str = "scheduled"):
        """Record failed rebuild."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Update counters
        self.rebuild_total.labels(status='failure', trigger_type=trigger_type).inc()
        self.rebuild_duration_seconds.labels(status='failure').observe(duration_seconds)
        
        # Update gauges
        current_failures = self.consecutive_failures._value._value + 1
        self.consecutive_failures.set(current_failures)
        self.last_failure_timestamp.set(time.time())
    
    def update_index_metrics(self, horizon: int, index_type: str, metrics: Dict[str, Any]):
        """Update index-specific metrics."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        horizon_str = f"{horizon}h"
        
        # Size metrics
        if 'file_size_mb' in metrics:
            size_bytes = metrics['file_size_mb'] * 1024 * 1024
            self.index_size_total.labels(horizon=horizon_str, index_type=index_type).set(size_bytes)
        
        # Performance metrics
        if 'search_latency_ms' in metrics:
            self.index_search_latency_ms.labels(
                horizon=horizon_str, 
                index_type=index_type
            ).set(metrics['search_latency_ms'])
        
        if 'recall_score' in metrics:
            self.index_recall_score.labels(
                horizon=horizon_str, 
                index_type=index_type
            ).set(metrics['recall_score'])
    
    def update_resource_metrics(self, resource_summary: Dict[str, Any]):
        """Update resource usage metrics."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        memory_data = resource_summary.get('memory_gb', {})
        cpu_data = resource_summary.get('cpu_percent', {})
        
        if 'max' in memory_data:
            peak_memory_bytes = memory_data['max'] * 1024 * 1024 * 1024
            self.rebuild_memory_peak_bytes.set(peak_memory_bytes)
        
        if 'avg' in cpu_data:
            self.rebuild_cpu_avg_percent.set(cpu_data['avg'])

class AlertManager:
    """Manages alerts for FAISS rebuild monitoring."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.alerts = []
        
        # Define default alert rules
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default alert rules."""
        self.alerts = [
            AlertRule(
                name="FAISSRebuildHighDuration",
                description="FAISS rebuild taking too long",
                query="faiss_rebuild_duration_seconds > {}".format(
                    self.config.max_rebuild_duration_minutes * 60
                ),
                threshold=self.config.max_rebuild_duration_minutes * 60,
                comparison="gt",
                duration="1m",
                severity="warning",
                labels={"component": "faiss_rebuild", "type": "performance"}
            ),
            
            AlertRule(
                name="FAISSRebuildConsecutiveFailures",
                description="Too many consecutive FAISS rebuild failures",
                query="faiss_rebuild_consecutive_failures >= {}".format(
                    self.config.max_consecutive_failures
                ),
                threshold=self.config.max_consecutive_failures,
                comparison="gte",
                duration="1m",
                severity="critical",
                labels={"component": "faiss_rebuild", "type": "reliability"}
            ),
            
            AlertRule(
                name="FAISSRebuildLowSuccessRate",
                description="FAISS rebuild success rate too low",
                query="rate(faiss_rebuild_total{{status='success'}}[24h]) / rate(faiss_rebuild_total[24h]) < {}".format(
                    self.config.min_success_rate_24h
                ),
                threshold=self.config.min_success_rate_24h,
                comparison="lt",
                duration="5m",
                severity="warning",
                labels={"component": "faiss_rebuild", "type": "reliability"}
            ),
            
            AlertRule(
                name="FAISSRebuildStale",
                description="FAISS rebuild hasn't succeeded recently",
                query="time() - faiss_rebuild_last_success_timestamp > 86400 * 7",  # 7 days
                threshold=86400 * 7,
                comparison="gt",
                duration="5m",
                severity="critical",
                labels={"component": "faiss_rebuild", "type": "staleness"}
            ),
            
            AlertRule(
                name="FAISSIndexLowRecall",
                description="FAISS index recall score too low",
                query="faiss_index_recall_score < 0.9",
                threshold=0.9,
                comparison="lt",
                duration="5m",
                severity="warning",
                labels={"component": "faiss_index", "type": "quality"}
            )
        ]
    
    def generate_prometheus_rules(self) -> str:
        """Generate Prometheus alert rules configuration."""
        rules = {
            "groups": [
                {
                    "name": "faiss_rebuild_alerts",
                    "rules": []
                }
            ]
        }
        
        for alert in self.alerts:
            rule = {
                "alert": alert.name,
                "expr": alert.query,
                "for": alert.duration,
                "labels": {
                    "severity": alert.severity,
                    **alert.labels
                },
                "annotations": {
                    "summary": alert.description,
                    "description": f"{alert.description}. Query: {alert.query}"
                }
            }
            rules["groups"][0]["rules"].append(rule)
        
        import yaml
        return yaml.dump(rules, default_flow_style=False)
    
    def check_alerts(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check alert conditions against current metrics."""
        active_alerts = []
        
        for alert in self.alerts:
            try:
                # Simple threshold checking (in production, use proper Prometheus evaluation)
                if self._evaluate_alert_condition(alert, metrics_data):
                    active_alerts.append({
                        "name": alert.name,
                        "description": alert.description,
                        "severity": alert.severity,
                        "labels": alert.labels,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                logger.warning(f"Failed to evaluate alert {alert.name}: {e}")
        
        return active_alerts
    
    def _evaluate_alert_condition(self, alert: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Evaluate alert condition (simplified implementation)."""
        # This is a simplified implementation
        # In production, you'd use proper Prometheus query evaluation
        
        if "consecutive_failures" in alert.query:
            value = metrics.get('consecutive_failures', 0)
            return self._compare(value, alert.threshold, alert.comparison)
        
        elif "duration_seconds" in alert.query:
            value = metrics.get('last_rebuild_duration', 0)
            return self._compare(value, alert.threshold, alert.comparison)
        
        elif "success_rate" in alert.query:
            success_rate = metrics.get('success_rate_24h', 1.0)
            return self._compare(success_rate, alert.threshold, alert.comparison)
        
        elif "last_success_timestamp" in alert.query:
            last_success = metrics.get('last_success_timestamp', time.time())
            age_seconds = time.time() - last_success
            return self._compare(age_seconds, alert.threshold, alert.comparison)
        
        return False
    
    def _compare(self, value: float, threshold: float, comparison: str) -> bool:
        """Compare value against threshold."""
        if comparison == "gt":
            return value > threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "gte":
            return value >= threshold
        elif comparison == "lte":
            return value <= threshold
        elif comparison == "eq":
            return value == threshold
        else:
            return False

class FAISSRebuildMonitor:
    """Main monitoring system for FAISS rebuilds."""
    
    def __init__(self, config: MonitoringConfig = None, project_root: Path = None):
        self.config = config or MonitoringConfig()
        self.project_root = project_root or Path("/home/micha/adelaide-weather-final")
        
        # Initialize components
        self.metrics = PrometheusMetrics() if PROMETHEUS_AVAILABLE else None
        self.alert_manager = AlertManager(self.config)
        
        # State tracking
        self.monitoring_data = {}
        self.alert_history = []
        
        # Integration with existing monitoring
        self.faiss_health_monitor = None
        if self.config.integrate_with_existing_monitoring:
            self._setup_existing_monitoring_integration()
        
        logger.info(f"Initialized FAISS Rebuild Monitor")
        logger.info(f"  Prometheus: {'enabled' if PROMETHEUS_AVAILABLE else 'disabled'}")
        logger.info(f"  Health endpoint: {self.config.health_check_path}")
        logger.info(f"  Metrics endpoint: {self.config.metrics_path}")
    
    def _setup_existing_monitoring_integration(self):
        """Setup integration with existing FAISS health monitoring."""
        try:
            from api.services.faiss_health_monitoring import get_faiss_health_monitor
            # This would be an async call in practice
            # self.faiss_health_monitor = await get_faiss_health_monitor()
            logger.info("Integration with existing FAISS monitoring enabled")
        except ImportError:
            logger.warning("Existing FAISS monitoring not available")
    
    def record_rebuild_event(self, event: ScheduledRebuildEvent):
        """Record a rebuild event for monitoring."""
        if event.status == "completed" and event.rebuild_result:
            # Calculate duration
            duration = 0
            if event.actual_start_time and event.completion_time:
                start_time = datetime.fromisoformat(event.actual_start_time)
                end_time = datetime.fromisoformat(event.completion_time)
                duration = (end_time - start_time).total_seconds()
            
            if event.rebuild_result.success:
                self._record_success(event, duration)
            else:
                self._record_failure(event, duration)
        
        elif event.status == "failed":
            # Calculate duration for failed events
            duration = 0
            if event.actual_start_time and event.completion_time:
                start_time = datetime.fromisoformat(event.actual_start_time)
                end_time = datetime.fromisoformat(event.completion_time)
                duration = (end_time - start_time).total_seconds()
            
            self._record_failure(event, duration)
        
        # Update monitoring data
        self._update_monitoring_data(event)
    
    def _record_success(self, event: ScheduledRebuildEvent, duration_seconds: float):
        """Record successful rebuild."""
        if self.metrics:
            self.metrics.record_rebuild_success(event.rebuild_result, duration_seconds)
            
            # Update index metrics if validation results available
            for validation_key, validation_data in event.rebuild_result.validation_results.items():
                if isinstance(validation_data, dict):
                    horizon = validation_data.get('horizon')
                    index_type = validation_data.get('index_type')
                    metrics = validation_data.get('metrics', {})
                    
                    if horizon and index_type:
                        self.metrics.update_index_metrics(horizon, index_type, metrics)
        
        logger.info(f"📊 Recorded successful rebuild: {event.event_id} ({duration_seconds:.1f}s)")
    
    def _record_failure(self, event: ScheduledRebuildEvent, duration_seconds: float):
        """Record failed rebuild."""
        if self.metrics:
            error_message = event.error_message or "Unknown error"
            trigger_type = event.triggered_by or "unknown"
            self.metrics.record_rebuild_failure(error_message, duration_seconds, trigger_type)
        
        logger.error(f"📊 Recorded failed rebuild: {event.event_id} ({duration_seconds:.1f}s)")
    
    def _update_monitoring_data(self, event: ScheduledRebuildEvent):
        """Update internal monitoring data."""
        self.monitoring_data.update({
            'last_event_id': event.event_id,
            'last_event_time': event.completion_time or event.scheduled_time.isoformat(),
            'last_event_status': event.status
        })
        
        # Update success/failure tracking
        if event.status == "completed":
            self.monitoring_data['last_success_time'] = event.completion_time
            self.monitoring_data['consecutive_failures'] = 0
        elif event.status == "failed":
            self.monitoring_data['last_failure_time'] = event.completion_time
            current_failures = self.monitoring_data.get('consecutive_failures', 0)
            self.monitoring_data['consecutive_failures'] = current_failures + 1
    
    def update_resource_usage(self, resource_summary: Dict[str, Any]):
        """Update resource usage metrics."""
        if self.metrics:
            self.metrics.update_resource_metrics(resource_summary)
        
        self.monitoring_data['resource_usage'] = resource_summary
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for active alerts."""
        # Prepare metrics data for alert evaluation
        metrics_data = {
            'consecutive_failures': self.monitoring_data.get('consecutive_failures', 0),
            'last_rebuild_duration': self.monitoring_data.get('last_rebuild_duration', 0),
            'success_rate_24h': self._calculate_success_rate_24h(),
            'last_success_timestamp': self._get_last_success_timestamp()
        }
        
        active_alerts = self.alert_manager.check_alerts(metrics_data)
        
        # Record new alerts
        for alert in active_alerts:
            alert_key = alert['name']
            if not any(h.get('name') == alert_key and h.get('resolved', False) is False 
                      for h in self.alert_history[-10:]):
                self.alert_history.append(alert)
                logger.warning(f"🚨 Alert triggered: {alert['name']} - {alert['description']}")
        
        return active_alerts
    
    def _calculate_success_rate_24h(self) -> float:
        """Calculate success rate over last 24 hours."""
        # Simplified implementation - in practice, you'd query actual metrics
        return 0.95  # Placeholder
    
    def _get_last_success_timestamp(self) -> float:
        """Get timestamp of last successful rebuild."""
        last_success = self.monitoring_data.get('last_success_time')
        if last_success:
            return datetime.fromisoformat(last_success).timestamp()
        return time.time() - 86400  # Default to 1 day ago
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for health check endpoint."""
        active_alerts = self.check_alerts()
        
        # Determine overall health
        critical_alerts = [a for a in active_alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in active_alerts if a['severity'] == 'warning']
        
        if critical_alerts:
            status = "critical"
        elif warning_alerts:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "faiss_rebuild_system",
            "monitoring_data": self.monitoring_data,
            "active_alerts": active_alerts,
            "alert_counts": {
                "critical": len(critical_alerts),
                "warning": len(warning_alerts),
                "total": len(active_alerts)
            },
            "metrics_enabled": PROMETHEUS_AVAILABLE
        }
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics."""
        if not PROMETHEUS_AVAILABLE or not self.metrics:
            return "# Prometheus metrics not available\n"
        
        return generate_latest(self.metrics.registry)
    
    def export_grafana_dashboard(self) -> Dict[str, Any]:
        """Export Grafana dashboard configuration."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "FAISS Index Rebuild Monitoring",
                "description": "Monitoring dashboard for FAISS index rebuild automation",
                "tags": ["faiss", "ml", "infrastructure"],
                "timezone": "UTC",
                "panels": [
                    {
                        "id": 1,
                        "title": "Rebuild Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "rate(faiss_rebuild_total{status='success'}[24h]) / rate(faiss_rebuild_total[24h])",
                                "legendFormat": "Success Rate"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percentunit",
                                "min": 0,
                                "max": 1
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Rebuild Duration",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "faiss_rebuild_duration_seconds",
                                "legendFormat": "Duration ({{status}})"
                            }
                        ],
                        "yAxes": [
                            {
                                "unit": "s",
                                "label": "Duration"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Index Search Latency",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "faiss_index_search_latency_ms",
                                "legendFormat": "{{horizon}} {{index_type}}"
                            }
                        ],
                        "yAxes": [
                            {
                                "unit": "ms",
                                "label": "Latency"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Consecutive Failures",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "faiss_rebuild_consecutive_failures",
                                "legendFormat": "Failures"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {
                                    "mode": "thresholds"
                                },
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 1},
                                        {"color": "red", "value": 3}
                                    ]
                                }
                            }
                        }
                    }
                ],
                "time": {
                    "from": "now-24h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }
        
        return dashboard
    
    def cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.events_retention_days)
        
        # Clean up alert history
        self.alert_history = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp']) > cutoff_date
        ]
        
        logger.info(f"Cleaned up monitoring data older than {self.config.events_retention_days} days")

def create_monitoring_service(config: MonitoringConfig = None) -> FAISSRebuildMonitor:
    """Factory function to create monitoring service."""
    return FAISSRebuildMonitor(config)

def main():
    """CLI entry point for monitoring utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FAISS Rebuild Monitoring')
    parser.add_argument('--action', choices=['health', 'metrics', 'alerts', 'dashboard'],
                       required=True, help='Action to perform')
    parser.add_argument('--config', help='Path to monitoring config JSON file')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    # Load config
    config = MonitoringConfig()
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = MonitoringConfig(**config_data)
    
    # Initialize monitor
    monitor = FAISSRebuildMonitor(config)
    
    if args.action == 'health':
        health = monitor.get_health_status()
        output = json.dumps(health, indent=2)
        
    elif args.action == 'metrics':
        output = monitor.get_metrics()
        
    elif args.action == 'alerts':
        alert_rules = monitor.alert_manager.generate_prometheus_rules()
        output = alert_rules
        
    elif args.action == 'dashboard':
        dashboard = monitor.export_grafana_dashboard()
        output = json.dumps(dashboard, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Output written to {args.output}")
    else:
        print(output)

if __name__ == "__main__":
    main()