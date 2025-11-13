#!/usr/bin/env python3
"""
Test script for weak token detection in configuration drift system.

Tests various token security scenarios and verifies the drift detection
system properly identifies and reports weak tokens.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add the project path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config_drift_detector import ConfigurationDriftDetector
from api.token_rotation_cli import TokenEntropyValidator, SecureTokenGenerator


def test_weak_token_detection():
    """Test the weak token detection functionality."""
    print("🔒 Testing Weak Token Detection Implementation")
    print("=" * 60)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Initialize drift detector
        drift_detector = ConfigurationDriftDetector(
            project_root=project_root,
            enable_real_time=False
        )
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Strong Token",
                "token": SecureTokenGenerator.generate_api_token(length=64),
                "should_trigger_drift": False
            },
            {
                "name": "Weak Token - Too Short",
                "token": "short_token_123",
                "should_trigger_drift": True
            },
            {
                "name": "Weak Token - Low Entropy",
                "token": "a" * 40,  # Long but very low entropy
                "should_trigger_drift": True
            },
            {
                "name": "Weak Token - Common Patterns",
                "token": "test_password_demo_123456789012345",
                "should_trigger_drift": True
            },
            {
                "name": "Marginally Acceptable Token",
                "token": "AbC123def456GHI789jkl012MNO345pqr",  # 32 chars with good diversity
                "should_trigger_drift": False
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{i}. Testing: {scenario['name']}")
            print(f"   Token: {scenario['token'][:20]}{'...' if len(scenario['token']) > 20 else ''}")
            
            # Set API_TOKEN environment variable
            os.environ['API_TOKEN'] = scenario['token']
            
            # Perform drift detection
            try:
                drift_events = drift_detector.detect_drift(generate_report=False)
                
                # Debug: print all events first
                if drift_events and scenario['should_trigger_drift']:
                    print(f"   🔍 DEBUG: Found {len(drift_events)} total events:")
                    for i, evt in enumerate(drift_events):
                        print(f"      Event {i}: {evt.drift_type} | {evt.description}")
                
                # Look for security drift events
                security_events = [
                    e for e in drift_events 
                    if "security_drift" in str(e.drift_type)
                ]
                
                weak_token_events = [
                    e for e in security_events 
                    if ("weak_token" in e.event_id or 
                        "token" in e.description.lower())
                ]
                
                # Verify expected behavior
                if scenario['should_trigger_drift']:
                    if weak_token_events:
                        print(f"   ✅ PASS: Weak token detected as expected")
                        event = weak_token_events[0]
                        print(f"   📊 Event: {event.description}")
                        
                        # Show token analysis if available
                        token_analysis = event.metadata.get("token_security_analysis", {})
                        if token_analysis:
                            print(f"   🔍 Entropy: {token_analysis.get('entropy_bits', 0):.1f} bits")
                            print(f"   🎨 Diversity: {token_analysis.get('charset_diversity', 0):.2f}")
                            print(f"   🛡️  Security Level: {token_analysis.get('security_level', 'UNKNOWN')}")
                            
                            recommendations = token_analysis.get('recommendations', [])
                            if recommendations:
                                print(f"   💡 Recommendations:")
                                for rec in recommendations[:2]:  # Show first 2
                                    print(f"      • {rec}")
                    else:
                        print(f"   ❌ FAIL: Expected weak token detection but none found")
                        
                else:
                    if weak_token_events:
                        print(f"   ❌ FAIL: Unexpected weak token detection")
                        for event in weak_token_events:
                            print(f"      Event: {event.description}")
                    else:
                        print(f"   ✅ PASS: No weak token detected as expected")
                
                # Show TokenEntropyValidator analysis
                try:
                    is_valid, issues = TokenEntropyValidator.validate_token(scenario['token'])
                    metrics = TokenEntropyValidator.calculate_entropy(scenario['token'])
                    print(f"   📈 Validator: {'Valid' if is_valid else 'Invalid'} "
                          f"({metrics.security_level})")
                except Exception as e:
                    print(f"   ⚠️  Validator error: {e}")
                    
            except Exception as e:
                print(f"   ❌ ERROR: Drift detection failed: {e}")
        
        # Cleanup
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']
    
    print(f"\n🎯 Weak Token Detection Test Complete")


def test_health_endpoint_integration():
    """Test integration with health endpoints."""
    print(f"\n🏥 Testing Health Endpoint Integration")
    print("=" * 60)
    
    # Set a weak token for testing
    weak_token = "weak_test_token_123"
    os.environ['API_TOKEN'] = weak_token
    
    try:
        from api.health_checks import EnhancedHealthChecker
        
        # Initialize health checker
        health_checker = EnhancedHealthChecker()
        
        # Test configuration drift check
        import asyncio
        async def run_test():
            result = await health_checker._check_configuration_drift()
            
            print(f"Health Check Status: {result.status}")
            print(f"Message: {result.message}")
            print(f"Duration: {result.duration_ms:.1f}ms")
            
            details = result.details
            if details:
                print(f"Total Events: {details.get('total_events', 0)}")
                print(f"Critical Events: {details.get('events_by_severity', {}).get('critical', 0)}")
                
                token_security = details.get('token_security', {})
                if token_security:
                    print(f"🔒 Token Security Analysis:")
                    print(f"   Weak Token Detected: {token_security.get('weak_token_detected', False)}")
                    print(f"   Security Level: {token_security.get('security_level', 'UNKNOWN')}")
                    print(f"   Entropy: {token_security.get('entropy_bits', 0):.1f} bits")
                    
                    recommendations = token_security.get('recommendations', [])
                    if recommendations:
                        print(f"   Recommendations:")
                        for rec in recommendations[:3]:  # Show first 3
                            print(f"      • {rec}")
            
            return result.status == "fail"  # Should fail with weak token
        
        test_result = asyncio.run(run_test())
        if test_result:
            print("✅ PASS: Health endpoint correctly detected weak token")
        else:
            print("❌ FAIL: Health endpoint did not detect weak token")
            
    except Exception as e:
        print(f"❌ ERROR: Health endpoint test failed: {e}")
    finally:
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']


if __name__ == "__main__":
    test_weak_token_detection()
    test_health_endpoint_integration()
    print(f"\n🚀 All tests completed!")