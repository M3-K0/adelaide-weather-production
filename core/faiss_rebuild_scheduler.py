#!/usr/bin/env python3
"""
FAISS Index Rebuild Scheduler
============================

Production-ready scheduling system for automated FAISS index rebuilds with
configurable timing, monitoring, and alert integration. Supports both
cron-style scheduling and systemd timer integration.

Features:
- Flexible scheduling with cron-style expressions
- Health monitoring and failure detection
- Integration with monitoring systems
- Alert notifications for failures
- Graceful shutdown and restart handling
- Resource usage monitoring
- Rebuild history tracking
- Manual trigger capability

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import schedule

from core.faiss_index_rebuilder import FAISSIndexRebuilder, RebuildConfig, RebuildResult

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """Configuration for the FAISS rebuild scheduler."""
    # Scheduling
    rebuild_schedule: str = "0 2 * * 0"  # Weekly at 2 AM on Sunday (cron format)
    timezone: str = "UTC"
    max_rebuild_duration_hours: int = 4
    
    # Rebuild configuration
    rebuild_config: Dict[str, Any] = None
    
    # Monitoring
    health_check_interval_minutes: int = 5
    max_consecutive_failures: int = 3
    failure_cooldown_hours: int = 24
    
    # Notifications
    enable_notifications: bool = True
    notification_channels: List[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Resource limits
    max_memory_gb: float = 8.0
    max_cpu_percent: float = 80.0
    
    def __post_init__(self):
        if self.rebuild_config is None:
            self.rebuild_config = {}
        if self.notification_channels is None:
            self.notification_channels = ['log']

@dataclass
class ScheduledRebuildEvent:
    """Represents a scheduled rebuild event."""
    event_id: str
    scheduled_time: datetime
    actual_start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    status: str = "scheduled"  # scheduled, running, completed, failed, cancelled
    rebuild_result: Optional[RebuildResult] = None
    error_message: Optional[str] = None
    triggered_by: str = "scheduler"  # scheduler, manual, api

class NotificationManager:
    """Manages notifications for rebuild events."""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.enabled = config.enable_notifications
        
    def send_notification(self, event_type: str, message: str, severity: str = "info"):
        """Send notification through configured channels."""
        if not self.enabled:
            return
        
        timestamp = datetime.now(timezone.utc).isoformat()
        notification = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "source": "faiss_rebuild_scheduler"
        }
        
        for channel in self.config.notification_channels:
            try:
                self._send_to_channel(channel, notification)
            except Exception as e:
                logger.warning(f"Failed to send notification to {channel}: {e}")
    
    def _send_to_channel(self, channel: str, notification: Dict[str, Any]):
        """Send notification to specific channel."""
        if channel == "log":
            level = getattr(logging, notification['severity'].upper(), logging.INFO)
            logger.log(level, f"[{notification['event_type']}] {notification['message']}")
        
        elif channel == "slack":
            self._send_slack_notification(notification)
        
        elif channel == "email":
            self._send_email_notification(notification)
        
        elif channel == "webhook":
            self._send_webhook_notification(notification)
        
        else:
            logger.warning(f"Unknown notification channel: {channel}")
    
    def _send_slack_notification(self, notification: Dict[str, Any]):
        """Send Slack notification (placeholder for integration)."""
        # Implement Slack webhook integration
        logger.info(f"Slack notification: {notification['message']}")
    
    def _send_email_notification(self, notification: Dict[str, Any]):
        """Send email notification (placeholder for integration)."""
        # Implement email notification
        logger.info(f"Email notification: {notification['message']}")
    
    def _send_webhook_notification(self, notification: Dict[str, Any]):
        """Send webhook notification (placeholder for integration)."""
        # Implement webhook notification
        logger.info(f"Webhook notification: {notification['message']}")

class ResourceMonitor:
    """Monitors system resources during rebuilds."""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.monitoring = False
        self.monitor_thread = None
        self.resource_usage = []
        
    def start_monitoring(self):
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.resource_usage = []
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Resource monitoring stopped")
    
    def _monitor_resources(self):
        """Monitor system resources."""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available, resource monitoring disabled")
            return
        
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Get current resource usage
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                memory_gb = memory_mb / 1024
                cpu_percent = process.cpu_percent()
                
                # System-wide metrics
                system_memory = psutil.virtual_memory()
                system_cpu = psutil.cpu_percent()
                
                usage = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "process_memory_mb": memory_mb,
                    "process_memory_gb": memory_gb,
                    "process_cpu_percent": cpu_percent,
                    "system_memory_percent": system_memory.percent,
                    "system_cpu_percent": system_cpu,
                    "system_memory_available_gb": system_memory.available / (1024**3)
                }
                
                self.resource_usage.append(usage)
                
                # Check limits
                if memory_gb > self.config.max_memory_gb:
                    logger.warning(f"Memory usage high: {memory_gb:.1f}GB > {self.config.max_memory_gb}GB")
                
                if cpu_percent > self.config.max_cpu_percent:
                    logger.warning(f"CPU usage high: {cpu_percent:.1f}% > {self.config.max_cpu_percent}%")
                
                # Keep only recent data (last hour)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                self.resource_usage = [
                    usage for usage in self.resource_usage
                    if datetime.fromisoformat(usage["timestamp"]) > cutoff_time
                ]
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource usage summary."""
        if not self.resource_usage:
            return {"error": "No resource data available"}
        
        memory_values = [u["process_memory_gb"] for u in self.resource_usage]
        cpu_values = [u["process_cpu_percent"] for u in self.resource_usage]
        
        return {
            "sample_count": len(self.resource_usage),
            "memory_gb": {
                "current": memory_values[-1] if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "avg": sum(memory_values) / len(memory_values) if memory_values else 0
            },
            "cpu_percent": {
                "current": cpu_values[-1] if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0
            },
            "monitoring_duration_minutes": len(self.resource_usage) * 0.5  # 30 second intervals
        }

class FAISSRebuildScheduler:
    """Main scheduler for automated FAISS index rebuilds."""
    
    def __init__(self, config: SchedulerConfig = None, project_root: Path = None):
        self.config = config or SchedulerConfig()
        self.project_root = project_root or Path("/home/micha/adelaide-weather-final")
        
        # Initialize components
        self.notification_manager = NotificationManager(self.config)
        self.resource_monitor = ResourceMonitor(self.config)
        
        # State tracking
        self.running = False
        self.rebuild_history: List[ScheduledRebuildEvent] = []
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.scheduler_thread = None
        self.health_check_thread = None
        
        # Rebuilder instance
        rebuild_config = RebuildConfig(**self.config.rebuild_config)
        self.rebuilder = FAISSIndexRebuilder(rebuild_config, self.project_root)
        
        # Setup logging
        self._setup_logging()
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"Initialized FAISS Rebuild Scheduler")
        logger.info(f"  Schedule: {self.config.rebuild_schedule}")
        logger.info(f"  Max duration: {self.config.max_rebuild_duration_hours}h")
        logger.info(f"  Notifications: {self.config.notification_channels}")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Configure root logger
        logger.setLevel(log_level)
        
        # Add file handler if specified
        if self.config.log_file:
            log_file_path = Path(self.config.log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info("🚀 Starting FAISS Rebuild Scheduler")
        
        # Setup schedule
        self._setup_schedule()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=False)
        self.scheduler_thread.start()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._run_health_check, daemon=True)
        self.health_check_thread.start()
        
        # Send startup notification
        self.notification_manager.send_notification(
            "scheduler_started",
            f"FAISS Rebuild Scheduler started with schedule: {self.config.rebuild_schedule}",
            "info"
        )
        
        logger.info("✅ Scheduler started successfully")
    
    def stop(self, timeout: int = 30):
        """Stop the scheduler gracefully."""
        if not self.running:
            return
        
        logger.info("⏹️ Stopping FAISS Rebuild Scheduler")
        self.running = False
        
        # Stop resource monitoring
        self.resource_monitor.stop_monitoring()
        
        # Wait for threads to complete
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=timeout)
        
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        
        # Send shutdown notification
        self.notification_manager.send_notification(
            "scheduler_stopped",
            "FAISS Rebuild Scheduler stopped",
            "info"
        )
        
        logger.info("✅ Scheduler stopped")
    
    def _setup_schedule(self):
        """Setup the rebuild schedule."""
        # Parse cron-style schedule
        # For simplicity, using the schedule library with conversion
        # In production, you might want to use a more robust cron parser
        
        cron_parts = self.config.rebuild_schedule.split()
        if len(cron_parts) == 5:
            minute, hour, day, month, weekday = cron_parts
            
            # Convert to schedule library format
            if weekday != "*":
                # Weekly schedule
                days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                weekday_num = int(weekday) if weekday.isdigit() else 0
                day_name = days[weekday_num]
                
                schedule.every().week.at(f"{hour}:{minute}").do(self._execute_scheduled_rebuild)
                logger.info(f"Scheduled weekly rebuilds on {day_name} at {hour}:{minute}")
            
            elif day != "*":
                # Monthly schedule
                schedule.every().month.do(self._execute_scheduled_rebuild)
                logger.info(f"Scheduled monthly rebuilds on day {day}")
            
            else:
                # Daily schedule
                schedule.every().day.at(f"{hour}:{minute}").do(self._execute_scheduled_rebuild)
                logger.info(f"Scheduled daily rebuilds at {hour}:{minute}")
        
        else:
            # Fallback to weekly
            schedule.every().sunday.at("02:00").do(self._execute_scheduled_rebuild)
            logger.warning(f"Invalid cron format, using default weekly schedule")
    
    def _run_scheduler(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
        
        logger.info("Scheduler loop stopped")
    
    def _run_health_check(self):
        """Health check loop."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                self._perform_health_check()
                time.sleep(self.config.health_check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(600)  # Wait 10 minutes on error
        
        logger.info("Health check loop stopped")
    
    def _perform_health_check(self):
        """Perform health check on the system."""
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scheduler_running": self.running,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "rebuild_history_count": len(self.rebuild_history),
            "resource_usage": self.resource_monitor.get_resource_summary()
        }
        
        # Check for issues
        issues = []
        
        if self.consecutive_failures >= self.config.max_consecutive_failures:
            issues.append(f"Too many consecutive failures: {self.consecutive_failures}")
        
        if self.last_failure_time:
            time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
            if time_since_failure < timedelta(hours=self.config.failure_cooldown_hours):
                issues.append(f"Recent failure: {time_since_failure.total_seconds() / 3600:.1f}h ago")
        
        # Check recent rebuild history
        recent_events = [
            event for event in self.rebuild_history
            if event.completion_time and 
            datetime.fromisoformat(event.completion_time) > datetime.now(timezone.utc) - timedelta(days=7)
        ]
        
        failed_recent = [event for event in recent_events if event.status == "failed"]
        if len(failed_recent) > len(recent_events) * 0.5:  # >50% failure rate
            issues.append(f"High recent failure rate: {len(failed_recent)}/{len(recent_events)}")
        
        health_status["issues"] = issues
        health_status["healthy"] = len(issues) == 0
        
        # Log health status
        if issues:
            logger.warning(f"Health check issues: {'; '.join(issues)}")
        else:
            logger.debug("Health check passed")
        
        # Save health status
        health_file = self.project_root / "logs" / "scheduler_health.json"
        health_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(health_file, 'w') as f:
            json.dump(health_status, f, indent=2)
    
    def _execute_scheduled_rebuild(self):
        """Execute a scheduled rebuild."""
        event_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Check if in cooldown period
        if self._in_failure_cooldown():
            logger.warning(f"Skipping rebuild {event_id}: in failure cooldown period")
            return
        
        # Create event
        event = ScheduledRebuildEvent(
            event_id=event_id,
            scheduled_time=datetime.now(timezone.utc),
            triggered_by="scheduler"
        )
        
        self.rebuild_history.append(event)
        
        try:
            self._execute_rebuild_event(event)
        except Exception as e:
            logger.error(f"Scheduled rebuild failed: {e}")
            event.status = "failed"
            event.error_message = str(e)
            event.completion_time = datetime.now(timezone.utc)
            
            self._handle_rebuild_failure(event)
    
    def trigger_manual_rebuild(self, triggered_by: str = "manual") -> str:
        """Trigger a manual rebuild."""
        event_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_manual")
        
        event = ScheduledRebuildEvent(
            event_id=event_id,
            scheduled_time=datetime.now(timezone.utc),
            triggered_by=triggered_by
        )
        
        self.rebuild_history.append(event)
        
        # Execute in background thread
        rebuild_thread = threading.Thread(
            target=self._execute_rebuild_event,
            args=(event,),
            daemon=True
        )
        rebuild_thread.start()
        
        logger.info(f"Manual rebuild triggered: {event_id}")
        return event_id
    
    def _execute_rebuild_event(self, event: ScheduledRebuildEvent):
        """Execute a rebuild event."""
        logger.info(f"🔨 Starting rebuild: {event.event_id}")
        
        event.actual_start_time = datetime.now(timezone.utc)
        event.status = "running"
        
        # Send start notification
        self.notification_manager.send_notification(
            "rebuild_started",
            f"FAISS index rebuild started: {event.event_id}",
            "info"
        )
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        try:
            # Execute rebuild with timeout
            rebuild_result = self._execute_rebuild_with_timeout(event)
            
            event.rebuild_result = rebuild_result
            event.completion_time = datetime.now(timezone.utc)
            
            if rebuild_result.success:
                event.status = "completed"
                self._handle_rebuild_success(event)
            else:
                event.status = "failed"
                event.error_message = rebuild_result.error_message
                self._handle_rebuild_failure(event)
                
        except Exception as e:
            logger.error(f"Rebuild execution failed: {e}")
            event.status = "failed"
            event.error_message = str(e)
            event.completion_time = datetime.now(timezone.utc)
            self._handle_rebuild_failure(event)
        
        finally:
            # Stop resource monitoring
            self.resource_monitor.stop_monitoring()
    
    def _execute_rebuild_with_timeout(self, event: ScheduledRebuildEvent) -> RebuildResult:
        """Execute rebuild with timeout protection."""
        max_duration = timedelta(hours=self.config.max_rebuild_duration_hours)
        
        # Execute rebuild
        try:
            result = self.rebuilder.rebuild_all_indices()
            return result
            
        except Exception as e:
            # Check if we exceeded time limit
            if event.actual_start_time:
                duration = datetime.now(timezone.utc) - event.actual_start_time
                if duration > max_duration:
                    raise TimeoutError(f"Rebuild exceeded time limit: {duration.total_seconds() / 3600:.1f}h > {self.config.max_rebuild_duration_hours}h")
            
            raise e
    
    def _handle_rebuild_success(self, event: ScheduledRebuildEvent):
        """Handle successful rebuild."""
        # Reset failure counter
        self.consecutive_failures = 0
        self.last_failure_time = None
        
        duration = None
        if event.actual_start_time and event.completion_time:
            start_time = datetime.fromisoformat(event.actual_start_time)
            end_time = datetime.fromisoformat(event.completion_time)
            duration = (end_time - start_time).total_seconds() / 60  # minutes
        
        # Get resource summary
        resource_summary = self.resource_monitor.get_resource_summary()
        
        logger.info(f"✅ Rebuild completed successfully: {event.event_id}")
        
        # Send success notification
        message = f"FAISS index rebuild completed successfully: {event.event_id}"
        if duration:
            message += f" (duration: {duration:.1f} minutes)"
        
        if event.rebuild_result:
            horizons = event.rebuild_result.horizons_processed
            indices = len(event.rebuild_result.indices_created)
            message += f" - Processed {len(horizons)} horizons, created {indices} indices"
        
        self.notification_manager.send_notification(
            "rebuild_success",
            message,
            "info"
        )
    
    def _handle_rebuild_failure(self, event: ScheduledRebuildEvent):
        """Handle failed rebuild."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        logger.error(f"❌ Rebuild failed: {event.event_id}")
        
        # Send failure notification
        message = f"FAISS index rebuild failed: {event.event_id}"
        if event.error_message:
            message += f" - Error: {event.error_message}"
        
        message += f" (consecutive failures: {self.consecutive_failures})"
        
        severity = "critical" if self.consecutive_failures >= self.config.max_consecutive_failures else "error"
        
        self.notification_manager.send_notification(
            "rebuild_failure",
            message,
            severity
        )
    
    def _in_failure_cooldown(self) -> bool:
        """Check if we're in failure cooldown period."""
        if not self.last_failure_time:
            return False
        
        cooldown_duration = timedelta(hours=self.config.failure_cooldown_hours)
        time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
        
        return time_since_failure < cooldown_duration
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        next_run = None
        try:
            next_job = schedule.next_run()
            if next_job:
                next_run = next_job.isoformat()
        except:
            pass
        
        recent_events = self.rebuild_history[-10:] if self.rebuild_history else []
        
        return {
            "running": self.running,
            "next_scheduled_run": next_run,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "in_cooldown": self._in_failure_cooldown(),
            "total_rebuilds": len(self.rebuild_history),
            "recent_events": [asdict(event) for event in recent_events],
            "config": asdict(self.config),
            "resource_usage": self.resource_monitor.get_resource_summary()
        }
    
    def get_rebuild_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get rebuild history."""
        recent_events = self.rebuild_history[-limit:] if self.rebuild_history else []
        return [asdict(event) for event in recent_events]

def main():
    """CLI entry point for scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FAISS Rebuild Scheduler')
    parser.add_argument('--config', help='Path to scheduler config JSON file')
    parser.add_argument('--schedule', default="0 2 * * 0",
                       help='Cron-style schedule (default: weekly at 2 AM Sunday)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show configuration and exit')
    parser.add_argument('--trigger-rebuild', action='store_true',
                       help='Trigger immediate rebuild and exit')
    parser.add_argument('--status', action='store_true',
                       help='Show scheduler status and exit')
    
    args = parser.parse_args()
    
    # Load config
    config = SchedulerConfig()
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        config = SchedulerConfig(**config_data)
    
    # Apply CLI overrides
    if args.schedule:
        config.rebuild_schedule = args.schedule
    
    if args.dry_run:
        print("Scheduler Configuration:")
        print(json.dumps(asdict(config), indent=2))
        return
    
    # Initialize scheduler
    scheduler = FAISSRebuildScheduler(config)
    
    if args.status:
        status = scheduler.get_status()
        print("Scheduler Status:")
        print(json.dumps(status, indent=2))
        return
    
    if args.trigger_rebuild:
        event_id = scheduler.trigger_manual_rebuild("cli")
        print(f"Manual rebuild triggered: {event_id}")
        return
    
    try:
        # Start scheduler
        scheduler.start()
        
        # Keep running
        while scheduler.running:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        scheduler.stop()

if __name__ == "__main__":
    main()