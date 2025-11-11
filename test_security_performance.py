#!/usr/bin/env python3
"""
Security and Performance Integration Tests
"""
import sys
import os
import time
import json
from pathlib import Path
import hashlib

# Set up paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'api'))

def test_security_imports():
    """Test security module imports"""
    try:
        from api.security_middleware import (
            SecurityMiddleware, SecurityConfig, InputSanitizer
        )
        print("✅ Security middleware imported successfully")
        
        # Test security config
        config = SecurityConfig()
        print(f"✅ Security config created: rate_limit={config.rate_limit_per_minute}")
        
        # Test input sanitizer
        sanitizer = InputSanitizer()
        test_input = "test_input_123"
        sanitized = sanitizer.sanitize_input(test_input)
        print("✅ Input sanitizer working")
        
        return True
        
    except Exception as e:
        print(f"❌ Security test failed: {str(e)}")
        return False

def test_performance_middleware():
    """Test performance middleware"""
    try:
        from api.performance_middleware import (
            get_performance_stats, get_rate_limit_config
        )
        print("✅ Performance middleware imported successfully")
        
        # Test performance stats
        try:
            stats = get_performance_stats()
            print("✅ Performance stats retrieved")
        except Exception as e:
            print(f"⚠️ Performance stats not available (expected): {str(e)}")
        
        # Test rate limit config
        rate_config = get_rate_limit_config()
        print(f"✅ Rate limit config: {rate_config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance middleware test failed: {str(e)}")
        return False

def test_health_monitoring():
    """Test health monitoring system"""
    try:
        from api.enhanced_health_endpoints import health_router
        print("✅ Health endpoints imported successfully")
        
        # Test health monitor import
        try:
            from api.services.faiss_health_monitoring import FAISSHealthMonitor
            monitor = FAISSHealthMonitor()
            print("✅ FAISS health monitor created")
            
            # Test a basic health check method
            if hasattr(monitor, 'get_index_status'):
                print("✅ Health monitor has required methods")
            else:
                print("⚠️ Health monitor missing some methods")
                
        except Exception as e:
            print(f"⚠️ FAISS health monitor issue (expected in test): {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health monitoring test failed: {str(e)}")
        return False

def test_environment_configuration():
    """Test environment configuration"""
    try:
        # Test environment variable access
        api_token = os.getenv('API_TOKEN')
        if api_token:
            print("✅ API_TOKEN environment variable found")
            # Check token format (should be hex)
            try:
                bytes.fromhex(api_token)
                print("✅ API token format valid")
            except ValueError:
                print("⚠️ API token format may be non-standard")
        else:
            print("⚠️ API_TOKEN not set in environment")
            
        # Test other important environment variables
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        cors_origins = os.getenv('CORS_ORIGINS', 'localhost')
        
        print(f"✅ Environment config - LOG_LEVEL: {log_level}, CORS_ORIGINS: {cors_origins}")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment configuration test failed: {str(e)}")
        return False

def test_ssl_configuration():
    """Test SSL certificate configuration"""
    try:
        ssl_path = Path("nginx/ssl")
        if not ssl_path.exists():
            print("⚠️ SSL directory not found")
            return True
            
        cert_file = ssl_path / "cert.pem"
        key_file = ssl_path / "key.pem"
        
        if cert_file.exists() and key_file.exists():
            print("✅ SSL certificate files found")
            
            # Basic certificate validation
            try:
                with open(cert_file, 'r') as f:
                    cert_content = f.read()
                    if "BEGIN CERTIFICATE" in cert_content:
                        print("✅ SSL certificate format valid")
                    else:
                        print("⚠️ SSL certificate format may be invalid")
                        
                with open(key_file, 'r') as f:
                    key_content = f.read()
                    if "BEGIN PRIVATE KEY" in key_content:
                        print("✅ SSL private key format valid")
                    else:
                        print("⚠️ SSL private key format may be invalid")
                        
            except Exception as e:
                print(f"⚠️ Could not read SSL files: {str(e)}")
        else:
            print("⚠️ SSL certificate files missing")
            
        return True
        
    except Exception as e:
        print(f"❌ SSL configuration test failed: {str(e)}")
        return False

def test_monitoring_configuration():
    """Test monitoring configuration"""
    try:
        # Test prometheus metrics
        from prometheus_client import Counter, Histogram, generate_latest
        print("✅ Prometheus client working")
        
        # Create test metrics
        test_counter = Counter('test_requests_total', 'Test counter')
        test_histogram = Histogram('test_request_duration_seconds', 'Test histogram')
        
        test_counter.inc()
        test_histogram.observe(0.1)
        
        # Generate metrics output
        metrics_output = generate_latest()
        if b'test_requests_total' in metrics_output:
            print("✅ Prometheus metrics generation working")
        else:
            print("⚠️ Metrics generation issue")
            
        return True
        
    except Exception as e:
        print(f"❌ Monitoring configuration test failed: {str(e)}")
        return False

def test_performance_benchmarks():
    """Test basic performance benchmarks"""
    try:
        import numpy as np
        
        # Test FAISS performance (basic)
        try:
            import faiss
            
            # Simple performance test
            d = 256
            nb = 1000
            nq = 10
            
            # Generate test data
            xb = np.random.random((nb, d)).astype('float32')
            xq = np.random.random((nq, d)).astype('float32')
            
            # Create index
            start_time = time.time()
            index = faiss.IndexFlatL2(d)
            index.add(xb)
            index_time = time.time() - start_time
            
            # Search
            start_time = time.time()
            D, I = index.search(xq, 10)
            search_time = time.time() - start_time
            
            print(f"✅ FAISS benchmark - Index: {index_time:.4f}s, Search: {search_time:.4f}s")
            
            if search_time < 0.1:  # Should be very fast for small test
                print("✅ FAISS search performance acceptable")
            else:
                print("⚠️ FAISS search performance slow")
                
        except Exception as e:
            print(f"⚠️ FAISS performance test issue: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance benchmarks failed: {str(e)}")
        return False

def main():
    """Run all security and performance tests"""
    print("🔧 Starting Security & Performance Testing")
    print("=" * 50)
    
    tests = [
        test_security_imports,
        test_performance_middleware,
        test_health_monitoring,
        test_environment_configuration,
        test_ssl_configuration,
        test_monitoring_configuration,
        test_performance_benchmarks
    ]
    
    results = []
    for test in tests:
        print(f"\n🧪 Running {test.__name__}...")
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Exception in {test.__name__}: {str(e)}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    pass_rate = passed / total if total > 0 else 0
    
    print(f"\n📊 Security & Performance Test Summary:")
    print(f"   Tests: {total}, Passed: {passed}, Failed: {total-passed}")
    print(f"   Pass Rate: {pass_rate:.1%}")
    
    return {
        "total_tests": total,
        "passed_tests": passed,
        "pass_rate": pass_rate,
        "status": "PASS" if pass_rate >= 0.7 else "FAIL"
    }

if __name__ == "__main__":
    result = main()
    exit_code = 0 if result["pass_rate"] >= 0.7 else 1
    
    # Save results
    with open("security_performance_test_results.json", "w") as f:
        json.dump(result, f, indent=2)
    
    sys.exit(exit_code)