#!/usr/bin/env python3
"""
FAISS Rebuild Service Management
===============================

Production service management for FAISS index rebuilds with systemd integration,
service lifecycle management, and operational utilities.

Features:
- Systemd service integration
- Service lifecycle management
- Configuration management
- Log rotation and monitoring
- Health check endpoints
- Graceful shutdown handling
- Process monitoring and restart

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import json
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.faiss_rebuild_scheduler import FAISSRebuildScheduler, SchedulerConfig
from core.faiss_rebuild_monitoring import FAISSRebuildMonitor, MonitoringConfig

logger = logging.getLogger(__name__)

class FAISSRebuildService:
    """Main service class for FAISS rebuild automation."""
    
    def __init__(self, config_file: str = None):
        """Initialize the service."""
        self.config_file = config_file or "/etc/faiss-rebuild/config.json"
        self.pid_file = "/var/run/faiss-rebuild.pid"
        self.log_file = "/var/log/faiss-rebuild/service.log"
        
        # Load configuration
        self.scheduler_config, self.monitoring_config = self._load_config()
        
        # Initialize components
        self.scheduler = None
        self.monitor = None
        
        # Setup logging
        self._setup_logging()
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGHUP, self._reload_config)
        
        self.running = False
        
    def _load_config(self) -> tuple:
        """Load service configuration."""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                scheduler_config = SchedulerConfig(**config_data.get('scheduler', {}))
                monitoring_config = MonitoringConfig(**config_data.get('monitoring', {}))
                
                logger.info(f"Loaded configuration from {self.config_file}")
                
            else:
                logger.warning(f"Config file not found: {self.config_file}, using defaults")
                scheduler_config = SchedulerConfig()
                monitoring_config = MonitoringConfig()
            
            return scheduler_config, monitoring_config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return SchedulerConfig(), MonitoringConfig()
    
    def _setup_logging(self):
        """Setup service logging."""
        # Create log directory
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.scheduler_config.log_level, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger.info("Service logging initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _reload_config(self, signum, frame):
        """Reload configuration on SIGHUP."""
        logger.info("Received SIGHUP, reloading configuration...")
        try:
            new_scheduler_config, new_monitoring_config = self._load_config()
            
            # Restart components with new config
            if self.scheduler:
                self.scheduler.stop()
                self.scheduler = FAISSRebuildScheduler(new_scheduler_config)
                self.scheduler.start()
            
            if self.monitor:
                self.monitor = FAISSRebuildMonitor(new_monitoring_config)
            
            self.scheduler_config = new_scheduler_config
            self.monitoring_config = new_monitoring_config
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
    
    def start(self):
        """Start the service."""
        if self.running:
            logger.warning("Service already running")
            return
        
        logger.info("🚀 Starting FAISS Rebuild Service")
        
        try:
            # Write PID file
            self._write_pid_file()
            
            # Initialize components
            self.scheduler = FAISSRebuildScheduler(self.scheduler_config)
            self.monitor = FAISSRebuildMonitor(self.monitoring_config)
            
            # Start scheduler
            self.scheduler.start()
            
            self.running = True
            
            logger.info("✅ FAISS Rebuild Service started successfully")
            
            # Keep service running
            self._run_main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the service."""
        if not self.running:
            return
        
        logger.info("⏹️ Stopping FAISS Rebuild Service")
        
        try:
            # Stop scheduler
            if self.scheduler:
                self.scheduler.stop()
            
            self.running = False
            
            # Remove PID file
            self._remove_pid_file()
            
            logger.info("✅ Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
    
    def _run_main_loop(self):
        """Main service loop."""
        logger.info("Service main loop started")
        
        try:
            while self.running:
                # Perform periodic health checks
                if self.monitor:
                    health_status = self.monitor.get_health_status()
                    
                    if health_status['status'] == 'critical':
                        logger.warning("Service health check shows critical status")
                
                # Sleep for health check interval
                import time
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
        finally:
            self.stop()
    
    def _write_pid_file(self):
        """Write PID file."""
        try:
            pid_path = Path(self.pid_file)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(pid_path, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"PID file written: {self.pid_file}")
            
        except Exception as e:
            logger.warning(f"Failed to write PID file: {e}")
    
    def _remove_pid_file(self):
        """Remove PID file."""
        try:
            pid_path = Path(self.pid_file)
            if pid_path.exists():
                pid_path.unlink()
                logger.info("PID file removed")
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")
    
    def status(self) -> Dict[str, Any]:
        """Get service status."""
        status_info = {
            "service_running": self.running,
            "pid": os.getpid() if self.running else None,
            "config_file": self.config_file,
            "log_file": self.log_file,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.scheduler:
            status_info["scheduler"] = self.scheduler.get_status()
        
        if self.monitor:
            status_info["monitoring"] = self.monitor.get_health_status()
        
        return status_info
    
    def trigger_rebuild(self) -> str:
        """Trigger manual rebuild."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not running")
        
        event_id = self.scheduler.trigger_manual_rebuild("service_api")
        logger.info(f"Manual rebuild triggered: {event_id}")
        return event_id

def create_systemd_service_file(config_file: str = "/etc/faiss-rebuild/config.json") -> str:
    """Generate systemd service file content."""
    service_content = f"""[Unit]
Description=FAISS Index Rebuild Service
Documentation=https://github.com/your-org/adelaide-weather-final
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=faiss-rebuild
Group=faiss-rebuild
WorkingDirectory={project_root}
Environment=PYTHONPATH={project_root}
ExecStart=/usr/bin/python3 {project_root}/scripts/faiss_rebuild_service.py --config {config_file} start
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths={project_root}/logs {project_root}/indices /var/log/faiss-rebuild /var/run

# Resource limits
MemoryLimit=8G
CPUQuota=200%
TasksMax=100

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=faiss-rebuild

[Install]
WantedBy=multi-user.target
"""
    return service_content

def create_default_config() -> Dict[str, Any]:
    """Create default configuration."""
    return {
        "scheduler": {
            "rebuild_schedule": "0 2 * * 0",  # Weekly at 2 AM Sunday
            "timezone": "UTC",
            "max_rebuild_duration_hours": 4,
            "enable_notifications": True,
            "notification_channels": ["log", "email"],
            "log_level": "INFO",
            "log_file": "/var/log/faiss-rebuild/scheduler.log"
        },
        "monitoring": {
            "enable_prometheus": True,
            "metrics_port": 9100,
            "health_check_port": 8080,
            "integrate_with_existing_monitoring": True,
            "export_to_grafana": True
        }
    }

def install_service(config_file: str = "/etc/faiss-rebuild/config.json"):
    """Install the service on the system."""
    print("Installing FAISS Rebuild Service...")
    
    try:
        # Create service user
        import subprocess
        
        # Create user if it doesn't exist
        try:
            subprocess.run(['id', 'faiss-rebuild'], check=True, capture_output=True)
            print("Service user 'faiss-rebuild' already exists")
        except subprocess.CalledProcessError:
            subprocess.run([
                'sudo', 'useradd', '-r', '-s', '/bin/false', 
                '-d', '/var/lib/faiss-rebuild', 'faiss-rebuild'
            ], check=True)
            print("Created service user 'faiss-rebuild'")
        
        # Create config directory
        config_dir = Path(config_file).parent
        subprocess.run(['sudo', 'mkdir', '-p', str(config_dir)], check=True)
        
        # Create default config if it doesn't exist
        if not Path(config_file).exists():
            default_config = create_default_config()
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            subprocess.run(['sudo', 'chown', 'faiss-rebuild:faiss-rebuild', config_file], check=True)
            print(f"Created default config: {config_file}")
        
        # Create log directories
        log_dirs = ['/var/log/faiss-rebuild', '/var/lib/faiss-rebuild']
        for log_dir in log_dirs:
            subprocess.run(['sudo', 'mkdir', '-p', log_dir], check=True)
            subprocess.run(['sudo', 'chown', 'faiss-rebuild:faiss-rebuild', log_dir], check=True)
        
        # Create systemd service file
        service_content = create_systemd_service_file(config_file)
        service_file = '/etc/systemd/system/faiss-rebuild.service'
        
        with open('/tmp/faiss-rebuild.service', 'w') as f:
            f.write(service_content)
        
        subprocess.run(['sudo', 'mv', '/tmp/faiss-rebuild.service', service_file], check=True)
        print(f"Created systemd service: {service_file}")
        
        # Reload systemd
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'faiss-rebuild'], check=True)
        
        print("✅ Service installed successfully")
        print(f"Configuration: {config_file}")
        print("Start with: sudo systemctl start faiss-rebuild")
        print("Status with: sudo systemctl status faiss-rebuild")
        print("Logs with: sudo journalctl -u faiss-rebuild -f")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Installation error: {e}")
        sys.exit(1)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='FAISS Rebuild Service')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'install', 'config'],
                       help='Action to perform')
    parser.add_argument('--config', default='/etc/faiss-rebuild/config.json',
                       help='Configuration file path')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (for systemd)')
    
    args = parser.parse_args()
    
    if args.action == 'install':
        install_service(args.config)
        return
    
    elif args.action == 'config':
        default_config = create_default_config()
        print("Default Configuration:")
        print(json.dumps(default_config, indent=2))
        return
    
    # Initialize service
    service = FAISSRebuildService(args.config)
    
    if args.action == 'start':
        try:
            service.start()
        except KeyboardInterrupt:
            logger.info("Service interrupted")
        except Exception as e:
            logger.error(f"Service failed: {e}")
            sys.exit(1)
    
    elif args.action == 'stop':
        service.stop()
    
    elif args.action == 'status':
        status = service.status()
        print("Service Status:")
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()