#!/usr/bin/env python3
"""
Simple Test for Configuration Drift Detection System
===================================================

Basic tests that verify core functionality without external dependencies.
Tests the essential components of the configuration drift detection system.
"""

import os
import sys
import tempfile
import shutil
import time
import json
from pathlib import Path
from datetime import datetime
import hashlib

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_enums():
    """Test the enum definitions."""
    try:
        from core.config_drift_detector import DriftSeverity, DriftType
        
        print("✅ Testing DriftSeverity enum...")
        
        # Test string conversion
        assert str(DriftSeverity.LOW) == "low"
        assert str(DriftSeverity.CRITICAL) == "critical"
        
        # Test priority ordering
        assert DriftSeverity.LOW.get_priority() < DriftSeverity.HIGH.get_priority()
        assert DriftSeverity.HIGH.get_priority() < DriftSeverity.CRITICAL.get_priority()
        
        print("✅ Testing DriftType enum...")
        
        # Test string conversion
        assert str(DriftType.FILE_CHANGE) == "file_change"
        assert str(DriftType.ENV_MISMATCH) == "environment_mismatch"
        
        # Test all drift types are defined
        expected_types = [
            "file_change", "environment_mismatch", "schema_violation",
            "unauthorized_access", "baseline_deviation", "cross_environment",
            "security_drift", "dependency_mismatch"
        ]
        
        actual_types = [str(dt) for dt in DriftType]
        for expected in expected_types:
            assert expected in actual_types
        
        print("✅ Enum tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Enum tests failed: {e}")
        return False

def test_drift_event():
    """Test DriftEvent functionality."""
    try:
        from core.config_drift_detector import DriftEvent, DriftType, DriftSeverity
        
        print("✅ Testing DriftEvent creation...")
        
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
        assert event.event_id == "test_event_123"
        assert event.drift_type == DriftType.FILE_CHANGE
        assert event.severity == DriftSeverity.HIGH
        assert not event.resolved
        
        # Test serialization
        event_dict = event.to_dict()
        assert event_dict['event_id'] == "test_event_123"
        assert event_dict['drift_type'] == "file_change"
        assert event_dict['severity'] == "high"
        
        # Test critical detection
        critical_event = DriftEvent(
            event_id="critical_test",
            drift_type=DriftType.SECURITY_DRIFT,
            severity=DriftSeverity.CRITICAL,
            source_path="test",
            description="Critical issue",
            detected_at=datetime.now().isoformat()
        )
        
        assert critical_event.is_critical()
        assert not event.is_critical()
        
        print("✅ DriftEvent tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ DriftEvent tests failed: {e}")
        return False

def test_configuration_snapshot():
    """Test ConfigurationSnapshot functionality."""
    try:
        from core.config_drift_detector import ConfigurationSnapshot, DriftType
        
        print("✅ Testing ConfigurationSnapshot...")
        
        # Create test snapshots
        snapshot1 = ConfigurationSnapshot(
            snapshot_id="test1",
            timestamp=datetime.now().isoformat(),
            file_hashes={"file1.yaml": "hash1", "file2.yaml": "hash2"},
            environment_vars={"API_TOKEN": "token1", "LOG_LEVEL": "INFO"},
            schema_validation={"config1": True}
        )
        
        snapshot2 = ConfigurationSnapshot(
            snapshot_id="test2", 
            timestamp=datetime.now().isoformat(),
            file_hashes={"file1.yaml": "hash1_modified", "file2.yaml": "hash2"},
            environment_vars={"API_TOKEN": "token2", "LOG_LEVEL": "INFO"},
            schema_validation={"config1": True}
        )
        
        # Compare snapshots
        drift_events = snapshot2.compare_with(snapshot1)
        
        # Should detect file and environment changes
        assert len(drift_events) > 0
        
        # Check for file change events
        file_events = [e for e in drift_events if e.drift_type == DriftType.FILE_CHANGE]
        assert len(file_events) > 0
        
        # Check for environment change events
        env_events = [e for e in drift_events if e.drift_type == DriftType.ENV_MISMATCH]
        assert len(env_events) > 0
        
        print("✅ ConfigurationSnapshot tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ ConfigurationSnapshot tests failed: {e}")
        return False

def test_severity_assessment():
    """Test severity assessment logic."""
    try:
        from core.config_drift_detector import ConfigurationSnapshot, DriftSeverity
        
        print("✅ Testing severity assessment...")
        
        snapshot = ConfigurationSnapshot(
            snapshot_id="test",
            timestamp=datetime.now().isoformat(),
            file_hashes={},
            environment_vars={},
            schema_validation={}
        )
        
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
        
        for file_path, expected_severity in test_cases:
            severity = snapshot._determine_file_change_severity(file_path)
            assert severity == expected_severity, f"File {file_path} should have severity {expected_severity}, got {severity}"
        
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
            assert severity == expected_severity, f"Environment variable {env_var} should have severity {expected_severity}, got {severity}"
        
        print("✅ Severity assessment tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Severity assessment tests failed: {e}")
        return False

def test_file_monitoring_patterns():
    """Test file monitoring pattern logic without actual monitoring."""
    try:
        from core.config_drift_detector import ConfigurationDriftDetector
        import tempfile
        from pathlib import Path
        
        print("✅ Testing file monitoring patterns...")
        
        # Create temporary directory for testing
        temp_dir = Path(tempfile.mkdtemp())
        detector = ConfigurationDriftDetector(
            project_root=temp_dir,
            enable_real_time=False
        )
        
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
            assert detector._is_monitored_file(file_path), f"File {file_path} should be monitored"
        
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
            assert not detector._is_monitored_file(file_path), f"File {file_path} should NOT be monitored"
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
        print("✅ File monitoring pattern tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ File monitoring pattern tests failed: {e}")
        return False

def test_value_masking():
    """Test sensitive value masking functionality."""
    try:
        from core.config_drift_detector import ConfigurationSnapshot
        
        print("✅ Testing value masking...")
        
        snapshot = ConfigurationSnapshot(
            snapshot_id="test",
            timestamp=datetime.now().isoformat(),
            file_hashes={},
            environment_vars={},
            schema_validation={}
        )
        
        # Test masking of sensitive values
        test_cases = [
            ("API_TOKEN", "super-secret-token-12345", True),
            ("SECRET_KEY", "mysecretkey", True),
            ("PASSWORD", "password123", True),
            ("LOG_LEVEL", "DEBUG", False),
            ("ENVIRONMENT", "production", False)
        ]
        
        for env_var, value, should_mask in test_cases:
            masked_value = snapshot._mask_sensitive_value(env_var, value)
            
            if should_mask:
                assert "*" in masked_value, f"Sensitive variable {env_var} should be masked"
                assert masked_value != value, f"Masked value should be different from original"
            else:
                assert masked_value == value, f"Non-sensitive variable {env_var} should not be masked"
        
        print("✅ Value masking tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Value masking tests failed: {e}")
        return False

def test_import_structure():
    """Test that all required components can be imported."""
    try:
        print("✅ Testing import structure...")
        
        # Test main imports
        from core.config_drift_detector import (
            ConfigurationDriftDetector,
            DriftSeverity,
            DriftType,
            DriftEvent,
            ConfigurationSnapshot
        )
        
        # Verify classes are properly defined
        assert hasattr(ConfigurationDriftDetector, 'start_monitoring')
        assert hasattr(ConfigurationDriftDetector, 'detect_drift')
        assert hasattr(ConfigurationDriftDetector, 'get_drift_report')
        
        # Verify enums have required values
        assert hasattr(DriftSeverity, 'LOW')
        assert hasattr(DriftSeverity, 'MEDIUM') 
        assert hasattr(DriftSeverity, 'HIGH')
        assert hasattr(DriftSeverity, 'CRITICAL')
        
        assert hasattr(DriftType, 'FILE_CHANGE')
        assert hasattr(DriftType, 'ENV_MISMATCH')
        assert hasattr(DriftType, 'SCHEMA_VIOLATION')
        
        print("✅ Import structure tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import structure tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_simple_tests():
    """Run all simple tests."""
    print("🧪 Starting Simple Configuration Drift Detector Tests")
    print("=" * 80)
    
    tests = [
        ("Import Structure", test_import_structure),
        ("Enums", test_enums),
        ("DriftEvent", test_drift_event),
        ("ConfigurationSnapshot", test_configuration_snapshot),
        ("Severity Assessment", test_severity_assessment),
        ("File Monitoring Patterns", test_file_monitoring_patterns),
        ("Value Masking", test_value_masking)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name}: ERROR - {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SIMPLE TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    success = failed == 0
    
    if success:
        print(f"\n✅ ALL SIMPLE TESTS PASSED!")
        print(f"🚀 Configuration Drift Detector core functionality verified!")
    else:
        print(f"\n❌ {failed} TESTS FAILED!")
        print(f"🔧 Fix issues before proceeding.")
    
    return success

if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)