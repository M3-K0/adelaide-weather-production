#!/usr/bin/env python3
"""
FAISS Index Automation Integration Test
======================================

Integration test for the FAISS index automation system to validate all components
work together correctly.

Author: ML Infrastructure Team
Version: 1.0.0 - T-015 FAISS Index Automation
"""

import os
import sys
import json
import time
import tempfile
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.faiss_index_rebuilder import FAISSIndexRebuilder, RebuildConfig
from core.faiss_rebuild_scheduler import FAISSRebuildScheduler, SchedulerConfig
from core.faiss_rebuild_monitoring import FAISSRebuildMonitor, MonitoringConfig

logger = logging.getLogger(__name__)

class FAISSAutomationIntegrationTest:
    """Integration test for FAISS automation system."""
    
    def __init__(self):
        self.project_root = Path("/home/micha/adelaide-weather-final")
        self.test_dir = None
        self.passed_tests = 0
        self.failed_tests = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_test_environment(self):
        """Setup test environment."""
        print("🔧 Setting up test environment...")
        
        # Create temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp(prefix="faiss_automation_test_"))
        
        # Create required directories
        (self.test_dir / "indices").mkdir()
        (self.test_dir / "embeddings").mkdir()
        (self.test_dir / "logs").mkdir()
        
        print(f"✅ Test environment created: {self.test_dir}")
    
    def cleanup_test_environment(self):
        """Cleanup test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"🧹 Test environment cleaned up: {self.test_dir}")
    
    def test_rebuild_config(self):
        """Test rebuild configuration."""
        print("\n📋 Testing rebuild configuration...")
        
        try:
            # Test default config
            config = RebuildConfig()
            assert config.horizons == [6, 12, 24, 48], "Default horizons incorrect"
            assert config.index_types == ['flatip', 'ivfpq'], "Default index types incorrect"
            assert config.validation_enabled is True, "Validation should be enabled by default"
            
            # Test custom config
            custom_config = RebuildConfig(
                horizons=[6, 24],
                validation_enabled=False,
                max_backups=10
            )
            assert custom_config.horizons == [6, 24], "Custom horizons not set"
            assert custom_config.validation_enabled is False, "Validation not disabled"
            assert custom_config.max_backups == 10, "Max backups not set"
            
            print("✅ Rebuild configuration test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Rebuild configuration test failed: {e}")
            self.failed_tests += 1
    
    def test_scheduler_config(self):
        """Test scheduler configuration."""
        print("\n⏰ Testing scheduler configuration...")
        
        try:
            # Test default config
            config = SchedulerConfig()
            assert config.rebuild_schedule == "0 2 * * 0", "Default schedule incorrect"
            assert config.max_consecutive_failures == 3, "Default failure threshold incorrect"
            
            # Test custom config
            custom_config = SchedulerConfig(
                rebuild_schedule="0 1 * * 1",  # Monday 1 AM
                max_consecutive_failures=5,
                notification_channels=['slack', 'email']
            )
            assert custom_config.rebuild_schedule == "0 1 * * 1", "Custom schedule not set"
            assert custom_config.max_consecutive_failures == 5, "Custom failure threshold not set"
            assert 'slack' in custom_config.notification_channels, "Slack notifications not enabled"
            
            print("✅ Scheduler configuration test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Scheduler configuration test failed: {e}")
            self.failed_tests += 1
    
    def test_monitoring_config(self):
        """Test monitoring configuration."""
        print("\n📊 Testing monitoring configuration...")
        
        try:
            # Test default config
            config = MonitoringConfig()
            assert config.enable_prometheus is True, "Prometheus should be enabled by default"
            assert config.metrics_port == 9100, "Default metrics port incorrect"
            assert config.health_check_port == 8080, "Default health port incorrect"
            
            # Test custom config
            custom_config = MonitoringConfig(
                metrics_port=9200,
                health_check_port=8888,
                max_rebuild_duration_minutes=300.0
            )
            assert custom_config.metrics_port == 9200, "Custom metrics port not set"
            assert custom_config.health_check_port == 8888, "Custom health port not set"
            assert custom_config.max_rebuild_duration_minutes == 300.0, "Custom duration not set"
            
            print("✅ Monitoring configuration test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Monitoring configuration test failed: {e}")
            self.failed_tests += 1
    
    def test_rebuilder_initialization(self):
        """Test rebuilder initialization."""
        print("\n🔨 Testing rebuilder initialization...")
        
        try:
            config = RebuildConfig(
                embeddings_dir=str(self.test_dir / "embeddings"),
                indices_dir=str(self.test_dir / "indices"),
                backup_dir=str(self.test_dir / "backups"),
                staging_dir=str(self.test_dir / "staging")
            )
            
            rebuilder = FAISSIndexRebuilder(config, self.test_dir)
            
            # Check initialization
            assert rebuilder.config == config, "Config not set correctly"
            assert rebuilder.indices_dir == self.test_dir / "indices", "Indices dir not set"
            assert rebuilder.staging_dir == self.test_dir / "staging", "Staging dir not set"
            
            # Check status
            status = rebuilder.get_rebuild_status()
            assert not status['rebuild_in_progress'], "Should not have rebuild in progress"
            assert status['current_rebuild_id'] is None, "Should not have current rebuild ID"
            
            print("✅ Rebuilder initialization test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Rebuilder initialization test failed: {e}")
            self.failed_tests += 1
    
    def test_backup_manager(self):
        """Test backup manager functionality."""
        print("\n📦 Testing backup manager...")
        
        try:
            config = RebuildConfig(
                backup_dir=str(self.test_dir / "backups"),
                max_backups=3
            )
            
            rebuilder = FAISSIndexRebuilder(config, self.test_dir)
            
            # Create some dummy index files
            indices_dir = self.test_dir / "indices"
            (indices_dir / "faiss_6h_flatip.faiss").write_text("dummy index data")
            (indices_dir / "faiss_12h_ivfpq.faiss").write_text("dummy index data")
            
            # Test backup creation
            backup_id = rebuilder.backup_manager.create_backup(indices_dir)
            assert backup_id is not None, "Backup ID should be returned"
            
            # Test backup listing
            backups = rebuilder.backup_manager.list_backups()
            assert len(backups) >= 1, "Should have at least one backup"
            assert any(b['backup_id'] == backup_id for b in backups), "Created backup should be listed"
            
            print("✅ Backup manager test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Backup manager test failed: {e}")
            self.failed_tests += 1
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        print("\n⏰ Testing scheduler initialization...")
        
        try:
            config = SchedulerConfig(
                log_file=str(self.test_dir / "logs" / "scheduler.log")
            )
            
            scheduler = FAISSRebuildScheduler(config, self.test_dir)
            
            # Check initialization
            assert scheduler.config == config, "Config not set correctly"
            assert not scheduler.running, "Scheduler should not be running initially"
            
            # Check status
            status = scheduler.get_status()
            assert not status['running'], "Status should show not running"
            assert status['consecutive_failures'] == 0, "Should start with no failures"
            
            print("✅ Scheduler initialization test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Scheduler initialization test failed: {e}")
            self.failed_tests += 1
    
    def test_monitoring_initialization(self):
        """Test monitoring initialization."""
        print("\n📊 Testing monitoring initialization...")
        
        try:
            config = MonitoringConfig()
            monitor = FAISSRebuildMonitor(config, self.test_dir)
            
            # Check health status
            health = monitor.get_health_status()
            assert 'status' in health, "Health status should have status field"
            assert 'timestamp' in health, "Health status should have timestamp"
            assert 'component' in health, "Health status should have component field"
            
            # Check alerts
            alerts = monitor.check_alerts()
            assert isinstance(alerts, list), "Alerts should be a list"
            
            print("✅ Monitoring initialization test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Monitoring initialization test failed: {e}")
            self.failed_tests += 1
    
    def test_cli_imports(self):
        """Test CLI imports and basic functionality."""
        print("\n💻 Testing CLI imports...")
        
        try:
            # Test that CLI modules can be imported
            from scripts.faiss_rebuild_cli import FAISSRebuildCLI
            from scripts.faiss_rebuild_service import FAISSRebuildService
            
            # Test CLI initialization
            cli = FAISSRebuildCLI(self.test_dir)
            assert cli.project_root == self.test_dir, "CLI project root not set correctly"
            
            print("✅ CLI imports test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ CLI imports test failed: {e}")
            self.failed_tests += 1
    
    def test_integration_with_existing_system(self):
        """Test integration with existing FAISS infrastructure."""
        print("\n🔗 Testing integration with existing system...")
        
        try:
            # Test that we can import existing components
            from api.services.analog_search import get_analog_search_service
            from core.startup_validation_system import ExpertValidatedStartupSystem
            
            # Test startup validation integration
            validator = ExpertValidatedStartupSystem(self.project_root)
            assert validator.project_root == self.project_root, "Validator project root incorrect"
            
            print("✅ Integration test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            self.failed_tests += 1
    
    def test_configuration_files(self):
        """Test configuration file handling."""
        print("\n📄 Testing configuration files...")
        
        try:
            # Test JSON serialization/deserialization
            config_dict = {
                "scheduler": {
                    "rebuild_schedule": "0 3 * * 0",
                    "max_consecutive_failures": 5
                },
                "monitoring": {
                    "enable_prometheus": False,
                    "metrics_port": 9200
                }
            }
            
            # Write config file
            config_file = self.test_dir / "test_config.json"
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            # Read and validate
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
            
            assert loaded_config == config_dict, "Config file round-trip failed"
            
            # Test config object creation
            scheduler_config = SchedulerConfig(**loaded_config['scheduler'])
            assert scheduler_config.rebuild_schedule == "0 3 * * 0", "Loaded schedule incorrect"
            
            monitoring_config = MonitoringConfig(**loaded_config['monitoring'])
            assert monitoring_config.enable_prometheus is False, "Loaded prometheus setting incorrect"
            
            print("✅ Configuration files test passed")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"❌ Configuration files test failed: {e}")
            self.failed_tests += 1
    
    def run_all_tests(self):
        """Run all integration tests."""
        print("🚀 Starting FAISS Automation Integration Tests")
        print("=" * 60)
        
        try:
            self.setup_test_environment()
            
            # Run all tests
            self.test_rebuild_config()
            self.test_scheduler_config()
            self.test_monitoring_config()
            self.test_rebuilder_initialization()
            self.test_backup_manager()
            self.test_scheduler_initialization()
            self.test_monitoring_initialization()
            self.test_cli_imports()
            self.test_integration_with_existing_system()
            self.test_configuration_files()
            
        finally:
            self.cleanup_test_environment()
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 All integration tests passed!")
            print("The FAISS Index Automation system is ready for deployment.")
            return True
        else:
            print(f"\n⚠️ {self.failed_tests} test(s) failed.")
            print("Please review and fix issues before deployment.")
            return False

def main():
    """Main test runner."""
    test_runner = FAISSAutomationIntegrationTest()
    success = test_runner.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())