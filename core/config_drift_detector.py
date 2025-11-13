#!/usr/bin/env python3
"""
Configuration Drift Detection System for Adelaide Weather Forecasting
==================================================================

Real-time monitoring and detection of configuration drift across multiple sources
including YAML files, environment variables, and infrastructure settings.

This system provides:
- Real-time file monitoring with immediate drift detection
- Environment variable consistency validation
- Multi-source configuration correlation analysis
- Severity-based alerting with actionable reports
- Integration with existing health monitoring infrastructure

CRITICAL DESIGN PRINCIPLES:
- Zero tolerance for configuration inconsistencies in production
- Real-time monitoring with sub-second detection capability
- Comprehensive drift categorization and severity assessment
- Integration with existing production health framework
- Immutable audit trail for all configuration changes

Author: Infrastructure Security Team
Version: 1.0.0 - Production Configuration Monitoring
"""

import os
import sys
import time
import json
import hashlib
import logging
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextlib import contextmanager
import queue
import fnmatch

import yaml
import numpy as np
import pandas as pd

# Prometheus metrics integration
from prometheus_client import (
    Counter, Gauge, Histogram, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)

# Setup logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional dependency for real-time file monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    logger.warning("⚠️ Watchdog not available - real-time monitoring disabled")

class DriftSeverity(Enum):
    """Configuration drift severity levels with escalation thresholds."""
    LOW = "low"              # Non-critical changes, monitoring only
    MEDIUM = "medium"        # Changes requiring review, warning alerts
    HIGH = "high"            # Changes affecting operations, immediate attention
    CRITICAL = "critical"    # Changes breaking functionality, emergency response

    def __str__(self) -> str:
        return self.value
    
    def get_priority(self) -> int:
        """Get numeric priority for severity comparison."""
        priorities = {
            DriftSeverity.LOW: 1,
            DriftSeverity.MEDIUM: 2,
            DriftSeverity.HIGH: 3,
            DriftSeverity.CRITICAL: 4
        }
        return priorities[self]

class DriftType(Enum):
    """Types of configuration drift detection."""
    FILE_CHANGE = "file_change"                    # Configuration file modifications
    ENV_MISMATCH = "environment_mismatch"          # Environment variable inconsistencies  
    SCHEMA_VIOLATION = "schema_violation"          # Configuration schema violations
    UNAUTHORIZED_ACCESS = "unauthorized_access"    # Unexpected file access patterns
    BASELINE_DEVIATION = "baseline_deviation"      # Deviation from established baselines
    CROSS_ENVIRONMENT = "cross_environment"        # Inconsistency across environments
    SECURITY_DRIFT = "security_drift"             # Security-related configuration changes
    DEPENDENCY_MISMATCH = "dependency_mismatch"    # Package/dependency version mismatches

    def __str__(self) -> str:
        return self.value

@dataclass
class DriftEvent:
    """Container for configuration drift detection events."""
    event_id: str
    drift_type: DriftType
    severity: DriftSeverity
    source_path: str
    description: str
    detected_at: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert drift event to dictionary for serialization."""
        result = asdict(self)
        # Convert enums to strings for JSON serialization
        result['drift_type'] = str(self.drift_type)
        result['severity'] = str(self.severity)
        return result
    
    def is_critical(self) -> bool:
        """Check if this is a critical drift event."""
        return self.severity == DriftSeverity.CRITICAL

class ConfigDriftMetrics:
    """Prometheus metrics for configuration drift monitoring."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize Prometheus metrics for drift monitoring."""
        self.registry = registry or CollectorRegistry()
        
        # Drift event counters by type and severity
        self.drift_events_total = Counter(
            'config_drift_events_total',
            'Total configuration drift events detected',
            ['drift_type', 'severity', 'source_type'],
            registry=self.registry
        )
        
        # Last drift detection time
        self.last_drift_time = Gauge(
            'config_drift_last_detection_timestamp',
            'Timestamp of last drift detection run',
            registry=self.registry
        )
        
        # Drift detection duration
        self.drift_detection_duration = Histogram(
            'config_drift_detection_duration_seconds',
            'Time taken to perform drift detection',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        # Current unresolved drift events by severity
        self.unresolved_events = Gauge(
            'config_drift_unresolved_events',
            'Number of unresolved drift events',
            ['severity'],
            registry=self.registry
        )
        
        # Files monitored
        self.files_monitored = Gauge(
            'config_drift_files_monitored',
            'Number of configuration files being monitored',
            registry=self.registry
        )
        
        # Environment variables monitored
        self.env_vars_monitored = Gauge(
            'config_drift_env_vars_monitored',
            'Number of environment variables being monitored',
            registry=self.registry
        )
        
        # Snapshots created
        self.snapshots_created = Counter(
            'config_drift_snapshots_total',
            'Total configuration snapshots created',
            ['snapshot_type'],
            registry=self.registry
        )
        
        # Schema validation failures
        self.schema_validation_failures = Counter(
            'config_drift_schema_validation_failures_total',
            'Total schema validation failures',
            ['config_path'],
            registry=self.registry
        )
        
        # Webhook notifications
        self.webhook_notifications = Counter(
            'config_drift_webhook_notifications_total',
            'Total webhook notifications sent',
            ['status', 'severity'],
            registry=self.registry
        )
        
        # Real-time monitoring status
        self.monitoring_active = Gauge(
            'config_drift_monitoring_active',
            'Whether drift monitoring is currently active',
            registry=self.registry
        )
    
    def record_drift_event(self, event: 'DriftEvent'):
        """Record a drift event in metrics."""
        source_type = self._get_source_type(event.source_path)
        
        self.drift_events_total.labels(
            drift_type=str(event.drift_type),
            severity=str(event.severity),
            source_type=source_type
        ).inc()
    
    def record_detection_run(self, duration_seconds: float, file_count: int, env_var_count: int):
        """Record a drift detection run."""
        self.last_drift_time.set_to_current_time()
        self.drift_detection_duration.observe(duration_seconds)
        self.files_monitored.set(file_count)
        self.env_vars_monitored.set(env_var_count)
    
    def record_snapshot_creation(self, snapshot_type: str):
        """Record snapshot creation."""
        self.snapshots_created.labels(snapshot_type=snapshot_type).inc()
    
    def record_schema_validation_failure(self, config_path: str):
        """Record schema validation failure."""
        self.schema_validation_failures.labels(config_path=config_path).inc()
    
    def record_webhook_notification(self, status: str, severity: str):
        """Record webhook notification attempt."""
        self.webhook_notifications.labels(status=status, severity=severity).inc()
    
    def update_unresolved_events(self, events: List['DriftEvent']):
        """Update unresolved events gauge."""
        severity_counts = {}
        for event in events:
            if not event.resolved:
                severity = str(event.severity)
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Reset all severities to 0 first
        for severity in ['low', 'medium', 'high', 'critical']:
            self.unresolved_events.labels(severity=severity).set(0)
        
        # Set current counts
        for severity, count in severity_counts.items():
            self.unresolved_events.labels(severity=severity).set(count)
    
    def set_monitoring_status(self, active: bool):
        """Set monitoring active status."""
        self.monitoring_active.set(1 if active else 0)
    
    def _get_source_type(self, source_path: str) -> str:
        """Determine source type from path."""
        if source_path.startswith("ENV:"):
            return "environment_variable"
        elif any(ext in source_path.lower() for ext in ['.yaml', '.yml']):
            return "yaml_config"
        elif '.json' in source_path.lower():
            return "json_config"
        elif 'dockerfile' in source_path.lower():
            return "dockerfile"
        elif 'docker-compose' in source_path.lower():
            return "docker_compose"
        elif '.env' in source_path.lower():
            return "env_file"
        else:
            return "other"
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')

class WebhookNotifier:
    """Handle webhook notifications for critical drift events."""
    
    def __init__(self, webhook_url: Optional[str] = None, webhook_enabled: bool = False):
        """Initialize webhook notifier."""
        self.webhook_url = webhook_url or os.getenv('CONFIG_DRIFT_WEBHOOK_URL')
        self.webhook_enabled = webhook_enabled and bool(self.webhook_url)
        self.notification_timeout = float(os.getenv('CONFIG_DRIFT_WEBHOOK_TIMEOUT', '10'))
        self.max_retries = int(os.getenv('CONFIG_DRIFT_WEBHOOK_RETRIES', '3'))
        
        logger.info(f"🔗 Webhook notifier initialized - Enabled: {self.webhook_enabled}")
        if self.webhook_enabled:
            logger.info(f"   Webhook URL configured: {self.webhook_url[:50]}...")
    
    async def send_notification(self, event: 'DriftEvent', metrics: ConfigDriftMetrics) -> bool:
        """Send webhook notification for drift event."""
        if not self.webhook_enabled:
            return False
        
        try:
            payload = self._build_payload(event)
            
            # Send webhook with retries
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        self.webhook_url,
                        json=payload,
                        timeout=self.notification_timeout,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code < 400:
                        metrics.record_webhook_notification('success', str(event.severity))
                        logger.info(f"✅ Webhook notification sent successfully for event {event.event_id}")
                        return True
                    else:
                        logger.warning(f"⚠️ Webhook returned status {response.status_code} (attempt {attempt + 1})")
                        
                except requests.RequestException as e:
                    logger.warning(f"⚠️ Webhook request failed (attempt {attempt + 1}): {e}")
                    
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            metrics.record_webhook_notification('failed', str(event.severity))
            logger.error(f"❌ Failed to send webhook notification after {self.max_retries} attempts")
            return False
            
        except Exception as e:
            metrics.record_webhook_notification('error', str(event.severity))
            logger.error(f"💥 Webhook notification error: {e}")
            return False
    
    def _build_payload(self, event: 'DriftEvent') -> Dict[str, Any]:
        """Build webhook payload for drift event."""
        # Slack-compatible payload format
        color_map = {
            DriftSeverity.LOW: "good",
            DriftSeverity.MEDIUM: "warning", 
            DriftSeverity.HIGH: "warning",
            DriftSeverity.CRITICAL: "danger"
        }
        
        emoji_map = {
            DriftSeverity.LOW: "ℹ️",
            DriftSeverity.MEDIUM: "⚠️",
            DriftSeverity.HIGH: "🚨",
            DriftSeverity.CRITICAL: "🔥"
        }
        
        payload = {
            "text": f"{emoji_map.get(event.severity, '⚠️')} Configuration Drift Alert",
            "attachments": [
                {
                    "color": color_map.get(event.severity, "warning"),
                    "title": f"{event.severity.value.upper()} Configuration Drift Detected",
                    "fields": [
                        {
                            "title": "Source",
                            "value": event.source_path,
                            "short": True
                        },
                        {
                            "title": "Type",
                            "value": event.drift_type.value,
                            "short": True
                        },
                        {
                            "title": "Description",
                            "value": event.description,
                            "short": False
                        },
                        {
                            "title": "Event ID",
                            "value": event.event_id,
                            "short": True
                        },
                        {
                            "title": "Detected At",
                            "value": event.detected_at,
                            "short": True
                        }
                    ],
                    "footer": "Adelaide Weather Config Drift Monitor",
                    "ts": int(time.time())
                }
            ]
        }
        
        # Add change details if available
        if event.old_value is not None and event.new_value is not None:
            payload["attachments"][0]["fields"].append({
                "title": "Change Details",
                "value": f"Old: `{event.old_value}`\nNew: `{event.new_value}`",
                "short": False
            })
        
        return payload

@dataclass
class ConfigurationSnapshot:
    """Immutable snapshot of configuration state."""
    snapshot_id: str
    timestamp: str
    file_hashes: Dict[str, str]
    environment_vars: Dict[str, str]
    schema_validation: Dict[str, bool]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compare_with(self, other: 'ConfigurationSnapshot') -> List[DriftEvent]:
        """Compare this snapshot with another to detect drift."""
        drift_events = []
        
        # Compare file hashes
        for file_path, current_hash in self.file_hashes.items():
            if file_path in other.file_hashes:
                if current_hash != other.file_hashes[file_path]:
                    event = DriftEvent(
                        event_id=f"file_change_{int(time.time())}_{hash(file_path) % 10000}",
                        drift_type=DriftType.FILE_CHANGE,
                        severity=self._determine_file_change_severity(file_path),
                        source_path=file_path,
                        description=f"Configuration file changed: {file_path}",
                        detected_at=self.timestamp,
                        old_value=other.file_hashes[file_path],
                        new_value=current_hash,
                        metadata={"comparison_snapshot": other.snapshot_id}
                    )
                    drift_events.append(event)
        
        # Compare environment variables
        for env_var, current_value in self.environment_vars.items():
            if env_var in other.environment_vars:
                if current_value != other.environment_vars[env_var]:
                    event = DriftEvent(
                        event_id=f"env_change_{int(time.time())}_{hash(env_var) % 10000}",
                        drift_type=DriftType.ENV_MISMATCH,
                        severity=self._determine_env_change_severity(env_var),
                        source_path=f"ENV:{env_var}",
                        description=f"Environment variable changed: {env_var}",
                        detected_at=self.timestamp,
                        old_value=self._mask_sensitive_value(env_var, other.environment_vars[env_var]),
                        new_value=self._mask_sensitive_value(env_var, current_value),
                        metadata={"comparison_snapshot": other.snapshot_id}
                    )
                    drift_events.append(event)
        
        return drift_events
    
    def _determine_file_change_severity(self, file_path: str) -> DriftSeverity:
        """Determine severity of file change based on file type and location."""
        file_path_lower = file_path.lower()
        
        # Critical files that affect system operation
        critical_patterns = [
            "**/docker-compose*.yml",
            "docker-compose*.yml",
            "**/Dockerfile*",
            "Dockerfile*",
            "**/kubernetes/*.yaml",
            "**/terraform/*.tf",
            "**/security*.yml",
            "**/.env.production",
            ".env.production"
        ]
        
        # High priority configuration files
        high_patterns = [
            "**/model.yaml",
            "model.yaml",
            "**/data.yaml", 
            "data.yaml",
            "**/training.yaml",
            "training.yaml",
            "**/prometheus.yml",
            "prometheus.yml",
            "**/alertmanager.yml",
            "alertmanager.yml"
        ]
        
        # Medium priority files
        medium_patterns = [
            "**/.env*",
            ".env*",
            "**/config*.yaml",
            "config*.yaml",
            "**/settings*.json",
            "settings*.json"
        ]
        
        for pattern in critical_patterns:
            if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                return DriftSeverity.CRITICAL
        
        for pattern in high_patterns:
            if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                return DriftSeverity.HIGH
        
        for pattern in medium_patterns:
            if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                return DriftSeverity.MEDIUM
        
        return DriftSeverity.LOW
    
    def _determine_env_change_severity(self, env_var: str) -> DriftSeverity:
        """Determine severity of environment variable change."""
        env_var_lower = env_var.lower()
        
        # Critical environment variables
        critical_vars = {
            'api_token', 'secret_key', 'database_url', 'jwt_secret',
            'aws_access_key_id', 'aws_secret_access_key', 'prometheus_config'
        }
        
        # High priority environment variables
        high_vars = {
            'environment', 'log_level', 'debug', 'cors_origins',
            'rate_limit_per_minute', 'model_path', 'data_path'
        }
        
        # Medium priority environment variables
        medium_vars = {
            'api_base_url', 'timeout', 'max_workers', 'batch_size'
        }
        
        if env_var_lower in critical_vars:
            return DriftSeverity.CRITICAL
        elif env_var_lower in high_vars:
            return DriftSeverity.HIGH
        elif env_var_lower in medium_vars:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.LOW
    
    def _mask_sensitive_value(self, env_var: str, value: str) -> str:
        """Mask sensitive environment variable values for logging."""
        sensitive_patterns = ['token', 'secret', 'key', 'password', 'pwd']
        
        if any(pattern in env_var.lower() for pattern in sensitive_patterns):
            if len(value) > 8:
                return value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                return "*" * len(value)
        
        return value

class ConfigurationFileHandler:
    """File system event handler for real-time configuration monitoring."""
    
    def __init__(self, drift_detector: 'ConfigurationDriftDetector'):
        self.drift_detector = drift_detector
        self.last_event_time = {}
        self.debounce_interval = 0.5  # 500ms debounce to avoid duplicate events
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        self._process_file_event(event.src_path, "modified")
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        self._process_file_event(event.src_path, "created")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        self._process_file_event(event.src_path, "deleted")
    
    def _process_file_event(self, file_path: str, event_type: str):
        """Process file system events with debouncing."""
        current_time = time.time()
        
        # Debounce rapid consecutive events
        if file_path in self.last_event_time:
            if current_time - self.last_event_time[file_path] < self.debounce_interval:
                return
        
        self.last_event_time[file_path] = current_time
        
        # Filter relevant configuration files
        if self.drift_detector._is_monitored_file(file_path):
            logger.info(f"🔍 Configuration file {event_type}: {file_path}")
            
            # Queue the drift detection
            self.drift_detector._queue_drift_check(file_path, event_type)

class ConfigurationDriftDetector:
    """
    Production-grade configuration drift detection and monitoring system.
    
    Provides real-time monitoring of configuration files, environment variables,
    and cross-environment consistency with severity-based alerting.
    """
    
    # Monitoring configuration
    DEFAULT_CHECK_INTERVAL = 60  # seconds
    DEFAULT_BASELINE_RETENTION = 30  # days
    MAX_DRIFT_EVENTS = 1000  # Maximum events to retain in memory
    
    def __init__(self, 
                 project_root: Path = None,
                 baseline_retention_days: int = DEFAULT_BASELINE_RETENTION,
                 check_interval_seconds: int = DEFAULT_CHECK_INTERVAL,
                 enable_real_time: bool = True,
                 enable_metrics: bool = True,
                 enable_webhooks: bool = None,
                 webhook_url: Optional[str] = None):
        """
        Initialize configuration drift detector.
        
        Args:
            project_root: Path to project root directory
            baseline_retention_days: Number of days to retain baseline snapshots
            check_interval_seconds: Interval for periodic drift checks
            enable_real_time: Enable real-time file monitoring
            enable_metrics: Enable Prometheus metrics collection
            enable_webhooks: Enable webhook notifications (defaults to env var)
            webhook_url: Webhook URL for notifications
        """
        self.project_root = project_root or Path("/home/micha/adelaide-weather-final")
        self.baseline_retention_days = baseline_retention_days
        self.check_interval_seconds = check_interval_seconds
        self.enable_real_time = enable_real_time
        
        # Metrics and notifications configuration
        self.enable_metrics = enable_metrics and os.getenv('CONFIG_DRIFT_METRICS_ENABLED', 'true').lower() == 'true'
        webhook_enabled = enable_webhooks if enable_webhooks is not None else \
                         os.getenv('CONFIG_DRIFT_WEBHOOK_ENABLED', 'false').lower() == 'true'
        
        # Initialize metrics
        if self.enable_metrics:
            self.metrics = ConfigDriftMetrics()
            logger.info("📊 Prometheus metrics enabled for config drift monitoring")
        else:
            self.metrics = None
            logger.info("📊 Prometheus metrics disabled")
        
        # Initialize webhook notifier
        self.webhook_notifier = WebhookNotifier(
            webhook_url=webhook_url,
            webhook_enabled=webhook_enabled
        )
        
        # Internal state
        self.drift_events: List[DriftEvent] = []
        self.configuration_snapshots: List[ConfigurationSnapshot] = []
        self.baseline_snapshot: Optional[ConfigurationSnapshot] = None
        self.monitoring_active = False
        self.drift_queue = queue.Queue()
        
        # File monitoring setup
        self.observer = None
        self.file_handler = None
        self.monitoring_thread = None
        
        # Configuration patterns to monitor
        self.monitored_patterns = [
            "**/*.yaml", "**/*.yml", "**/*.json", "*.yaml", "*.yml", "*.json",
            "**/.env*", ".env*", "**/Dockerfile*", "Dockerfile*", 
            "**/docker-compose*.yml", "docker-compose*.yml",
            "**/terraform/*.tf", "**/kubernetes/*.yaml",
            "**/prometheus*.yml", "prometheus*.yml", "**/alertmanager*.yml", "alertmanager*.yml"
        ]
        
        # Environment variables to monitor
        self.monitored_env_vars = [
            "API_TOKEN", "API_BASE_URL", "ENVIRONMENT", "CORS_ORIGINS",
            "LOG_LEVEL", "RATE_LIMIT_PER_MINUTE", "DEBUG", "SECRET_KEY",
            "DATABASE_URL", "MODEL_PATH", "DATA_PATH", "PROMETHEUS_CONFIG"
        ]
        
        logger.info(f"🔧 Configuration Drift Detector initialized")
        logger.info(f"   Project Root: {self.project_root}")
        logger.info(f"   Real-time Monitoring: {enable_real_time}")
        logger.info(f"   Check Interval: {check_interval_seconds}s")
    
    def start_monitoring(self) -> bool:
        """
        Start real-time configuration monitoring.
        
        Returns:
            bool: True if monitoring started successfully
        """
        try:
            # Create initial baseline snapshot
            self.baseline_snapshot = self._create_configuration_snapshot("baseline")
            logger.info(f"📸 Created baseline configuration snapshot")
            
            # Record metrics for monitoring startup
            if self.metrics:
                self.metrics.set_monitoring_status(True)
                self.metrics.record_snapshot_creation("baseline")
            
            if self.enable_real_time and WATCHDOG_AVAILABLE:
                # Setup file system monitoring
                if FileSystemEventHandler:
                    # Create handler that inherits from FileSystemEventHandler
                    class WatchdogFileHandler(FileSystemEventHandler):
                        def __init__(self, drift_detector):
                            super().__init__()
                            self.drift_detector = drift_detector
                            self.last_event_time = {}
                            self.debounce_interval = 0.5
                        
                        def on_modified(self, event):
                            if event.is_directory:
                                return
                            self._process_file_event(event.src_path, "modified")
                        
                        def on_created(self, event):
                            if event.is_directory:
                                return
                            self._process_file_event(event.src_path, "created")
                        
                        def on_deleted(self, event):
                            if event.is_directory:
                                return
                            self._process_file_event(event.src_path, "deleted")
                        
                        def _process_file_event(self, file_path: str, event_type: str):
                            current_time = time.time()
                            
                            # Debounce rapid consecutive events
                            if file_path in self.last_event_time:
                                if current_time - self.last_event_time[file_path] < self.debounce_interval:
                                    return
                            
                            self.last_event_time[file_path] = current_time
                            
                            # Filter relevant configuration files
                            if self.drift_detector._is_monitored_file(file_path):
                                logger.info(f"🔍 Configuration file {event_type}: {file_path}")
                                
                                # Queue the drift detection
                                self.drift_detector._queue_drift_check(file_path, event_type)
                    
                    self.file_handler = WatchdogFileHandler(self)
                    self.observer = Observer()
                
                # Monitor configuration directories
                monitor_dirs = [
                    self.project_root / "configs",
                    self.project_root / "api",
                    self.project_root / "k8s",
                    self.project_root / "terraform",
                    self.project_root / "monitoring",
                    self.project_root  # Root for .env files
                ]
                
                for monitor_dir in monitor_dirs:
                    if monitor_dir.exists():
                        self.observer.schedule(self.file_handler, str(monitor_dir), recursive=True)
                        logger.info(f"📁 Monitoring directory: {monitor_dir}")
                
                self.observer.start()
                
                # Start background monitoring thread
                self.monitoring_thread = threading.Thread(
                    target=self._monitoring_loop,
                    daemon=True,
                    name="ConfigDriftMonitor"
                )
                self.monitoring_thread.start()
            elif self.enable_real_time and not WATCHDOG_AVAILABLE:
                logger.warning("⚠️ Real-time monitoring requested but watchdog not available")
                logger.info("📋 Continuing with periodic monitoring only")
            
            self.monitoring_active = True
            logger.info(f"🚀 Configuration drift monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start configuration monitoring: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop configuration monitoring and cleanup resources."""
        self.monitoring_active = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
        
        # Update metrics
        if self.metrics:
            self.metrics.set_monitoring_status(False)
        
        logger.info(f"🛑 Configuration drift monitoring stopped")
    
    def detect_drift(self, 
                    compare_with_baseline: bool = True,
                    generate_report: bool = True) -> List[DriftEvent]:
        """
        Perform comprehensive drift detection analysis.
        
        Args:
            compare_with_baseline: Compare with baseline snapshot
            generate_report: Generate detailed drift report
            
        Returns:
            List[DriftEvent]: Detected drift events
        """
        start_time = time.time()
        logger.info(f"🔍 Starting configuration drift detection...")
        
        # Create current snapshot
        current_snapshot = self._create_configuration_snapshot("drift_check")
        
        detected_events = []
        
        # Compare with baseline if available
        if compare_with_baseline and self.baseline_snapshot:
            baseline_events = current_snapshot.compare_with(self.baseline_snapshot)
            detected_events.extend(baseline_events)
            logger.info(f"📊 Baseline comparison: {len(baseline_events)} events detected")
        
        # Compare with recent snapshots for trend analysis
        if len(self.configuration_snapshots) > 0:
            recent_snapshot = self.configuration_snapshots[-1]
            recent_events = current_snapshot.compare_with(recent_snapshot)
            detected_events.extend(recent_events)
            logger.info(f"📈 Recent comparison: {len(recent_events)} events detected")
        
        # Perform additional drift analysis
        additional_events = self._perform_advanced_drift_analysis(current_snapshot)
        detected_events.extend(additional_events)
        
        # Add to drift events
        self.drift_events.extend(detected_events)
        
        # Trim drift events if exceeding maximum
        if len(self.drift_events) > self.MAX_DRIFT_EVENTS:
            self.drift_events = self.drift_events[-self.MAX_DRIFT_EVENTS:]
        
        # Store snapshot
        self.configuration_snapshots.append(current_snapshot)
        
        # Cleanup old snapshots
        self._cleanup_old_snapshots()
        
        # Record metrics for this detection run
        if self.metrics:
            detection_duration = time.time() - start_time
            self.metrics.record_detection_run(
                detection_duration,
                len(current_snapshot.file_hashes),
                len(current_snapshot.environment_vars)
            )
            
            # Record individual drift events
            for event in detected_events:
                self.metrics.record_drift_event(event)
            
            # Update unresolved events gauge
            self.metrics.update_unresolved_events(self.drift_events)
        
        # Send webhook notifications for critical events
        critical_events = [e for e in detected_events if e.is_critical()]
        if critical_events and self.webhook_notifier.webhook_enabled:
            import asyncio
            for event in critical_events:
                try:
                    # Run webhook notification asynchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.webhook_notifier.send_notification(event, self.metrics)
                    )
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Failed to send webhook for event {event.event_id}: {e}")
        
        # Generate report if requested
        if generate_report and detected_events:
            self._generate_drift_report(detected_events)
        
        # Log summary
        severity_counts = {}
        for event in detected_events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
        
        if detected_events:
            logger.warning(f"⚠️ Configuration drift detected: {len(detected_events)} events")
            for severity, count in severity_counts.items():
                logger.warning(f"   {severity}: {count} events")
            
            # Log critical events separately for emphasis
            if critical_events:
                logger.error(f"🚨 {len(critical_events)} CRITICAL drift events detected!")
                for event in critical_events:
                    logger.error(f"   {event.description}")
        else:
            logger.info(f"✅ No configuration drift detected")
        
        return detected_events
    
    def get_drift_report(self, 
                        severity_filter: Optional[DriftSeverity] = None,
                        hours_back: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate comprehensive drift analysis report.
        
        Args:
            severity_filter: Filter events by minimum severity
            hours_back: Include only events from last N hours
            
        Returns:
            Dict containing drift analysis report
        """
        # Filter events based on criteria
        filtered_events = self.drift_events
        
        if severity_filter:
            min_priority = severity_filter.get_priority()
            filtered_events = [
                event for event in filtered_events
                if event.severity.get_priority() >= min_priority
            ]
        
        if hours_back:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            filtered_events = [
                event for event in filtered_events
                if datetime.fromisoformat(event.detected_at) >= cutoff_time
            ]
        
        # Generate comprehensive report
        report = {
            "report_generated_at": datetime.now().isoformat(),
            "monitoring_status": {
                "active": self.monitoring_active,
                "baseline_available": self.baseline_snapshot is not None,
                "real_time_enabled": self.enable_real_time,
                "snapshots_count": len(self.configuration_snapshots)
            },
            "drift_summary": {
                "total_events": len(filtered_events),
                "unresolved_events": len([e for e in filtered_events if not e.resolved]),
                "critical_events": len([e for e in filtered_events if e.severity == DriftSeverity.CRITICAL]),
                "high_events": len([e for e in filtered_events if e.severity == DriftSeverity.HIGH]),
                "medium_events": len([e for e in filtered_events if e.severity == DriftSeverity.MEDIUM]),
                "low_events": len([e for e in filtered_events if e.severity == DriftSeverity.LOW])
            },
            "drift_types": self._analyze_drift_types(filtered_events),
            "affected_sources": self._analyze_affected_sources(filtered_events),
            "recent_events": [
                event.to_dict() for event in filtered_events[-10:]  # Last 10 events
            ],
            "critical_issues": [
                event.to_dict() for event in filtered_events
                if event.severity == DriftSeverity.CRITICAL and not event.resolved
            ],
            "recommendations": self._generate_recommendations(filtered_events)
        }
        
        return report
    
    def resolve_drift_event(self, event_id: str, resolution_notes: str) -> bool:
        """
        Mark a drift event as resolved with resolution notes.
        
        Args:
            event_id: ID of the drift event to resolve
            resolution_notes: Notes describing the resolution
            
        Returns:
            bool: True if event was found and resolved
        """
        for event in self.drift_events:
            if event.event_id == event_id:
                event.resolved = True
                event.resolution_notes = resolution_notes
                logger.info(f"✅ Drift event resolved: {event_id}")
                return True
        
        logger.warning(f"❌ Drift event not found: {event_id}")
        return False
    
    def update_baseline(self) -> bool:
        """
        Update the baseline configuration snapshot to current state.
        
        Returns:
            bool: True if baseline was updated successfully
        """
        try:
            self.baseline_snapshot = self._create_configuration_snapshot("baseline_update")
            logger.info(f"📸 Baseline configuration snapshot updated")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update baseline: {e}")
            return False
    
    def _create_configuration_snapshot(self, snapshot_type: str) -> ConfigurationSnapshot:
        """Create a comprehensive configuration snapshot."""
        snapshot_id = f"{snapshot_type}_{int(time.time())}"
        
        # Compute file hashes for all monitored files
        file_hashes = {}
        for pattern in self.monitored_patterns:
            for file_path in self.project_root.rglob(pattern):
                if file_path.is_file() and self._is_monitored_file(str(file_path)):
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                            relative_path = str(file_path.relative_to(self.project_root))
                            file_hashes[relative_path] = file_hash
                    except Exception as e:
                        logger.warning(f"⚠️ Could not hash file {file_path}: {e}")
        
        # Capture environment variables
        environment_vars = {}
        for env_var in self.monitored_env_vars:
            value = os.environ.get(env_var)
            if value is not None:
                environment_vars[env_var] = value
        
        # Perform schema validation
        schema_validation = self._validate_configuration_schemas()
        
        snapshot = ConfigurationSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now().isoformat(),
            file_hashes=file_hashes,
            environment_vars=environment_vars,
            schema_validation=schema_validation,
            metadata={
                "snapshot_type": snapshot_type,
                "files_monitored": len(file_hashes),
                "env_vars_monitored": len(environment_vars)
            }
        )
        
        # Record snapshot creation in metrics
        if self.metrics:
            self.metrics.record_snapshot_creation(snapshot_type)
        
        return snapshot
    
    def _is_monitored_file(self, file_path: str) -> bool:
        """Check if a file should be monitored for drift."""
        file_path_lower = file_path.lower()
        
        # Exclude certain directories and files
        exclude_patterns = [
            "**/node_modules/**", "node_modules/**", "**/.git/**", ".git/**", 
            "**/venv/**", "venv/**", "**/forecast_env/**", "forecast_env/**", 
            "**/__pycache__/**", "__pycache__/**", "**/.next/**", ".next/**",
            "**/build/**", "build/**", "**/dist/**", "dist/**", 
            "**/*.log", "*.log", "**/*.tmp", "*.tmp"
        ]
        
        for exclude_pattern in exclude_patterns:
            if fnmatch.fnmatch(file_path_lower, exclude_pattern.lower()):
                return False
        
        # Check if matches monitored patterns
        for pattern in self.monitored_patterns:
            if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                return True
        
        return False
    
    def _validate_configuration_schemas(self) -> Dict[str, bool]:
        """Validate configuration files against expected schemas."""
        validation_results = {}
        
        # Validate YAML configuration files
        yaml_configs = {
            "configs/data.yaml": self._validate_data_config,
            "configs/model.yaml": self._validate_model_config,
            "configs/training.yaml": self._validate_training_config
        }
        
        for config_path, validator in yaml_configs.items():
            full_path = self.project_root / config_path
            if full_path.exists():
                try:
                    validation_results[config_path] = validator(full_path)
                except Exception as e:
                    logger.warning(f"⚠️ Schema validation failed for {config_path}: {e}")
                    validation_results[config_path] = False
                    if self.metrics:
                        self.metrics.record_schema_validation_failure(config_path)
        
        return validation_results
    
    def _validate_data_config(self, config_path: Path) -> bool:
        """Validate data.yaml configuration schema."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check required sections
            required_sections = ['adelaide', 'era5', 'gfs', 'preprocessing']
            for section in required_sections:
                if section not in config:
                    return False
            
            # Validate Adelaide coordinates
            adelaide = config['adelaide']
            if not isinstance(adelaide.get('lat'), (int, float)) or not isinstance(adelaide.get('lon'), (int, float)):
                return False
            
            return True
        except Exception:
            return False
    
    def _validate_model_config(self, config_path: Path) -> bool:
        """Validate model.yaml configuration schema."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check required sections
            required_sections = ['encoder', 'training', 'faiss']
            for section in required_sections:
                if section not in config:
                    return False
            
            # Validate encoder configuration
            encoder = config['encoder']
            if 'input_shape' not in encoder or 'embedding_dim' not in encoder:
                return False
            
            return True
        except Exception:
            return False
    
    def _validate_training_config(self, config_path: Path) -> bool:
        """Validate training.yaml configuration schema."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Basic validation for training configuration
            # This would be expanded based on actual training config structure
            return isinstance(config, dict) and len(config) > 0
        except Exception:
            return False
    
    def _perform_advanced_drift_analysis(self, current_snapshot: ConfigurationSnapshot) -> List[DriftEvent]:
        """Perform advanced drift analysis including cross-environment checks."""
        additional_events = []
        
        # Check for unauthorized file access patterns
        unauthorized_events = self._detect_unauthorized_access()
        additional_events.extend(unauthorized_events)
        
        # Check for schema violations
        schema_events = self._detect_schema_violations(current_snapshot)
        additional_events.extend(schema_events)
        
        # Check for security-related drift
        security_events = self._detect_security_drift(current_snapshot)
        additional_events.extend(security_events)
        
        return additional_events
    
    def _detect_unauthorized_access(self) -> List[DriftEvent]:
        """Detect unauthorized access patterns to configuration files."""
        events = []
        
        # This is a simplified implementation
        # In production, this would integrate with file system auditing
        # and access control monitoring
        
        return events
    
    def _detect_schema_violations(self, snapshot: ConfigurationSnapshot) -> List[DriftEvent]:
        """Detect configuration schema violations."""
        events = []
        
        for config_path, is_valid in snapshot.schema_validation.items():
            if not is_valid:
                event = DriftEvent(
                    event_id=f"schema_violation_{int(time.time())}_{hash(config_path) % 10000}",
                    drift_type=DriftType.SCHEMA_VIOLATION,
                    severity=DriftSeverity.HIGH,
                    source_path=config_path,
                    description=f"Configuration schema validation failed: {config_path}",
                    detected_at=snapshot.timestamp,
                    metadata={"validation_failure": True}
                )
                events.append(event)
        
        return events
    
    def _detect_security_drift(self, snapshot: ConfigurationSnapshot) -> List[DriftEvent]:
        """Detect security-related configuration drift."""
        events = []
        
        # Check for security-sensitive environment variables
        security_vars = ['API_TOKEN', 'SECRET_KEY', 'DATABASE_URL']
        
        for var in security_vars:
            if var in snapshot.environment_vars:
                value = snapshot.environment_vars[var]
                
                # Check for obviously insecure values
                insecure_patterns = ['test', 'demo', 'localhost', 'password', '123']
                if any(pattern in value.lower() for pattern in insecure_patterns):
                    event = DriftEvent(
                        event_id=f"security_drift_{int(time.time())}_{hash(var) % 10000}",
                        drift_type=DriftType.SECURITY_DRIFT,
                        severity=DriftSeverity.CRITICAL,
                        source_path=f"ENV:{var}",
                        description=f"Potentially insecure value detected in {var}",
                        detected_at=snapshot.timestamp,
                        metadata={"security_concern": True}
                    )
                    events.append(event)
                
                # Advanced token entropy validation for API_TOKEN
                if var == 'API_TOKEN':
                    try:
                        # Import TokenEntropyValidator
                        import sys
                        from pathlib import Path
                        api_path = Path(__file__).parent.parent / "api"
                        sys.path.insert(0, str(api_path))
                        from token_rotation_cli import TokenEntropyValidator
                        
                        # Validate token security
                        is_valid, issues = TokenEntropyValidator.validate_token(value)
                        
                        if not is_valid:
                            # Calculate detailed metrics for recommendations
                            metrics = TokenEntropyValidator.calculate_entropy(value)
                            
                            # Generate specific recommendations
                            recommendations = []
                            if len(value) < TokenEntropyValidator.MIN_TOKEN_LENGTH:
                                recommendations.append(f"Increase token length to at least {TokenEntropyValidator.MIN_TOKEN_LENGTH} characters")
                            
                            if metrics.entropy_bits < TokenEntropyValidator.MIN_ENTROPY_BITS:
                                recommendations.append(f"Increase token entropy to at least {TokenEntropyValidator.MIN_ENTROPY_BITS} bits (current: {metrics.entropy_bits:.1f})")
                            
                            if metrics.charset_diversity < TokenEntropyValidator.MIN_CHARSET_DIVERSITY:
                                recommendations.append(f"Use diverse character sets including uppercase, lowercase, digits, and special characters (current diversity: {metrics.charset_diversity:.2f})")
                            
                            if metrics.pattern_score < 0.5:
                                recommendations.append("Avoid repetitive patterns and sequential characters")
                            
                            # Add recommendation for using the token rotation CLI
                            recommendations.append("Use 'python api/token_rotation_cli.py generate' to create a secure token")
                            
                            event = DriftEvent(
                                event_id=f"weak_token_drift_{int(time.time())}_{hash(value) % 10000}",
                                drift_type=DriftType.SECURITY_DRIFT,
                                severity=DriftSeverity.CRITICAL,
                                source_path=f"ENV:{var}",
                                description=f"Weak API token detected with insufficient security properties",
                                detected_at=snapshot.timestamp,
                                metadata={
                                    "security_concern": True,
                                    "token_security_analysis": {
                                        "length": metrics.length,
                                        "entropy_bits": metrics.entropy_bits,
                                        "charset_diversity": metrics.charset_diversity,
                                        "pattern_score": metrics.pattern_score,
                                        "security_level": metrics.security_level,
                                        "validation_issues": issues,
                                        "recommendations": recommendations,
                                        "minimum_requirements": {
                                            "min_length": TokenEntropyValidator.MIN_TOKEN_LENGTH,
                                            "min_entropy_bits": TokenEntropyValidator.MIN_ENTROPY_BITS,
                                            "min_charset_diversity": TokenEntropyValidator.MIN_CHARSET_DIVERSITY
                                        }
                                    }
                                }
                            )
                            events.append(event)
                            
                    except ImportError as e:
                        # Fallback validation if TokenEntropyValidator is not available
                        logger.warning(f"TokenEntropyValidator not available: {e}")
                        if len(value) < 32:
                            event = DriftEvent(
                                event_id=f"short_token_drift_{int(time.time())}_{hash(value) % 10000}",
                                drift_type=DriftType.SECURITY_DRIFT,
                                severity=DriftSeverity.CRITICAL,
                                source_path=f"ENV:{var}",
                                description=f"API token is too short (minimum 32 characters required)",
                                detected_at=snapshot.timestamp,
                                metadata={
                                    "security_concern": True,
                                    "fallback_validation": True,
                                    "token_length": len(value),
                                    "recommendations": [
                                        "Generate a longer token with at least 32 characters",
                                        "Use a cryptographically secure random generator"
                                    ]
                                }
                            )
                            events.append(event)
                            
                    except Exception as e:
                        # Log error but don't fail the drift detection
                        logger.error(f"Error during token validation: {e}")
        
        return events
    
    def _queue_drift_check(self, file_path: str, event_type: str):
        """Queue a drift check for real-time processing."""
        self.drift_queue.put({
            'file_path': file_path,
            'event_type': event_type,
            'timestamp': datetime.now().isoformat()
        })
    
    def _monitoring_loop(self):
        """Background monitoring loop for processing drift events."""
        logger.info(f"🔄 Configuration monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Process queued drift checks
                while not self.drift_queue.empty():
                    try:
                        drift_item = self.drift_queue.get_nowait()
                        self._process_real_time_drift(drift_item)
                    except queue.Empty:
                        break
                
                # Periodic comprehensive drift check
                time.sleep(self.check_interval_seconds)
                
                if self.monitoring_active:
                    logger.debug(f"🔍 Performing periodic drift check...")
                    detected_events = self.detect_drift(generate_report=False)
                    
                    # Log critical events immediately
                    critical_events = [e for e in detected_events if e.is_critical()]
                    if critical_events:
                        logger.error(f"🚨 {len(critical_events)} CRITICAL configuration drift events detected!")
                        for event in critical_events:
                            logger.error(f"   {event.description}")
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(5)  # Brief pause before retrying
    
    def _process_real_time_drift(self, drift_item: Dict[str, Any]):
        """Process real-time drift detection."""
        file_path = drift_item['file_path']
        event_type = drift_item['event_type']
        
        # Create immediate drift event for real-time changes
        relative_path = str(Path(file_path).relative_to(self.project_root))
        
        # Determine severity based on file
        severity = DriftSeverity.LOW
        if any(pattern in file_path.lower() for pattern in ['docker', 'kubernetes', 'terraform']):
            severity = DriftSeverity.CRITICAL
        elif any(pattern in file_path.lower() for pattern in ['config', '.env', 'model', 'data']):
            severity = DriftSeverity.HIGH
        
        event = DriftEvent(
            event_id=f"realtime_{event_type}_{int(time.time())}_{hash(file_path) % 10000}",
            drift_type=DriftType.FILE_CHANGE,
            severity=severity,
            source_path=relative_path,
            description=f"Real-time file {event_type}: {relative_path}",
            detected_at=drift_item['timestamp'],
            metadata={"real_time": True, "event_type": event_type}
        )
        
        self.drift_events.append(event)
        
        # Log based on severity
        if severity in [DriftSeverity.CRITICAL, DriftSeverity.HIGH]:
            logger.warning(f"⚠️ {severity.value.upper()} configuration change: {relative_path}")
    
    def _cleanup_old_snapshots(self):
        """Remove snapshots older than retention period."""
        cutoff_time = datetime.now() - timedelta(days=self.baseline_retention_days)
        
        self.configuration_snapshots = [
            snapshot for snapshot in self.configuration_snapshots
            if datetime.fromisoformat(snapshot.timestamp) >= cutoff_time
        ]
    
    def _analyze_drift_types(self, events: List[DriftEvent]) -> Dict[str, int]:
        """Analyze distribution of drift types."""
        type_counts = {}
        for event in events:
            drift_type = str(event.drift_type)
            type_counts[drift_type] = type_counts.get(drift_type, 0) + 1
        return type_counts
    
    def _analyze_affected_sources(self, events: List[DriftEvent]) -> Dict[str, int]:
        """Analyze most frequently affected configuration sources."""
        source_counts = {}
        for event in events:
            source = event.source_path
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Return top 10 most affected sources
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_sources[:10])
    
    def _generate_recommendations(self, events: List[DriftEvent]) -> List[str]:
        """Generate actionable recommendations based on drift patterns."""
        recommendations = []
        
        # Analyze patterns and generate recommendations
        critical_count = len([e for e in events if e.severity == DriftSeverity.CRITICAL])
        unresolved_count = len([e for e in events if not e.resolved])
        
        if critical_count > 0:
            recommendations.append(f"🚨 Immediate action required: {critical_count} critical configuration issues need resolution")
        
        if unresolved_count > 10:
            recommendations.append(f"📋 Review and resolve {unresolved_count} pending configuration drift events")
        
        # Check for frequent file changes
        file_events = [e for e in events if e.drift_type == DriftType.FILE_CHANGE]
        if len(file_events) > 20:
            recommendations.append("🔧 Consider implementing change management procedures for frequent configuration updates")
        
        # Check for environment variable issues
        env_events = [e for e in events if e.drift_type == DriftType.ENV_MISMATCH]
        if len(env_events) > 5:
            recommendations.append("🌍 Review environment variable management and ensure consistency across deployments")
        
        # Security recommendations
        security_events = [e for e in events if e.drift_type == DriftType.SECURITY_DRIFT]
        if len(security_events) > 0:
            recommendations.append("🔐 Security review required: Configuration changes may impact system security")
        
        if not recommendations:
            recommendations.append("✅ Configuration drift within acceptable parameters")
        
        return recommendations
    
    def _generate_drift_report(self, events: List[DriftEvent]):
        """Generate and save detailed drift report."""
        report = self.get_drift_report()
        
        # Save report to file
        report_path = self.project_root / "config_drift_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Configuration drift report saved: {report_path}")
    
    def get_prometheus_metrics(self) -> Optional[str]:
        """Get Prometheus metrics in text format."""
        if self.metrics:
            return self.metrics.get_prometheus_metrics()
        return None

def main():
    """Main entry point for configuration drift detection."""
    detector = ConfigurationDriftDetector()
    
    try:
        # Start monitoring
        if detector.start_monitoring():
            logger.info("🚀 Configuration drift monitoring is running...")
            
            # Run initial drift detection
            initial_events = detector.detect_drift()
            
            if initial_events:
                logger.warning(f"⚠️ Initial configuration drift detected: {len(initial_events)} events")
            else:
                logger.info("✅ No initial configuration drift detected")
            
            # Keep the main thread alive
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("👋 Shutting down configuration drift monitoring...")
        else:
            logger.error("❌ Failed to start configuration drift monitoring")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Configuration drift detector crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        detector.stop_monitoring()

if __name__ == "__main__":
    main()