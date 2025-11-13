#!/usr/bin/env python3
"""
Adelaide Weather Forecasting - Synthetic Monitoring Tests
=========================================================

Test suite for validating the synthetic monitoring system functionality.

Run this script to verify that all components are working correctly.
"""

import os
import sys
import time
import json
import asyncio
import requests
from datetime import datetime, timezone

# Test configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
SYNTHETIC_MONITOR_URL = os.getenv('SYNTHETIC_MONITOR_URL', 'http://localhost:8080')
API_TOKEN = os.getenv('API_TOKEN', 'test-token')

def test_api_endpoints():
    """Test API endpoints that synthetic monitoring checks."""
    print("🔍 Testing API endpoints...")
    
    tests = [
        {
            'name': 'Health Status',
            'url': f'{API_BASE_URL}/health/status',
            'expected_status': 200
        },
        {
            'name': 'Health Liveness',
            'url': f'{API_BASE_URL}/health/live',
            'expected_status': 200
        },
        {
            'name': 'Health Readiness',
            'url': f'{API_BASE_URL}/health/ready',
            'expected_status': 200
        },
        {
            'name': 'Forecast Endpoint',
            'url': f'{API_BASE_URL}/forecast?horizon=24h&vars=t2m',
            'headers': {'Authorization': f'Bearer {API_TOKEN}'},
            'expected_status': 200
        }
    ]
    
    results = []
    for test in tests:
        try:
            response = requests.get(
                test['url'], 
                headers=test.get('headers', {}),
                timeout=10
            )
            
            success = response.status_code == test['expected_status']
            results.append({
                'name': test['name'],
                'success': success,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            })
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test['name']}: {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
            
        except Exception as e:
            results.append({
                'name': test['name'],
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ FAIL {test['name']}: {str(e)}")
    
    return results

def test_synthetic_monitor():
    """Test synthetic monitoring service."""
    print("\n📊 Testing synthetic monitoring service...")
    
    try:
        # Check metrics endpoint
        response = requests.get(f'{SYNTHETIC_MONITOR_URL}/metrics', timeout=10)
        if response.status_code == 200:
            metrics_text = response.text
            
            # Check for key metrics
            required_metrics = [
                'synthetic_check_total',
                'synthetic_check_success_total',
                'synthetic_check_duration_seconds',
                'slo_availability_ratio',
                'slo_error_budget_remaining_ratio'
            ]
            
            found_metrics = []
            for metric in required_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)
                    print(f"  ✅ Found metric: {metric}")
                else:
                    print(f"  ❌ Missing metric: {metric}")
            
            print(f"  📈 Metrics found: {len(found_metrics)}/{len(required_metrics)}")
            return len(found_metrics) == len(required_metrics)
            
        else:
            print(f"  ❌ Metrics endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing synthetic monitor: {str(e)}")
        return False

def test_prometheus_integration():
    """Test Prometheus integration."""
    print("\n🎯 Testing Prometheus integration...")
    
    try:
        # Check Prometheus targets
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/targets', timeout=10)
        if response.status_code == 200:
            targets = response.json()
            
            # Find synthetic monitor target
            synthetic_targets = []
            for target in targets.get('data', {}).get('activeTargets', []):
                if 'synthetic-monitor' in target.get('job', ''):
                    synthetic_targets.append(target)
            
            if synthetic_targets:
                target = synthetic_targets[0]
                health = target.get('health')
                print(f"  ✅ Synthetic monitor target found: {health}")
                return health == 'up'
            else:
                print("  ❌ Synthetic monitor target not found")
                return False
                
        else:
            print(f"  ❌ Prometheus API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing Prometheus: {str(e)}")
        return False

def test_slo_metrics():
    """Test SLO metrics availability."""
    print("\n📋 Testing SLO metrics...")
    
    try:
        # Query SLO metrics from Prometheus
        queries = [
            'slo_availability_ratio',
            'slo_error_budget_remaining_ratio',
            'slo_burn_rate',
            'synthetic_check_success_total',
            'synthetic_check_duration_seconds'
        ]
        
        results = []
        for query in queries:
            response = requests.get(
                f'{PROMETHEUS_URL}/api/v1/query',
                params={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('data', {}).get('result', [])
                
                if result:
                    print(f"  ✅ {query}: {len(result)} series")
                    results.append(True)
                else:
                    print(f"  ⚠️  {query}: No data")
                    results.append(False)
            else:
                print(f"  ❌ {query}: Query failed ({response.status_code})")
                results.append(False)
        
        success_rate = sum(results) / len(results)
        print(f"  📊 SLO metrics availability: {success_rate:.1%}")
        return success_rate >= 0.8  # 80% of metrics should be available
        
    except Exception as e:
        print(f"  ❌ Error testing SLO metrics: {str(e)}")
        return False

def test_alert_rules():
    """Test alert rules configuration."""
    print("\n🚨 Testing alert rules...")
    
    try:
        # Check alert rules
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/rules', timeout=10)
        if response.status_code == 200:
            rules_data = response.json()
            
            slo_rules = 0
            synthetic_rules = 0
            
            for group in rules_data.get('data', {}).get('groups', []):
                group_name = group.get('name', '')
                
                if 'slo_' in group_name:
                    slo_rules += len(group.get('rules', []))
                elif 'synthetic' in group_name:
                    synthetic_rules += len(group.get('rules', []))
            
            print(f"  📊 SLO alert rules: {slo_rules}")
            print(f"  📊 Synthetic monitoring rules: {synthetic_rules}")
            
            total_rules = slo_rules + synthetic_rules
            if total_rules > 0:
                print(f"  ✅ Total alert rules: {total_rules}")
                return True
            else:
                print("  ❌ No alert rules found")
                return False
                
        else:
            print(f"  ❌ Rules API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing alert rules: {str(e)}")
        return False

def generate_test_report(results):
    """Generate a test report."""
    print("\n" + "="*60)
    print("🔍 SYNTHETIC MONITORING TEST REPORT")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    
    print(f"📊 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    print(f"📈 Success Rate: {passed_tests/total_tests:.1%}")
    print()
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Synthetic monitoring is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
        print("\nFailed tests:")
        for result in results:
            if not result['success']:
                print(f"  ❌ {result['name']}: {result.get('error', 'Test failed')}")
        return False

def main():
    """Run all synthetic monitoring tests."""
    print("🚀 Adelaide Weather Forecasting - Synthetic Monitoring Tests")
    print(f"⏰ Started at: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(5)
    
    # Run tests
    test_results = []
    
    # Test individual components
    api_test_success = len([r for r in test_api_endpoints() if r['success']]) > 0
    test_results.append({'name': 'API Endpoints', 'success': api_test_success})
    
    synthetic_test_success = test_synthetic_monitor()
    test_results.append({'name': 'Synthetic Monitor', 'success': synthetic_test_success})
    
    prometheus_test_success = test_prometheus_integration()
    test_results.append({'name': 'Prometheus Integration', 'success': prometheus_test_success})
    
    slo_test_success = test_slo_metrics()
    test_results.append({'name': 'SLO Metrics', 'success': slo_test_success})
    
    alert_test_success = test_alert_rules()
    test_results.append({'name': 'Alert Rules', 'success': alert_test_success})
    
    # Generate report
    success = generate_test_report(test_results)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())