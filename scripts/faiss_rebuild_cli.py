#!/usr/bin/env python3
"""
FAISS Rebuild CLI
================

Command-line interface for FAISS index rebuild operations, monitoring,
and maintenance tasks.

Features:
- Manual rebuild triggering
- Status monitoring
- Backup management
- Configuration management
- Health checks
- Log analysis
- Maintenance operations

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.faiss_index_rebuilder import FAISSIndexRebuilder, RebuildConfig
from core.faiss_rebuild_scheduler import FAISSRebuildScheduler, SchedulerConfig
from core.faiss_rebuild_monitoring import FAISSRebuildMonitor, MonitoringConfig

logger = logging.getLogger(__name__)

class FAISSRebuildCLI:
    """CLI interface for FAISS rebuild operations."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path("/home/micha/adelaide-weather-final")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def rebuild(self, args):
        """Execute manual rebuild."""
        print("🔨 Starting FAISS index rebuild...")
        
        # Load config
        config = RebuildConfig()
        if args.config:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
            config = RebuildConfig(**config_data)
        
        # Apply CLI overrides
        if args.horizons:
            config.horizons = args.horizons
        if args.skip_validation:
            config.validation_enabled = False
            config.require_validation_pass = False
        if args.skip_backup:
            # Note: This would require modifying RebuildConfig to have backup_enabled
            print("Warning: Backup skipping not implemented in RebuildConfig")
        
        # Initialize rebuilder
        rebuilder = FAISSIndexRebuilder(config, self.project_root)
        
        try:
            # Execute rebuild
            result = rebuilder.rebuild_all_indices(force=args.force)
            
            # Display results
            self._display_rebuild_result(result)
            
            return 0 if result.success else 1
            
        except KeyboardInterrupt:
            print("\n❌ Rebuild interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Rebuild failed: {e}")
            return 1
    
    def status(self, args):
        """Show rebuild system status."""
        print("📊 FAISS Rebuild System Status")
        print("=" * 50)
        
        try:
            # Rebuilder status
            config = RebuildConfig()
            rebuilder = FAISSIndexRebuilder(config, self.project_root)
            rebuild_status = rebuilder.get_rebuild_status()
            
            print(f"Rebuild in progress: {rebuild_status['rebuild_in_progress']}")
            if rebuild_status['current_rebuild_id']:
                print(f"Current rebuild ID: {rebuild_status['current_rebuild_id']}")
            
            print(f"Indices directory: {rebuild_status['indices_dir']}")
            print(f"Staging directory: {rebuild_status['staging_dir']}")
            
            # Check if scheduler is running (simplified check)
            scheduler_running = self._check_scheduler_running()
            print(f"Scheduler running: {scheduler_running}")
            
            # Show recent backups
            backups = rebuilder.list_available_backups()
            print(f"\nAvailable backups: {len(backups)}")
            for backup in backups[:5]:  # Show recent 5
                timestamp = backup.get('timestamp', 'unknown')
                backup_id = backup.get('backup_id', 'unknown')
                files = len(backup.get('files', []))
                print(f"  {backup_id}: {files} files ({timestamp})")
            
            # Index file status
            indices_dir = Path(rebuild_status['indices_dir'])
            if indices_dir.exists():
                index_files = list(indices_dir.glob("*.faiss"))
                print(f"\nCurrent index files: {len(index_files)}")
                for index_file in index_files:
                    size_mb = index_file.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(index_file.stat().st_mtime)
                    print(f"  {index_file.name}: {size_mb:.1f}MB (modified: {mtime.strftime('%Y-%m-%d %H:%M')})")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            return 1
    
    def backup(self, args):
        """Manage backups."""
        config = RebuildConfig()
        rebuilder = FAISSIndexRebuilder(config, self.project_root)
        
        if args.action == 'list':
            backups = rebuilder.list_available_backups()
            
            print(f"📦 Available Backups ({len(backups)})")
            print("=" * 50)
            
            for backup in backups:
                backup_id = backup.get('backup_id', 'unknown')
                timestamp = backup.get('timestamp', 'unknown')
                files = backup.get('files', [])
                size_mb = backup.get('total_size_mb', 0)
                
                print(f"ID: {backup_id}")
                print(f"  Timestamp: {timestamp}")
                print(f"  Files: {len(files)} ({', '.join(files[:3])}{'...' if len(files) > 3 else ''})")
                print(f"  Size: {size_mb:.1f}MB")
                print()
        
        elif args.action == 'create':
            try:
                backup_id = rebuilder.backup_manager.create_backup(rebuilder.indices_dir)
                print(f"✅ Backup created: {backup_id}")
                return 0
            except Exception as e:
                print(f"❌ Backup failed: {e}")
                return 1
        
        elif args.action == 'restore':
            if not args.backup_id:
                print("❌ Backup ID required for restore")
                return 1
            
            try:
                # Confirm restore
                if not args.force:
                    confirm = input(f"Restore backup '{args.backup_id}'? This will replace current indices. [y/N]: ")
                    if confirm.lower() != 'y':
                        print("Restore cancelled")
                        return 0
                
                success = rebuilder.backup_manager.restore_backup(args.backup_id, rebuilder.indices_dir)
                if success:
                    print(f"✅ Backup restored: {args.backup_id}")
                    return 0
                else:
                    print(f"❌ Restore failed")
                    return 1
                    
            except Exception as e:
                print(f"❌ Restore failed: {e}")
                return 1
        
        return 0
    
    def monitor(self, args):
        """Show monitoring information."""
        print("📈 FAISS Rebuild Monitoring")
        print("=" * 50)
        
        try:
            # Initialize monitor
            config = MonitoringConfig()
            monitor = FAISSRebuildMonitor(config, self.project_root)
            
            if args.health:
                health = monitor.get_health_status()
                print(f"Health Status: {health['status'].upper()}")
                print(f"Timestamp: {health['timestamp']}")
                print(f"Component: {health['component']}")
                
                if health['active_alerts']:
                    print(f"\nActive Alerts ({len(health['active_alerts'])}):")
                    for alert in health['active_alerts']:
                        severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(alert['severity'], "")
                        print(f"  {severity_emoji} {alert['name']}: {alert['description']}")
                else:
                    print("\n✅ No active alerts")
            
            elif args.metrics:
                metrics = monitor.get_metrics()
                if metrics:
                    print("Prometheus Metrics:")
                    print(metrics)
                else:
                    print("❌ Metrics not available")
            
            elif args.alerts:
                active_alerts = monitor.check_alerts()
                print(f"Active Alerts ({len(active_alerts)}):")
                for alert in active_alerts:
                    print(f"  {alert['severity'].upper()}: {alert['name']} - {alert['description']}")
                
                if not active_alerts:
                    print("✅ No active alerts")
            
            return 0
            
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            return 1
    
    def config(self, args):
        """Configuration management."""
        if args.action == 'show':
            config_types = {
                'rebuild': RebuildConfig(),
                'scheduler': SchedulerConfig(),
                'monitoring': MonitoringConfig()
            }
            
            for config_name, config_obj in config_types.items():
                print(f"\n{config_name.title()} Configuration:")
                print("-" * 30)
                config_dict = config_obj.__dict__
                print(json.dumps(config_dict, indent=2, default=str))
        
        elif args.action == 'validate':
            if not args.file:
                print("❌ Configuration file required")
                return 1
            
            try:
                with open(args.file, 'r') as f:
                    config_data = json.load(f)
                
                # Validate by trying to create config objects
                if 'rebuild' in config_data:
                    RebuildConfig(**config_data['rebuild'])
                    print("✅ Rebuild config valid")
                
                if 'scheduler' in config_data:
                    SchedulerConfig(**config_data['scheduler'])
                    print("✅ Scheduler config valid")
                
                if 'monitoring' in config_data:
                    MonitoringConfig(**config_data['monitoring'])
                    print("✅ Monitoring config valid")
                
                print("✅ Configuration file is valid")
                return 0
                
            except Exception as e:
                print(f"❌ Configuration validation failed: {e}")
                return 1
        
        return 0
    
    def maintenance(self, args):
        """Maintenance operations."""
        try:
            config = RebuildConfig()
            rebuilder = FAISSIndexRebuilder(config, self.project_root)
            
            if args.action == 'cleanup':
                print("🧹 Cleaning up staging directories...")
                rebuilder.cleanup_staging(keep_recent=args.keep_recent)
                print("✅ Cleanup completed")
            
            elif args.action == 'validate':
                print("🔍 Validating current indices...")
                
                # Use startup validation system
                from core.startup_validation_system import ExpertValidatedStartupSystem
                validator = ExpertValidatedStartupSystem(self.project_root)
                
                result = validator.validate_faiss_indices_expert()
                
                if result.is_passing():
                    print("✅ Index validation passed")
                    print(f"Message: {result.message}")
                else:
                    print("❌ Index validation failed")
                    print(f"Message: {result.message}")
                    return 1
            
            elif args.action == 'disk-usage':
                print("💾 Disk Usage Analysis")
                print("-" * 30)
                
                directories = {
                    'indices': rebuilder.indices_dir,
                    'staging': rebuilder.staging_dir,
                    'backups': Path(rebuilder.config.backup_dir)
                }
                
                for name, directory in directories.items():
                    if directory.exists():
                        total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
                        size_mb = total_size / (1024 * 1024)
                        file_count = len([f for f in directory.rglob('*') if f.is_file()])
                        print(f"{name.title()}: {size_mb:.1f}MB ({file_count} files)")
                    else:
                        print(f"{name.title()}: Directory not found")
            
            return 0
            
        except Exception as e:
            print(f"❌ Maintenance operation failed: {e}")
            return 1
    
    def _display_rebuild_result(self, result):
        """Display rebuild result in formatted way."""
        print("\n" + "=" * 50)
        print("REBUILD RESULT")
        print("=" * 50)
        
        status_emoji = "✅" if result.success else "❌"
        print(f"Status: {status_emoji} {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Rebuild ID: {result.rebuild_id}")
        print(f"Timestamp: {result.timestamp}")
        
        if result.success:
            print(f"Horizons processed: {result.horizons_processed}")
            print(f"Indices created: {len(result.indices_created)}")
            
            if result.metrics:
                total_time = result.metrics.get('total_time_seconds', 0)
                print(f"Total time: {total_time:.1f}s")
                
                if 'verification_results' in result.metrics:
                    verification = result.metrics['verification_results']
                    print(f"Verification: {'✅ PASSED' if verification.get('success') else '❌ FAILED'}")
            
            if result.validation_results:
                print(f"\nValidation Results:")
                for key, validation in result.validation_results.items():
                    if isinstance(validation, dict):
                        passed = validation.get('passed', False)
                        print(f"  {key}: {'✅ PASSED' if passed else '❌ FAILED'}")
            
            if result.backup_id:
                print(f"Backup ID: {result.backup_id}")
        
        else:
            print(f"Error: {result.error_message}")
            if result.rollback_performed:
                print("🔄 Rollback was performed")
    
    def _check_scheduler_running(self) -> bool:
        """Check if scheduler service is running."""
        try:
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'faiss-rebuild'], 
                                  capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip() == 'active'
        except:
            return False

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='FAISS Rebuild CLI')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Rebuild command
    rebuild_parser = subparsers.add_parser('rebuild', help='Execute manual rebuild')
    rebuild_parser.add_argument('--config', help='Rebuild config file')
    rebuild_parser.add_argument('--horizons', nargs='+', type=int, 
                               help='Horizons to rebuild (default: all)')
    rebuild_parser.add_argument('--skip-validation', action='store_true',
                               help='Skip validation (not recommended)')
    rebuild_parser.add_argument('--skip-backup', action='store_true',
                               help='Skip backup creation')
    rebuild_parser.add_argument('--force', action='store_true',
                               help='Force rebuild even if one is in progress')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup management')
    backup_parser.add_argument('action', choices=['list', 'create', 'restore'],
                              help='Backup action')
    backup_parser.add_argument('--backup-id', help='Backup ID for restore')
    backup_parser.add_argument('--force', action='store_true',
                              help='Force restore without confirmation')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitoring information')
    monitor_group = monitor_parser.add_mutually_exclusive_group()
    monitor_group.add_argument('--health', action='store_true', help='Show health status')
    monitor_group.add_argument('--metrics', action='store_true', help='Show metrics')
    monitor_group.add_argument('--alerts', action='store_true', help='Show alerts')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('action', choices=['show', 'validate'],
                              help='Config action')
    config_parser.add_argument('--file', help='Configuration file to validate')
    
    # Maintenance command
    maintenance_parser = subparsers.add_parser('maintenance', help='Maintenance operations')
    maintenance_parser.add_argument('action', choices=['cleanup', 'validate', 'disk-usage'],
                                   help='Maintenance action')
    maintenance_parser.add_argument('--keep-recent', type=int, default=3,
                                   help='Number of recent staging dirs to keep (default: 3)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize CLI
    cli = FAISSRebuildCLI()
    
    # Execute command
    try:
        if args.command == 'rebuild':
            return cli.rebuild(args)
        elif args.command == 'status':
            return cli.status(args)
        elif args.command == 'backup':
            return cli.backup(args)
        elif args.command == 'monitor':
            return cli.monitor(args)
        elif args.command == 'config':
            return cli.config(args)
        elif args.command == 'maintenance':
            return cli.maintenance(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted")
        return 1
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())