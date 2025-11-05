#!/usr/bin/env python3
"""
Test Suite for API Token Rotation and Audit Logging
===================================================

Comprehensive integration tests for the API token rotation CLI and 
encrypted audit logging system with redaction capabilities.

Test Coverage:
- Token generation with entropy validation
- Token rotation with backup and restore
- Audit logging with proper redaction
- Integration with existing credential manager
- Backward compatibility with API_TOKEN environment variable
- CLI functionality and error handling
- Security compliance validation

Author: Quality Assurance Team
Version: 1.0.0 - Token Management Test Suite
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our components
try:
    from api.token_rotation_cli import (
        APITokenManager, TokenEntropyValidator, SecureTokenGenerator,
        TokenRotationAuditLogger, TokenMetrics
    )
    from api.enhanced_token_manager import BackwardCompatibleTokenManager
    from core.secure_credential_manager import SecureCredentialManager, CredentialType, SecurityLevel
    CLI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import token management components: {e}")
    CLI_AVAILABLE = False


class TokenRotationTestSuite:
    """Comprehensive test suite for token rotation functionality."""
    
    def __init__(self):
        self.test_environment = "test_token_rotation"
        self.temp_dir = None
        self.test_results: List[Dict[str, Any]] = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup isolated test environment."""
        # Create temporary directory for test
        self.temp_dir = tempfile.mkdtemp(prefix="adelaide_token_test_")
        
        # Set test environment variables
        os.environ["ENVIRONMENT"] = self.test_environment
        os.environ["CREDENTIAL_MASTER_KEY"] = "test_master_key_for_token_rotation_testing_only"
        
        print(f"🧪 Test environment setup: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up test directory: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️ Warning: Could not cleanup test directory: {e}")
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results."""
        print(f"\n🔬 Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            test_record = {
                "name": test_name,
                "status": "PASS" if result else "FAIL",
                "duration": round(duration, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": getattr(test_func, '_test_details', {})
            }
            
            self.test_results.append(test_record)
            
            if result:
                print(f"✅ {test_name} - PASSED ({duration:.3f}s)")
            else:
                print(f"❌ {test_name} - FAILED ({duration:.3f}s)")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            test_record = {
                "name": test_name,
                "status": "ERROR",
                "duration": round(duration, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "details": {}
            }
            
            self.test_results.append(test_record)
            print(f"💥 {test_name} - ERROR: {str(e)} ({duration:.3f}s)")
            return False
    
    def test_entropy_validator(self) -> bool:
        """Test token entropy validation functionality."""
        if not CLI_AVAILABLE:
            return False
        
        # Test strong token
        strong_token = "AbC123XyZ789-_qWeRtYuIoPaSdFgHjKlZxCvBnM.QwErTyUiOpAsDfGhJkL"
        metrics = TokenEntropyValidator.calculate_entropy(strong_token)
        
        if metrics.entropy_bits < 256:
            print(f"   ❌ Strong token entropy too low: {metrics.entropy_bits}")
            return False
        
        if metrics.security_level not in ["EXCELLENT", "GOOD"]:
            print(f"   ❌ Strong token security level inadequate: {metrics.security_level}")
            return False
        
        # Test weak token
        weak_token = "test123"
        is_valid, issues = TokenEntropyValidator.validate_token(weak_token)
        
        if is_valid:
            print(f"   ❌ Weak token incorrectly validated as valid")
            return False
        
        if len(issues) == 0:
            print(f"   ❌ No issues detected for weak token")
            return False
        
        print(f"   ✅ Entropy validator correctly identified weak token with {len(issues)} issues")
        return True
    
    def test_secure_token_generation(self) -> bool:
        """Test secure token generation with various parameters."""
        if not CLI_AVAILABLE:
            return False
        
        # Test default generation
        token1 = SecureTokenGenerator.generate_api_token()
        
        if len(token1) != 64:  # Default length
            print(f"   ❌ Default token length incorrect: {len(token1)}")
            return False
        
        # Validate entropy
        is_valid, issues = TokenEntropyValidator.validate_token(token1)
        if not is_valid:
            print(f"   ❌ Generated token failed validation: {issues}")
            return False
        
        # Test custom length
        token2 = SecureTokenGenerator.generate_api_token(length=32)
        if len(token2) != 32:
            print(f"   ❌ Custom length token incorrect: {len(token2)}")
            return False
        
        # Test uniqueness
        token3 = SecureTokenGenerator.generate_api_token()
        if token1 == token3:
            print(f"   ❌ Generated tokens are not unique")
            return False
        
        print(f"   ✅ Generated secure tokens with correct properties")
        return True
    
    def test_audit_logging_with_redaction(self) -> bool:
        """Test audit logging ensures tokens are properly redacted."""
        if not CLI_AVAILABLE:
            return False
        
        audit_logger = TokenRotationAuditLogger(self.test_environment)
        
        # Test token that should be redacted (make it strong enough to pass validation)
        test_token = "SuperSecretTokenThatShouldNeverAppearInLogsButHasGoodEntropyABC123XYZ789"
        
        # Log an operation
        audit_logger.log_token_operation(
            operation="test_operation",
            token_id="test_token_id",
            token_value=test_token,
            user_id="test_user",
            success=True,
            details={"test": "data"}
        )
        
        # Small delay to ensure log is written
        import time
        time.sleep(0.1)
        
        # Read audit logs and verify redaction
        records = audit_logger.get_audit_records()
        
        if not records:
            print(f"   ❌ No audit records found")
            return False
        
        # Check that the actual token value never appears in logs
        for record in records:
            if test_token in record:
                print(f"   ❌ Token value found in audit log: {record}")
                return False
        
        # Verify that hash is present (for correlation)
        found_hash = False
        found_test_operation = False
        for record in records:
            if "hash:" in record:
                found_hash = True
            if "test_operation" in record:
                found_test_operation = True
        
        if not found_hash:
            print(f"   ❌ Token hash not found in audit records")
            return False
            
        if not found_test_operation:
            print(f"   ❌ Test operation not found in audit records")
            return False
        
        print(f"   ✅ Audit logging properly redacts tokens while maintaining correlation")
        return True
    
    def test_token_manager_integration(self) -> bool:
        """Test integration with APITokenManager."""
        if not CLI_AVAILABLE:
            return False
        
        token_manager = APITokenManager(self.test_environment)
        
        # Test token generation
        new_token, metrics = token_manager.generate_new_token(length=48, user_id="test_integration")
        
        if len(new_token) != 48:
            print(f"   ❌ Generated token has wrong length: {len(new_token)}")
            return False
        
        if metrics.entropy_bits < 200:  # Should be high for 48-char token
            print(f"   ❌ Generated token has insufficient entropy: {metrics.entropy_bits}")
            return False
        
        # Test token rotation
        old_token = new_token
        rotated_token, backup_id = token_manager.rotate_api_token(
            length=64, 
            user_id="test_integration"
        )
        
        if len(rotated_token) != 64:
            print(f"   ❌ Rotated token has wrong length: {len(rotated_token)}")
            return False
        
        if rotated_token == old_token:
            print(f"   ❌ Rotated token is the same as old token")
            return False
        
        if not backup_id:
            print(f"   ❌ No backup ID returned from rotation")
            return False
        
        # Test current token retrieval
        current_token = token_manager.get_current_token("test_integration")
        if current_token != rotated_token:
            print(f"   ❌ Current token does not match rotated token")
            return False
        
        # Test token validation
        validation_result = token_manager.validate_token(current_token, "test_integration")
        if not validation_result["valid"]:
            print(f"   ❌ Current token failed validation")
            return False
        
        print(f"   ✅ Token manager integration working correctly")
        return True
    
    def test_backward_compatibility(self) -> bool:
        """Test backward compatibility with environment variables."""
        if not CLI_AVAILABLE:
            return False
        
        # Set test environment variable with proper entropy (64 chars, strong entropy)
        test_env_token = "StrongTestEnvironmentToken2024WithProperEntropyAbC123XyZ789DEFG"
        os.environ["API_TOKEN"] = test_env_token
        
        # Test backward compatible token manager
        compat_manager = BackwardCompatibleTokenManager(self.test_environment)
        
        # Should retrieve from environment variable
        retrieved_token = compat_manager.get_api_token()
        if retrieved_token != test_env_token:
            print(f"   ❌ Failed to retrieve token from environment variable")
            return False
        
        # Test validation
        is_valid, details = compat_manager.validate_token(test_env_token)
        if not is_valid:
            print(f"   ❌ Environment token failed validation: {details}")
            return False
        
        # Test current token check
        if not compat_manager.is_current_token(test_env_token):
            print(f"   ❌ Environment token not recognized as current")
            return False
        
        # Test token info
        token_info = compat_manager.get_token_info()
        if not token_info["configured"]:
            print(f"   ❌ Token not reported as configured")
            return False
        
        if token_info["source"] not in ["environment", "both"]:
            print(f"   ❌ Token source incorrect: {token_info['source']}")
            return False
        
        # Cleanup environment variable
        del os.environ["API_TOKEN"]
        
        print(f"   ✅ Backward compatibility working correctly")
        return True
    
    def test_cli_functionality(self) -> bool:
        """Test CLI functionality through subprocess calls."""
        if not CLI_AVAILABLE:
            return False
        
        cli_script = Path(__file__).parent / "api" / "token_rotation_cli.py"
        if not cli_script.exists():
            print(f"   ❌ CLI script not found: {cli_script}")
            return False
        
        try:
            # Test CLI help
            result = subprocess.run(
                [sys.executable, str(cli_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ❌ CLI help command failed: {result.stderr}")
                return False
            
            if "Adelaide Weather API Token Rotation CLI" not in result.stdout:
                print(f"   ❌ CLI help output missing expected content")
                return False
            
            # Test token generation
            result = subprocess.run(
                [sys.executable, str(cli_script), "--environment", self.test_environment, "generate", "--length", "32"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ❌ CLI generate command failed: {result.stderr}")
                return False
            
            if "Generated new API token" not in result.stdout:
                print(f"   ❌ CLI generate output missing expected content")
                return False
            
            # Test health check
            result = subprocess.run(
                [sys.executable, str(cli_script), "--environment", self.test_environment, "health"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ❌ CLI health command failed: {result.stderr}")
                return False
            
            print(f"   ✅ CLI functionality working correctly")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"   ❌ CLI command timed out")
            return False
        except Exception as e:
            print(f"   ❌ CLI test error: {e}")
            return False
    
    def test_security_compliance(self) -> bool:
        """Test security compliance requirements."""
        if not CLI_AVAILABLE:
            return False
        
        token_manager = APITokenManager(self.test_environment)
        
        # Generate token and check entropy requirements
        token, metrics = token_manager.generate_new_token(user_id="security_test")
        
        # Check minimum entropy (128 bits required)
        if metrics.entropy_bits < 128:
            print(f"   ❌ Token entropy below security minimum: {metrics.entropy_bits}")
            return False
        
        # Check character set diversity (minimum 0.75)
        if metrics.charset_diversity < 0.75:
            print(f"   ❌ Character set diversity below minimum: {metrics.charset_diversity}")
            return False
        
        # Check minimum length (32 characters)
        if metrics.length < 32:
            print(f"   ❌ Token length below security minimum: {metrics.length}")
            return False
        
        # Test audit trail completeness
        audit_records = token_manager.audit_logger.get_audit_records()
        
        required_operations = ["generate_token"]
        found_operations = set()
        
        for record in audit_records:
            parts = record.split('|')
            if len(parts) >= 2:
                found_operations.add(parts[1])
        
        missing_operations = set(required_operations) - found_operations
        if missing_operations:
            print(f"   ❌ Missing audit operations: {missing_operations}")
            return False
        
        # Verify no tokens in audit logs
        for record in audit_records:
            # Check for token patterns (should not exist)
            if len([part for part in record.split('|') if len(part) > 30 and part not in ['generate_token', 'rotate_token']]) > 0:
                # Additional check to ensure it's not actually a token value
                parts = record.split('|')
                for part in parts:
                    if len(part) > 30 and not part.startswith('{') and ':' not in part and '=' not in part:
                        print(f"   ❌ Potential token leak in audit log: {part[:20]}...")
                        return False
        
        print(f"   ✅ Security compliance requirements met")
        return True
    
    def test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        if not CLI_AVAILABLE:
            return False
        
        token_manager = APITokenManager(self.test_environment)
        
        # Test invalid token validation
        invalid_tokens = [
            "",  # Empty
            "abc",  # Too short
            "test123",  # Weak pattern
            "a" * 200,  # Too long but weak
        ]
        
        for invalid_token in invalid_tokens:
            try:
                is_valid, issues = token_manager.validate_token(invalid_token)
                if is_valid:
                    print(f"   ❌ Invalid token incorrectly validated: {invalid_token[:10]}...")
                    return False
            except Exception:
                # Expected for some invalid inputs
                pass
        
        # Test backup restoration with non-existent backup
        try:
            token_manager.restore_from_backup("non_existent_backup_id", "test_user")
            print(f"   ❌ Should have failed to restore non-existent backup")
            return False
        except Exception:
            # Expected
            pass
        
        print(f"   ✅ Error handling working correctly")
        return True
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        print("🚀 Starting Adelaide Weather API Token Rotation Test Suite")
        print(f"   Environment: {self.test_environment}")
        print(f"   CLI Available: {CLI_AVAILABLE}")
        
        if not CLI_AVAILABLE:
            print("❌ CLI components not available - skipping tests")
            return {
                "overall_status": "SKIPPED",
                "reason": "CLI components not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Define test cases
        test_cases = [
            ("Token Entropy Validation", self.test_entropy_validator),
            ("Secure Token Generation", self.test_secure_token_generation),
            ("Audit Logging with Redaction", self.test_audit_logging_with_redaction),
            ("Token Manager Integration", self.test_token_manager_integration),
            ("Backward Compatibility", self.test_backward_compatibility),
            ("CLI Functionality", self.test_cli_functionality),
            ("Security Compliance", self.test_security_compliance),
            ("Error Handling", self.test_error_handling),
        ]
        
        # Run all tests
        results = []
        for test_name, test_func in test_cases:
            success = self.run_test(test_name, test_func)
            results.append(success)
        
        # Calculate summary
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        overall_status = "PASS" if failed_tests == 0 else "FAIL"
        
        summary = {
            "overall_status": overall_status,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0,
            "test_results": self.test_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.test_environment
        }
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Overall Status: {'✅ PASS' if overall_status == 'PASS' else '❌ FAIL'}")
        print(f"   Tests Passed: {passed_tests}/{total_tests} ({summary['pass_rate']}%)")
        
        if failed_tests > 0:
            print(f"   Failed Tests:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"     - {result['name']}: {result['status']}")
        
        return summary


def main():
    """Main test execution function."""
    test_suite = TokenRotationTestSuite()
    
    try:
        # Run all tests
        results = test_suite.run_all_tests()
        
        # Save results to file
        results_file = Path(test_suite.temp_dir) / "token_rotation_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📁 Test results saved to: {results_file}")
        
        # Return appropriate exit code
        exit_code = 0 if results["overall_status"] == "PASS" else 1
        
        return exit_code
        
    finally:
        # Cleanup
        test_suite.cleanup_test_environment()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)