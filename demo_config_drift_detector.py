#!/usr/bin/env python3
"""
Configuration Drift Detection System Demo
=========================================

Comprehensive demonstration of the configuration drift detection capabilities
for the Adelaide weather forecasting system. Shows real-world usage scenarios
and integration with existing infrastructure.

This demo showcases:
- Initial configuration baseline establishment
- Real-time drift detection and alerting
- Severity-based categorization and reporting
- Cross-environment consistency validation
- Integration with existing health monitoring
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config_drift_detector import (
    ConfigurationDriftDetector,
    DriftSeverity,
    DriftType
)

def demo_basic_functionality():
    """Demonstrate basic drift detection functionality."""
    print("\n" + "="*80)
    print("🎯 DEMO: Basic Configuration Drift Detection")
    print("="*80)
    
    # Create temporary environment for demo
    temp_dir = Path(tempfile.mkdtemp())
    print(f"📁 Demo environment: {temp_dir}")
    
    try:
        # Create sample configuration structure
        configs_dir = temp_dir / "configs"
        configs_dir.mkdir()
        
        # Create initial configuration files
        data_config = {
            'adelaide': {'lat': -34.9, 'lon': 138.6},
            'era5': {'variables': ['temperature', 'pressure']},
            'processing': {'normalize_method': 'zscore'}
        }
        
        with open(configs_dir / "data.yaml", 'w') as f:
            import yaml
            yaml.dump(data_config, f)
        
        # Create environment file
        env_content = """API_TOKEN=demo-token-12345
ENVIRONMENT=development
LOG_LEVEL=INFO
"""
        with open(temp_dir / ".env", 'w') as f:
            f.write(env_content)
        
        print("✅ Created sample configuration files")
        
        # Initialize drift detector
        detector = ConfigurationDriftDetector(
            project_root=temp_dir,
            enable_real_time=False,  # Disable for demo
            check_interval_seconds=5
        )
        
        # Start monitoring and create baseline
        success = detector.start_monitoring()
        print(f"🚀 Monitoring started: {success}")
        
        # Perform initial drift detection
        print("\n🔍 Performing initial drift detection...")
        initial_events = detector.detect_drift()
        print(f"📊 Initial drift events: {len(initial_events)}")
        
        # Simulate configuration changes
        print("\n⚡ Simulating configuration changes...")
        
        # 1. Modify data configuration (HIGH severity)
        data_config['processing']['normalize_method'] = 'minmax'
        data_config['new_setting'] = {'added': True}
        
        with open(configs_dir / "data.yaml", 'w') as f:
            yaml.dump(data_config, f)
        print("   Modified data.yaml configuration")
        
        # 2. Change environment variable (CRITICAL severity)
        env_content_modified = """API_TOKEN=new-token-67890
ENVIRONMENT=development
LOG_LEVEL=DEBUG
"""
        with open(temp_dir / ".env", 'w') as f:
            f.write(env_content_modified)
        print("   Changed environment variables")
        
        # 3. Add new critical configuration (CRITICAL severity)
        docker_compose = {
            'version': '3.8',
            'services': {
                'api': {'image': 'weather-api:latest', 'ports': ['8000:8000']}
            }
        }
        
        with open(temp_dir / "docker-compose.yml", 'w') as f:
            yaml.dump(docker_compose, f)
        print("   Added docker-compose.yml")
        
        # 4. Create potentially insecure configuration (CRITICAL security drift)
        os.environ['API_TOKEN'] = 'test123'  # Obviously insecure
        
        # Detect drift after changes
        print("\n🔍 Detecting configuration drift...")
        drift_events = detector.detect_drift()
        
        print(f"\n📈 DRIFT DETECTION RESULTS:")
        print(f"   Total events detected: {len(drift_events)}")
        
        # Categorize by severity
        severity_counts = {}
        for event in drift_events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
        
        for severity, count in severity_counts.items():
            print(f"   {severity.value.upper()}: {count} events")
        
        # Show sample events
        print(f"\n📋 SAMPLE DRIFT EVENTS:")
        for i, event in enumerate(drift_events[:3]):  # Show first 3
            print(f"   {i+1}. [{event.severity.value.upper()}] {event.description}")
            print(f"      Source: {event.source_path}")
            print(f"      Type: {event.drift_type.value}")
        
        if len(drift_events) > 3:
            print(f"   ... and {len(drift_events) - 3} more events")
        
        # Generate comprehensive report
        print(f"\n📄 Generating drift report...")
        report = detector.get_drift_report()
        
        print(f"   Report generated with {report['drift_summary']['total_events']} events")
        print(f"   Critical issues: {report['drift_summary']['critical_events']}")
        print(f"   Recommendations: {len(report['recommendations'])}")
        
        # Show recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'][:3]):
            print(f"   {i+1}. {rec}")
        
        # Demonstrate event resolution
        if drift_events:
            print(f"\n✅ Demonstrating event resolution...")
            first_event = drift_events[0]
            success = detector.resolve_drift_event(
                first_event.event_id, 
                "Resolved during demo - configuration change approved"
            )
            print(f"   Event resolved: {success}")
        
        # Stop monitoring
        detector.stop_monitoring()
        print(f"\n🛑 Monitoring stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        
        # Restore environment
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']

def demo_severity_assessment():
    """Demonstrate severity assessment and prioritization."""
    print("\n" + "="*80)
    print("🎯 DEMO: Severity Assessment and Prioritization")
    print("="*80)
    
    from core.config_drift_detector import ConfigurationSnapshot
    
    # Create test snapshot for severity testing
    snapshot = ConfigurationSnapshot(
        snapshot_id="severity_demo",
        timestamp=datetime.now().isoformat(),
        file_hashes={},
        environment_vars={},
        schema_validation={}
    )
    
    # Test file severity assessment
    print("📁 FILE SEVERITY ASSESSMENT:")
    
    test_files = [
        ("docker-compose.yml", "Production orchestration"),
        (".env.production", "Production secrets"),
        ("configs/model.yaml", "ML model configuration"),
        ("configs/data.yaml", "Data processing configuration"),
        ("monitoring/prometheus.yml", "Monitoring configuration"),
        (".env", "Environment variables"),
        ("package.json", "Dependencies"),
        ("README.md", "Documentation")
    ]
    
    for file_path, description in test_files:
        severity = snapshot._determine_file_change_severity(file_path)
        severity_icon = {
            DriftSeverity.CRITICAL: "🚨",
            DriftSeverity.HIGH: "⚠️",
            DriftSeverity.MEDIUM: "📋",
            DriftSeverity.LOW: "ℹ️"
        }
        
        print(f"   {severity_icon[severity]} {severity.value.upper():8} | {file_path:25} | {description}")
    
    # Test environment variable severity assessment
    print(f"\n🌍 ENVIRONMENT VARIABLE SEVERITY ASSESSMENT:")
    
    test_env_vars = [
        ("API_TOKEN", "Authentication token"),
        ("SECRET_KEY", "Application secret key"),
        ("DATABASE_URL", "Database connection"),
        ("ENVIRONMENT", "Deployment environment"),
        ("LOG_LEVEL", "Logging configuration"),
        ("API_BASE_URL", "Service endpoint"),
        ("TIMEOUT", "Request timeout"),
        ("CUSTOM_VAR", "Custom application setting")
    ]
    
    for env_var, description in test_env_vars:
        severity = snapshot._determine_env_change_severity(env_var)
        severity_icon = {
            DriftSeverity.CRITICAL: "🚨",
            DriftSeverity.HIGH: "⚠️",
            DriftSeverity.MEDIUM: "📋",
            DriftSeverity.LOW: "ℹ️"
        }
        
        print(f"   {severity_icon[severity]} {severity.value.upper():8} | {env_var:20} | {description}")
    
    print(f"\n💡 SEVERITY GUIDELINES:")
    print(f"   🚨 CRITICAL: Immediate action required - system functionality at risk")
    print(f"   ⚠️ HIGH:     Review required - operational impact possible")
    print(f"   📋 MEDIUM:   Monitor changes - configuration management needed")
    print(f"   ℹ️ LOW:      Informational - track for completeness")

def demo_security_drift_detection():
    """Demonstrate security-related drift detection."""
    print("\n" + "="*80)
    print("🎯 DEMO: Security Drift Detection")
    print("="*80)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize detector
        detector = ConfigurationDriftDetector(
            project_root=temp_dir,
            enable_real_time=False
        )
        
        print("🔐 Testing security drift detection...")
        
        # Set up potentially insecure environment variables
        insecure_configs = {
            'API_TOKEN': 'test123',        # Obviously insecure
            'SECRET_KEY': 'password',      # Common weak secret
            'DATABASE_URL': 'localhost:5432/test',  # Contains localhost
            'JWT_SECRET': 'demo'           # Too simple
        }
        
        print(f"\n⚠️ Setting up insecure configurations:")
        for var, value in insecure_configs.items():
            os.environ[var] = value
            print(f"   {var}: {'*' * len(value[:4])}{value[4:] if len(value) > 4 else ''}")
        
        # Create snapshot and detect security drift
        snapshot = detector._create_configuration_snapshot("security_test")
        security_events = detector._detect_security_drift(snapshot)
        
        print(f"\n🚨 SECURITY DRIFT DETECTED:")
        print(f"   Total security issues: {len(security_events)}")
        
        for i, event in enumerate(security_events, 1):
            print(f"   {i}. {event.description}")
            print(f"      Source: {event.source_path}")
            print(f"      Severity: {event.severity.value.upper()}")
        
        if not security_events:
            print("   ✅ No security drift detected")
        
        print(f"\n🛡️ SECURITY RECOMMENDATIONS:")
        print(f"   • Use strong, randomly generated tokens")
        print(f"   • Avoid localhost references in production")
        print(f"   • Implement secret management systems")
        print(f"   • Regularly rotate credentials")
        print(f"   • Monitor for credential exposure")
        
    finally:
        # Cleanup environment
        for var in ['API_TOKEN', 'SECRET_KEY', 'DATABASE_URL', 'JWT_SECRET']:
            if var in os.environ:
                del os.environ[var]
        
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def demo_reporting_and_analytics():
    """Demonstrate comprehensive reporting and analytics."""
    print("\n" + "="*80)
    print("🎯 DEMO: Reporting and Analytics")
    print("="*80)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize detector
        detector = ConfigurationDriftDetector(
            project_root=temp_dir,
            enable_real_time=False
        )
        
        # Create mock drift events for demonstration
        from core.config_drift_detector import DriftEvent
        
        mock_events = [
            DriftEvent(
                event_id="demo_001",
                drift_type=DriftType.FILE_CHANGE,
                severity=DriftSeverity.CRITICAL,
                source_path="docker-compose.yml",
                description="Production orchestration modified",
                detected_at=datetime.now().isoformat(),
                metadata={"demo": True}
            ),
            DriftEvent(
                event_id="demo_002",
                drift_type=DriftType.ENV_MISMATCH,
                severity=DriftSeverity.HIGH,
                source_path="ENV:LOG_LEVEL",
                description="Logging configuration changed",
                detected_at=datetime.now().isoformat(),
                metadata={"demo": True}
            ),
            DriftEvent(
                event_id="demo_003",
                drift_type=DriftType.SCHEMA_VIOLATION,
                severity=DriftSeverity.MEDIUM,
                source_path="configs/invalid.yaml",
                description="Configuration schema validation failed",
                detected_at=datetime.now().isoformat(),
                metadata={"demo": True}
            ),
            DriftEvent(
                event_id="demo_004",
                drift_type=DriftType.SECURITY_DRIFT,
                severity=DriftSeverity.CRITICAL,
                source_path="ENV:API_TOKEN",
                description="Insecure token detected",
                detected_at=datetime.now().isoformat(),
                metadata={"demo": True}
            )
        ]
        
        # Add mock events to detector
        detector.drift_events = mock_events
        
        print("📊 Generating comprehensive drift report...")
        
        # Generate full report
        report = detector.get_drift_report()
        
        print(f"\n📈 DRIFT ANALYSIS SUMMARY:")
        summary = report['drift_summary']
        print(f"   Total Events: {summary['total_events']}")
        print(f"   Unresolved: {summary['unresolved_events']}")
        print(f"   Critical: {summary['critical_events']}")
        print(f"   High: {summary['high_events']}")
        print(f"   Medium: {summary['medium_events']}")
        print(f"   Low: {summary['low_events']}")
        
        print(f"\n🏷️ DRIFT TYPE DISTRIBUTION:")
        for drift_type, count in report['drift_types'].items():
            print(f"   {drift_type.replace('_', ' ').title()}: {count}")
        
        print(f"\n📁 MOST AFFECTED SOURCES:")
        for source, count in list(report['affected_sources'].items())[:5]:
            print(f"   {source}: {count} events")
        
        print(f"\n🚨 CRITICAL ISSUES REQUIRING ATTENTION:")
        for issue in report['critical_issues']:
            print(f"   • {issue['description']}")
            print(f"     Source: {issue['source_path']}")
        
        print(f"\n💡 ACTIONABLE RECOMMENDATIONS:")
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   {i}. {recommendation}")
        
        print(f"\n📋 MONITORING STATUS:")
        status = report['monitoring_status']
        print(f"   Active: {status['active']}")
        print(f"   Baseline Available: {status['baseline_available']}")
        print(f"   Real-time Enabled: {status['real_time_enabled']}")
        print(f"   Snapshots: {status['snapshots_count']}")
        
        # Demonstrate filtering
        print(f"\n🔍 FILTERING EXAMPLES:")
        
        # Filter by severity
        critical_report = detector.get_drift_report(severity_filter=DriftSeverity.CRITICAL)
        print(f"   Critical-only filter: {critical_report['drift_summary']['total_events']} events")
        
        # Filter by time
        recent_report = detector.get_drift_report(hours_back=1)
        print(f"   Last 1 hour filter: {recent_report['drift_summary']['total_events']} events")
        
        # Save report to file
        report_path = temp_dir / "drift_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: {report_path}")
        
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def demo_integration_with_adelaide_system():
    """Demonstrate integration with Adelaide weather system."""
    print("\n" + "="*80)
    print("🎯 DEMO: Integration with Adelaide Weather System")
    print("="*80)
    
    # Use actual project root
    adelaide_root = Path("/home/micha/adelaide-weather-final")
    
    if not adelaide_root.exists():
        print("⚠️ Adelaide weather system not found - skipping integration demo")
        return
    
    print(f"🌦️ Integrating with Adelaide weather system at: {adelaide_root}")
    
    # Initialize detector with real project
    detector = ConfigurationDriftDetector(
        project_root=adelaide_root,
        enable_real_time=False,  # Safe for demo
        check_interval_seconds=30
    )
    
    print(f"\n🔍 Analyzing existing configuration...")
    
    # Start monitoring to create baseline
    success = detector.start_monitoring()
    print(f"   Monitoring started: {success}")
    
    if success:
        # Perform drift detection on existing system
        drift_events = detector.detect_drift(generate_report=False)
        
        print(f"   Configuration files found: {len(detector.baseline_snapshot.file_hashes) if detector.baseline_snapshot else 0}")
        print(f"   Environment variables monitored: {len(detector.baseline_snapshot.environment_vars) if detector.baseline_snapshot else 0}")
        print(f"   Initial drift events: {len(drift_events)}")
        
        if drift_events:
            print(f"\n⚠️ EXISTING DRIFT DETECTED:")
            for event in drift_events[:3]:
                print(f"   • {event.description}")
        else:
            print(f"\n✅ No configuration drift detected in Adelaide system")
        
        # Show configuration files being monitored
        if detector.baseline_snapshot:
            print(f"\n📁 MONITORED CONFIGURATION FILES:")
            config_files = list(detector.baseline_snapshot.file_hashes.keys())
            for config_file in sorted(config_files)[:10]:  # Show first 10
                print(f"   • {config_file}")
            if len(config_files) > 10:
                print(f"   ... and {len(config_files) - 10} more files")
        
        # Show environment variables being monitored
        if detector.baseline_snapshot:
            print(f"\n🌍 MONITORED ENVIRONMENT VARIABLES:")
            env_vars = list(detector.baseline_snapshot.environment_vars.keys())
            for env_var in sorted(env_vars):
                value = detector.baseline_snapshot.environment_vars[env_var]
                masked_value = detector.baseline_snapshot._mask_sensitive_value(env_var, value)
                print(f"   • {env_var}: {masked_value}")
        
        detector.stop_monitoring()
    
    print(f"\n🏗️ PRODUCTION DEPLOYMENT RECOMMENDATIONS:")
    print(f"   • Enable real-time monitoring in production")
    print(f"   • Set up alerting for CRITICAL and HIGH severity events")
    print(f"   • Integrate with existing health monitoring systems")
    print(f"   • Schedule regular drift reports")
    print(f"   • Implement automated drift resolution workflows")

def main():
    """Run comprehensive configuration drift detection demo."""
    print("🎬 Configuration Drift Detection System - Comprehensive Demo")
    print("=" * 80)
    print("Demonstrating production-grade configuration monitoring capabilities")
    print("for the Adelaide Weather Forecasting System")
    print("=" * 80)
    
    demos = [
        ("Basic Functionality", demo_basic_functionality),
        ("Severity Assessment", demo_severity_assessment),
        ("Security Drift Detection", demo_security_drift_detection),
        ("Reporting and Analytics", demo_reporting_and_analytics),
        ("Adelaide System Integration", demo_integration_with_adelaide_system)
    ]
    
    successful_demos = 0
    
    for demo_name, demo_func in demos:
        print(f"\n🎯 Starting Demo: {demo_name}")
        try:
            success = demo_func()
            if success is not False:  # Handle None as success
                successful_demos += 1
                print(f"✅ Demo completed successfully: {demo_name}")
            else:
                print(f"❌ Demo failed: {demo_name}")
        except Exception as e:
            print(f"💥 Demo crashed: {demo_name} - {e}")
    
    print(f"\n" + "="*80)
    print(f"DEMO SUMMARY")
    print(f"="*80)
    print(f"Completed: {successful_demos}/{len(demos)} demos")
    
    if successful_demos == len(demos):
        print(f"🚀 ALL DEMOS SUCCESSFUL!")
        print(f"🎯 Configuration Drift Detector is ready for production deployment!")
    else:
        print(f"⚠️ Some demos had issues - review output above")
    
    print(f"\n🏁 Configuration Drift Detection Demo Complete")

if __name__ == "__main__":
    main()