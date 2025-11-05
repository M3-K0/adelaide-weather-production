#!/usr/bin/env python3
"""
Test Suite for Configuration Drift Detection System
==================================================

Comprehensive tests for the ConfigurationDriftDetector including:
- Real-time file monitoring and drift detection
- Environment variable consistency validation
- Severity assessment and drift categorization
- Cross-environment configuration comparison
- Production-grade monitoring capabilities

This test suite validates all core functionality and integration
with the Adelaide weather forecasting system infrastructure.
"""

import os
import sys
import tempfile
import shutil
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config_drift_detector import (
    ConfigurationDriftDetector,
    DriftSeverity,
    DriftType,
    DriftEvent,
    ConfigurationSnapshot
)

class TestConfigurationDriftDetector(unittest.TestCase):
    """Test suite for configuration drift detection system."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_project_root = self.temp_dir / "test_project"
        self.test_project_root.mkdir(parents=True)
        
        # Create test directory structure
        self._create_test_directory_structure()
        
        # Initialize detector with test directory
        self.detector = ConfigurationDriftDetector(
            project_root=self.test_project_root,
            baseline_retention_days=1,
            check_interval_seconds=1,
            enable_real_time=False  # Disable for most tests
        )
        
        # Store original environment
        self.original_env = dict(os.environ)
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop monitoring if active
        if hasattr(self.detector, 'monitoring_active') and self.detector.monitoring_active:
            self.detector.stop_monitoring()
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Remove temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_directory_structure(self):
        """Create realistic test directory structure."""
        # Create configs directory with sample files
        configs_dir = self.test_project_root / "configs"
        configs_dir.mkdir()
        
        # Sample data.yaml
        data_config = {
            'adelaide': {'lat': -34.9, 'lon': 138.6},
            'era5': {
                'variables': ['temperature', 'pressure'],
                'years': [2020, 2021]
            },
            'preprocessing': {'normalize_method': 'zscore'}
        }
        
        with open(configs_dir / "data.yaml", 'w') as f:
            import yaml
            yaml.dump(data_config, f)
        
        # Sample model.yaml
        model_config = {
            'encoder': {
                'input_shape': [16, 16, 9],
                'embedding_dim': 256
            },
            'training': {
                'batch_size': 128,
                'learning_rate': 0.0003
            },
            'faiss': {
                'index_type': 'IndexFlatIP',
                'num_analogs': 30
            }
        }
        
        with open(configs_dir / "model.yaml", 'w') as f:
            yaml.dump(model_config, f)
        
        # Create .env file
        env_content = """API_TOKEN=test-token-12345
API_BASE_URL=http://localhost:8000
ENVIRONMENT=test
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=60
"""
        with open(self.test_project_root / ".env", 'w') as f:
            f.write(env_content)
        
        # Create docker-compose.yml
        docker_compose = {
            'version': '3.8',
            'services': {
                'api': {
                    'build': '.',
                    'ports': ['8000:8000']
                }
            }
        }
        
        with open(self.test_project_root / "docker-compose.yml", 'w') as f:
            yaml.dump(docker_compose, f)
        
        # Create monitoring directory
        monitoring_dir = self.test_project_root / "monitoring"
        monitoring_dir.mkdir()
        
        prometheus_config = {
            'global': {'scrape_interval': '15s'},
            'scrape_configs': [{
                'job_name': 'adelaide-weather',
                'static_configs': [{'targets': ['localhost:8000']}]
            }]
        }
        
        with open(monitoring_dir / "prometheus.yml", 'w') as f:
            yaml.dump(prometheus_config, f)
    
    def test_drift_severity_enum(self):
        """Test DriftSeverity enum functionality."""
        # Test string conversion
        self.assertEqual(str(DriftSeverity.LOW), "low")
        self.assertEqual(str(DriftSeverity.CRITICAL), "critical")
        
        # Test priority ordering
        self.assertLess(DriftSeverity.LOW.get_priority(), DriftSeverity.HIGH.get_priority())
        self.assertLess(DriftSeverity.HIGH.get_priority(), DriftSeverity.CRITICAL.get_priority())
        
        # Test all severity levels
        severities = [DriftSeverity.LOW, DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        priorities = [s.get_priority() for s in severities]
        self.assertEqual(priorities, sorted(priorities))
    
    def test_drift_type_enum(self):
        """Test DriftType enum functionality."""
        # Test string conversion
        self.assertEqual(str(DriftType.FILE_CHANGE), "file_change")
        self.assertEqual(str(DriftType.ENV_MISMATCH), "environment_mismatch")
        
        # Test all drift types are defined
        expected_types = [
            "file_change", "environment_mismatch", "schema_violation",
            "unauthorized_access", "baseline_deviation", "cross_environment",
            "security_drift", "dependency_mismatch"
        ]
        
        actual_types = [str(dt) for dt in DriftType]
        for expected in expected_types:
            self.assertIn(expected, actual_types)
    
    def test_drift_event_creation(self):
        """Test DriftEvent creation and serialization."""
        event = DriftEvent(
            event_id="test_event_123",
            drift_type=DriftType.FILE_CHANGE,
            severity=DriftSeverity.HIGH,
            source_path="configs/data.yaml",
            description="Configuration file modified",
            detected_at=datetime.now().isoformat(),
            old_value="old_hash",
            new_value="new_hash",
            metadata={"test": True}
        )
        
        # Test basic properties
        self.assertEqual(event.event_id, "test_event_123")
        self.assertEqual(event.drift_type, DriftType.FILE_CHANGE)
        self.assertEqual(event.severity, DriftSeverity.HIGH)
        self.assertFalse(event.resolved)
        
        # Test serialization
        event_dict = event.to_dict()
        self.assertEqual(event_dict['event_id'], "test_event_123")
        self.assertEqual(event_dict['drift_type'], "file_change")
        self.assertEqual(event_dict['severity'], "high")
        
        # Test critical detection
        critical_event = DriftEvent(
            event_id="critical_test",
            drift_type=DriftType.SECURITY_DRIFT,
            severity=DriftSeverity.CRITICAL,
            source_path="test",
            description="Critical issue",
            detected_at=datetime.now().isoformat()
        )
        
        self.assertTrue(critical_event.is_critical())
        self.assertFalse(event.is_critical())
    
    def test_configuration_snapshot_creation(self):
        """Test configuration snapshot creation and comparison."""
        # Set up environment variables
        os.environ['API_TOKEN'] = 'test-token'
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # Create initial snapshot
        snapshot1 = self.detector._create_configuration_snapshot("test1")
        
        # Verify snapshot structure
        self.assertIsInstance(snapshot1.snapshot_id, str)
        self.assertIsInstance(snapshot1.timestamp, str)
        self.assertIsInstance(snapshot1.file_hashes, dict)
        self.assertIsInstance(snapshot1.environment_vars, dict)
        
        # Check that configuration files are captured
        self.assertGreater(len(snapshot1.file_hashes), 0)
        
        # Check environment variables are captured
        self.assertIn('API_TOKEN', snapshot1.environment_vars)
        self.assertEqual(snapshot1.environment_vars['API_TOKEN'], 'test-token')
        
        # Modify a file and create second snapshot
        config_file = self.test_project_root / "configs" / "data.yaml"
        with open(config_file, 'a') as f:
            f.write("\n# Modified for testing\n")
        
        snapshot2 = self.detector._create_configuration_snapshot("test2")
        
        # Compare snapshots
        drift_events = snapshot2.compare_with(snapshot1)
        
        # Should detect file change
        file_change_events = [e for e in drift_events if e.drift_type == DriftType.FILE_CHANGE]
        self.assertGreater(len(file_change_events), 0)
        
        # Check the specific file that changed
        data_yaml_events = [e for e in file_change_events if 'data.yaml' in e.source_path]
        self.assertEqual(len(data_yaml_events), 1)
        
        event = data_yaml_events[0]
        self.assertEqual(event.drift_type, DriftType.FILE_CHANGE)
        self.assertIn('data.yaml', event.source_path)
        self.assertNotEqual(event.old_value, event.new_value)
    
    def test_environment_variable_drift_detection(self):
        """Test environment variable drift detection."""
        # Set initial environment
        os.environ['API_TOKEN'] = 'initial-token'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        snapshot1 = self.detector._create_configuration_snapshot("env_test1")
        
        # Change environment variable
        os.environ['API_TOKEN'] = 'changed-token'
        
        snapshot2 = self.detector._create_configuration_snapshot("env_test2")
        
        # Compare snapshots
        drift_events = snapshot2.compare_with(snapshot1)
        
        # Should detect environment variable change
        env_events = [e for e in drift_events if e.drift_type == DriftType.ENV_MISMATCH]
        self.assertGreater(len(env_events), 0)
        
        # Find the API_TOKEN change event
        token_events = [e for e in env_events if 'API_TOKEN' in e.source_path]
        self.assertEqual(len(token_events), 1)
        
        event = token_events[0]
        self.assertEqual(event.drift_type, DriftType.ENV_MISMATCH)
        self.assertEqual(event.severity, DriftSeverity.CRITICAL)  # API_TOKEN is critical
        
        # Check value masking for sensitive variables
        self.assertIn('*', event.old_value)  # Should be masked
        self.assertIn('*', event.new_value)  # Should be masked
    
    def test_severity_assessment(self):
        """Test configuration drift severity assessment."""
        # Test file-based severity assessment
        test_cases = [
            ("docker-compose.yml", DriftSeverity.CRITICAL),
            ("configs/model.yaml", DriftSeverity.HIGH),
            ("configs/data.yaml", DriftSeverity.HIGH),
            (".env.production", DriftSeverity.CRITICAL),
            (".env", DriftSeverity.MEDIUM),
            ("monitoring/prometheus.yml", DriftSeverity.HIGH),
            ("some_random_file.txt", DriftSeverity.LOW)
        ]
        
        snapshot = ConfigurationSnapshot(
            snapshot_id="test",
            timestamp=datetime.now().isoformat(),
            file_hashes={},
            environment_vars={},
            schema_validation={}
        )
        
        for file_path, expected_severity in test_cases:
            severity = snapshot._determine_file_change_severity(file_path)
            self.assertEqual(severity, expected_severity, 
                           f"File {file_path} should have severity {expected_severity}, got {severity}")
        
        # Test environment variable severity assessment
        env_test_cases = [
            ("API_TOKEN", DriftSeverity.CRITICAL),
            ("SECRET_KEY", DriftSeverity.CRITICAL),
            ("ENVIRONMENT", DriftSeverity.HIGH),
            ("LOG_LEVEL", DriftSeverity.HIGH),
            ("API_BASE_URL", DriftSeverity.MEDIUM),
            ("SOME_RANDOM_VAR", DriftSeverity.LOW)
        ]
        
        for env_var, expected_severity in env_test_cases:
            severity = snapshot._determine_env_change_severity(env_var)
            self.assertEqual(severity, expected_severity,
                           f"Environment variable {env_var} should have severity {expected_severity}, got {severity}")
    
    def test_schema_validation(self):
        """Test configuration schema validation."""
        # Valid configuration should pass
        validation_results = self.detector._validate_configuration_schemas()
        
        # Check that validation ran for expected files
        expected_configs = ["configs/data.yaml", "configs/model.yaml"]
        for config in expected_configs:
            if Path(self.test_project_root / config).exists():
                self.assertIn(config, validation_results)
                self.assertTrue(validation_results[config])
        
        # Test invalid configuration
        invalid_config = self.test_project_root / "configs" / "invalid.yaml"
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should handle invalid YAML gracefully
        # This would be caught in the validation process
    
    def test_drift_detection_workflow(self):
        """Test complete drift detection workflow."""
        # Set up environment
        os.environ['API_TOKEN'] = 'workflow-test-token'
        os.environ['LOG_LEVEL'] = 'INFO'
        
        # Start monitoring (without real-time for testing)
        success = self.detector.start_monitoring()
        self.assertTrue(success)
        
        # Verify baseline snapshot created
        self.assertIsNotNone(self.detector.baseline_snapshot)
        
        # Perform initial drift detection
        initial_events = self.detector.detect_drift(generate_report=False)
        
        # Should have no drift initially
        self.assertEqual(len(initial_events), 0)
        
        # Make some changes
        # 1. Modify configuration file
        config_file = self.test_project_root / "configs" / "model.yaml"
        with open(config_file, 'a') as f:
            f.write("\n# Test modification\ntest_param: 123\n")
        
        # 2. Change environment variable
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # 3. Create invalid configuration
        with open(self.test_project_root / "configs" / "broken.yaml", 'w') as f:
            f.write("broken: yaml: [invalid")
        
        # Detect drift
        drift_events = self.detector.detect_drift(generate_report=True)
        
        # Should detect changes
        self.assertGreater(len(drift_events), 0)
        
        # Verify different types of drift are detected
        drift_types = [e.drift_type for e in drift_events]
        
        # Should have file changes
        self.assertIn(DriftType.FILE_CHANGE, drift_types)
        
        # Check that events are stored
        self.assertGreater(len(self.detector.drift_events), 0)
        
        # Stop monitoring
        self.detector.stop_monitoring()
        self.assertFalse(self.detector.monitoring_active)
    
    def test_drift_report_generation(self):
        """Test drift report generation and filtering."""
        # Create test drift events
        test_events = [
            DriftEvent(
                event_id="test1",
                drift_type=DriftType.FILE_CHANGE,
                severity=DriftSeverity.HIGH,
                source_path="configs/data.yaml",
                description="Data config changed",
                detected_at=datetime.now().isoformat()
            ),
            DriftEvent(
                event_id="test2",
                drift_type=DriftType.ENV_MISMATCH,
                severity=DriftSeverity.CRITICAL,
                source_path="ENV:API_TOKEN",
                description="API token changed",
                detected_at=datetime.now().isoformat()
            ),
            DriftEvent(
                event_id="test3",
                drift_type=DriftType.SCHEMA_VIOLATION,
                severity=DriftSeverity.MEDIUM,
                source_path="configs/invalid.yaml",
                description="Schema violation",
                detected_at=(datetime.now() - timedelta(hours=2)).isoformat()
            )
        ]
        
        self.detector.drift_events = test_events
        
        # Generate full report
        report = self.detector.get_drift_report()
        
        # Verify report structure
        self.assertIn('report_generated_at', report)
        self.assertIn('monitoring_status', report)
        self.assertIn('drift_summary', report)
        self.assertIn('drift_types', report)
        self.assertIn('affected_sources', report)
        self.assertIn('recent_events', report)
        self.assertIn('critical_issues', report)
        self.assertIn('recommendations', report)
        
        # Check drift summary
        summary = report['drift_summary']
        self.assertEqual(summary['total_events'], 3)
        self.assertEqual(summary['critical_events'], 1)
        self.assertEqual(summary['high_events'], 1)
        self.assertEqual(summary['medium_events'], 1)
        
        # Test severity filtering
        critical_report = self.detector.get_drift_report(severity_filter=DriftSeverity.CRITICAL)
        self.assertEqual(critical_report['drift_summary']['total_events'], 1)
        
        # Test time filtering
        recent_report = self.detector.get_drift_report(hours_back=1)
        self.assertEqual(recent_report['drift_summary']['total_events'], 2)  # Excludes 2-hour-old event
        
        # Check critical issues section
        critical_issues = report['critical_issues']
        self.assertEqual(len(critical_issues), 1)
        self.assertEqual(critical_issues[0]['event_id'], 'test2')
    
    def test_drift_event_resolution(self):
        """Test drift event resolution functionality."""
        # Create test event
        test_event = DriftEvent(
            event_id="resolution_test",
            drift_type=DriftType.FILE_CHANGE,
            severity=DriftSeverity.HIGH,
            source_path="test_file.yaml",
            description="Test event for resolution",
            detected_at=datetime.now().isoformat()
        )
        
        self.detector.drift_events = [test_event]
        
        # Verify event is not resolved initially
        self.assertFalse(test_event.resolved)
        self.assertIsNone(test_event.resolution_notes)
        
        # Resolve the event
        success = self.detector.resolve_drift_event("resolution_test", "Fixed by updating configuration")
        self.assertTrue(success)
        
        # Verify event is marked as resolved
        self.assertTrue(test_event.resolved)
        self.assertEqual(test_event.resolution_notes, "Fixed by updating configuration")
        
        # Test resolving non-existent event
        success = self.detector.resolve_drift_event("non_existent", "Should fail")
        self.assertFalse(success)
    
    def test_baseline_update(self):
        """Test baseline configuration update."""
        # Start monitoring to create initial baseline
        self.detector.start_monitoring()
        initial_baseline = self.detector.baseline_snapshot
        self.assertIsNotNone(initial_baseline)
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.01)
        
        # Update baseline
        success = self.detector.update_baseline()
        self.assertTrue(success)
        
        # Verify new baseline is different
        new_baseline = self.detector.baseline_snapshot
        self.assertNotEqual(initial_baseline.snapshot_id, new_baseline.snapshot_id)
        self.assertNotEqual(initial_baseline.timestamp, new_baseline.timestamp)
        
        self.detector.stop_monitoring()
    
    def test_file_monitoring_patterns(self):
        """Test file monitoring pattern matching."""
        # Test files that should be monitored
        monitored_files = [
            "configs/data.yaml",
            "configs/model.yml", 
            ".env",
            ".env.production",
            "docker-compose.yml",
            "monitoring/prometheus.yml",
            "package.json"
        ]
        
        for file_path in monitored_files:
            self.assertTrue(self.detector._is_monitored_file(file_path),
                          f"File {file_path} should be monitored")
        
        # Test files that should NOT be monitored
        excluded_files = [
            "node_modules/package.json",
            ".git/config",
            "__pycache__/module.py",
            "venv/lib/python3.11/site-packages/package.json",
            "build/output.log",
            "dist/bundle.js",
            ".next/static/chunks/main.js"
        ]
        
        for file_path in excluded_files:
            self.assertFalse(self.detector._is_monitored_file(file_path),
                           f"File {file_path} should NOT be monitored")
    
    def test_security_drift_detection(self):
        """Test security-related drift detection."""
        # Set up insecure environment variables
        os.environ['API_TOKEN'] = 'test123'  # Obviously insecure
        os.environ['SECRET_KEY'] = 'password'  # Obviously insecure
        os.environ['DATABASE_URL'] = 'localhost:5432'  # Contains localhost
        
        # Create snapshot
        snapshot = self.detector._create_configuration_snapshot("security_test")
        
        # Detect security drift
        security_events = self.detector._detect_security_drift(snapshot)
        
        # Should detect multiple security issues
        self.assertGreater(len(security_events), 0)
        
        # All should be security drift type
        for event in security_events:
            self.assertEqual(event.drift_type, DriftType.SECURITY_DRIFT)
            self.assertEqual(event.severity, DriftSeverity.CRITICAL)
    
    def test_real_time_monitoring_setup(self):
        """Test real-time monitoring setup and teardown."""
        # Create detector with real-time monitoring enabled
        realtime_detector = ConfigurationDriftDetector(
            project_root=self.test_project_root,
            enable_real_time=True,
            check_interval_seconds=1
        )
        
        try:
            # Start monitoring
            success = realtime_detector.start_monitoring()
            self.assertTrue(success)
            self.assertTrue(realtime_detector.monitoring_active)
            
            # Verify observer is set up
            self.assertIsNotNone(realtime_detector.observer)
            self.assertIsNotNone(realtime_detector.file_handler)
            self.assertIsNotNone(realtime_detector.monitoring_thread)
            
            # Give monitoring thread a moment to start
            time.sleep(0.1)
            
        finally:
            # Stop monitoring
            realtime_detector.stop_monitoring()
            self.assertFalse(realtime_detector.monitoring_active)
    
    def test_performance_and_scalability(self):
        """Test performance characteristics and scalability."""
        # Create many configuration files
        configs_dir = self.test_project_root / "configs"
        for i in range(50):
            config_file = configs_dir / f"config_{i}.yaml"
            with open(config_file, 'w') as f:
                f.write(f"test_config_{i}:\n  value: {i}\n")
        
        # Measure snapshot creation time
        start_time = time.time()
        snapshot = self.detector._create_configuration_snapshot("performance_test")
        snapshot_time = time.time() - start_time
        
        # Should complete reasonably quickly (under 5 seconds even with many files)
        self.assertLess(snapshot_time, 5.0)
        
        # Should capture all configuration files
        self.assertGreaterEqual(len(snapshot.file_hashes), 50)
        
        # Test drift detection performance
        start_time = time.time()
        drift_events = self.detector.detect_drift(generate_report=False)
        detection_time = time.time() - start_time
        
        # Should complete quickly
        self.assertLess(detection_time, 2.0)

class TestIntegrationWithExistingSystem(unittest.TestCase):
    """Integration tests with existing Adelaide weather system components."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.project_root = Path("/home/micha/adelaide-weather-final")
        
        # Only run integration tests if in actual project directory
        if not self.project_root.exists():
            self.skipTest("Adelaide weather project directory not found")
    
    def test_integration_with_existing_configs(self):
        """Test integration with existing configuration files."""
        detector = ConfigurationDriftDetector(
            project_root=self.project_root,
            enable_real_time=False
        )
        
        # Should be able to create snapshot of existing system
        snapshot = detector._create_configuration_snapshot("integration_test")
        
        # Should find existing configuration files
        self.assertGreater(len(snapshot.file_hashes), 0)
        
        # Should validate existing schemas
        validation_results = snapshot.schema_validation
        self.assertIsInstance(validation_results, dict)
    
    def test_integration_with_health_validator(self):
        """Test integration with existing system health validator."""
        try:
            from core.system_health_validator import ProductionHealthValidator
            
            # Both systems should be able to coexist
            health_validator = ProductionHealthValidator(self.project_root)
            drift_detector = ConfigurationDriftDetector(
                project_root=self.project_root,
                enable_real_time=False
            )
            
            # Both should be able to operate on the same project
            self.assertEqual(health_validator.project_root, drift_detector.project_root)
            
        except ImportError:
            self.skipTest("System health validator not available")

def run_comprehensive_tests():
    """Run comprehensive test suite with detailed reporting."""
    print("🧪 Starting Configuration Drift Detector Test Suite")
    print("=" * 80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationDriftDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWithExistingSystem))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"   {test}: {failure}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, error in result.errors:
            print(f"   {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"🚀 Configuration Drift Detector is ready for production!")
    else:
        print(f"\n❌ SOME TESTS FAILED!")
        print(f"🔧 Fix issues before deploying to production.")
    
    return success

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)