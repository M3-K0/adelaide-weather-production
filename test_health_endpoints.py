#!/usr/bin/env python3
"""
Test script for health endpoints with weak token detection.

This script tests the health endpoint integration with configuration drift
detection and shows how weak token detection is surfaced.
"""

import os
import sys
import json
from pathlib import Path

# Add the project path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_drift_detector_directly():
    """Test the configuration drift detector directly."""
    print("🔧 Testing Configuration Drift Detector Directly")
    print("=" * 60)
    
    try:
        from core.config_drift_detector import ConfigurationDriftDetector
        
        # Set a weak token
        weak_token = "weak_test_123_demo"
        os.environ['API_TOKEN'] = weak_token
        print(f"Set API_TOKEN: {weak_token}")
        
        # Initialize drift detector
        drift_detector = ConfigurationDriftDetector(
            project_root=Path("."),
            enable_real_time=False
        )
        
        # Perform drift detection
        events = drift_detector.detect_drift(generate_report=False)
        
        # Analyze results
        security_events = [e for e in events if "security_drift" in str(e.drift_type)]
        token_events = [e for e in security_events if "token" in e.description.lower()]
        
        print(f"✅ Drift detection completed")
        print(f"   Total events: {len(events)}")
        print(f"   Security events: {len(security_events)}")
        print(f"   Token-related events: {len(token_events)}")
        
        # Show token analysis details
        for event in token_events:
            print(f"\n📊 Token Security Event:")
            print(f"   Event ID: {event.event_id}")
            print(f"   Description: {event.description}")
            print(f"   Severity: {event.severity}")
            
            # Show detailed analysis
            token_analysis = event.metadata.get("token_security_analysis", {})
            if token_analysis:
                print(f"   🔍 Security Analysis:")
                print(f"      Security Level: {token_analysis.get('security_level', 'UNKNOWN')}")
                print(f"      Entropy: {token_analysis.get('entropy_bits', 0):.1f} bits")
                print(f"      Charset Diversity: {token_analysis.get('charset_diversity', 0):.2f}")
                
                recommendations = token_analysis.get('recommendations', [])
                if recommendations:
                    print(f"   💡 Recommendations:")
                    for rec in recommendations[:3]:  # Show first 3
                        print(f"      • {rec}")
        
        return len(token_events) > 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']


def test_health_checker_mock():
    """Test the health checker without psutil dependency."""
    print(f"\n🏥 Testing Health Checker with Drift Detection")
    print("=" * 60)
    
    # Set a weak token for testing
    weak_token = "weak_test_token_123"
    os.environ['API_TOKEN'] = weak_token
    print(f"Set API_TOKEN: {weak_token}")
    
    try:
        # Import the configuration part only
        from core.config_drift_detector import ConfigurationDriftDetector
        
        project_root = Path(".")
        drift_detector = ConfigurationDriftDetector(
            project_root=project_root,
            enable_real_time=False
        )
        
        # Simulate the health check process
        print("🔍 Running configuration drift check...")
        
        # Perform drift detection (this is what the health endpoint would do)
        drift_events = drift_detector.detect_drift(generate_report=False)
        
        # Simulate health check analysis
        critical_events = [e for e in drift_events if e.is_critical()]
        security_events = [e for e in drift_events if "security_drift" in str(e.drift_type)]
        token_events = [e for e in security_events if "token" in e.description.lower()]
        
        # Determine health status
        if critical_events:
            status = "fail"
            message = f"{len(critical_events)} critical configuration drift events detected"
        else:
            status = "pass"
            message = "No critical configuration drift detected"
        
        # Prepare token security details
        token_security_details = {}
        if token_events:
            event = token_events[0]
            token_analysis = event.metadata.get("token_security_analysis", {})
            if token_analysis:
                token_security_details = {
                    "weak_token_detected": True,
                    "entropy_bits": token_analysis.get("entropy_bits", 0),
                    "charset_diversity": token_analysis.get("charset_diversity", 0),
                    "security_level": token_analysis.get("security_level", "UNKNOWN"),
                    "validation_issues": token_analysis.get("validation_issues", []),
                    "recommendations": token_analysis.get("recommendations", [])
                }
        
        # Format health response (similar to what the health endpoint would return)
        health_response = {
            "configuration_drift": {
                "status": status,
                "message": message,
                "monitoring_active": True,
                "total_events": len(drift_events),
                "events_by_severity": {
                    "critical": len(critical_events),
                    "high": len([e for e in drift_events if str(e.severity) == "high"]),
                    "medium": len([e for e in drift_events if str(e.severity) == "medium"]),
                    "low": len([e for e in drift_events if str(e.severity) == "low"])
                },
                "security_events": len(security_events)
            },
            "token_security_analysis": token_security_details
        }
        
        print(f"✅ Health check simulation completed")
        print(f"   Overall status: {status}")
        print(f"   Message: {message}")
        print(f"   Critical events: {len(critical_events)}")
        
        if token_security_details:
            print(f"\n🔒 Token Security Analysis:")
            print(f"   Weak token detected: {token_security_details['weak_token_detected']}")
            print(f"   Security level: {token_security_details['security_level']}")
            print(f"   Entropy: {token_security_details['entropy_bits']:.1f} bits")
            print(f"   Charset diversity: {token_security_details['charset_diversity']:.2f}")
            
            recommendations = token_security_details.get('recommendations', [])
            if recommendations:
                print(f"   💡 Top recommendations:")
                for rec in recommendations[:2]:
                    print(f"      • {rec}")
        
        # Show formatted JSON response
        print(f"\n📋 Health Endpoint Response Preview:")
        print(json.dumps(health_response, indent=2)[:500] + "...")
        
        return status == "fail"  # Should fail with weak token
        
    except Exception as e:
        print(f"❌ ERROR: Health check simulation failed: {e}")
        return False
    finally:
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']


def test_strong_token_scenario():
    """Test with a strong token to verify 0 criticals are reported."""
    print(f"\n🛡️  Testing Strong Token Scenario")
    print("=" * 60)
    
    try:
        from api.token_rotation_cli import SecureTokenGenerator
        from core.config_drift_detector import ConfigurationDriftDetector
        
        # Generate a strong token
        strong_token = SecureTokenGenerator.generate_api_token(length=64)
        os.environ['API_TOKEN'] = strong_token
        print(f"Set strong API_TOKEN: {strong_token[:20]}...")
        
        # Initialize drift detector
        drift_detector = ConfigurationDriftDetector(
            project_root=Path("."),
            enable_real_time=False
        )
        
        # Perform drift detection
        events = drift_detector.detect_drift(generate_report=False)
        critical_events = [e for e in events if e.is_critical()]
        security_events = [e for e in events if "security_drift" in str(e.drift_type)]
        
        print(f"✅ Strong token test completed")
        print(f"   Total events: {len(events)}")
        print(f"   Critical events: {len(critical_events)}")
        print(f"   Security events: {len(security_events)}")
        
        # Should have 0 critical events with a strong token
        if len(critical_events) == 0:
            print("✅ PASS: No critical events detected with strong token")
            return True
        else:
            print("❌ FAIL: Unexpected critical events with strong token")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Strong token test failed: {e}")
        return False
    finally:
        if 'API_TOKEN' in os.environ:
            del os.environ['API_TOKEN']


if __name__ == "__main__":
    print("🚀 Health Endpoints Integration Testing")
    print("=" * 80)
    
    # Run tests
    test1_result = test_drift_detector_directly()
    test2_result = test_health_checker_mock()
    test3_result = test_strong_token_scenario()
    
    print(f"\n📊 Test Summary:")
    print(f"   Drift detector integration: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"   Health check simulation: {'✅ PASS' if test2_result else '❌ FAIL'}")
    print(f"   Strong token validation: {'✅ PASS' if test3_result else '❌ FAIL'}")
    
    if test1_result and test2_result and test3_result:
        print(f"\n🎉 All tests passed! Weak token detection is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Review implementation.")