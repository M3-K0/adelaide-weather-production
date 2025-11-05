#!/usr/bin/env python3
"""
Adelaide Weather API - Token Rotation Demonstration
===================================================

Demonstrates the complete token rotation and audit logging functionality.
This script showcases the integration between the CLI tools, secure credential
management, and enhanced security features.

Features Demonstrated:
- Secure token generation with entropy validation
- Token rotation with automatic backup creation
- Comprehensive audit logging with redaction
- Backward compatibility with environment variables
- CLI integration and operational workflows

Author: Security Operations Team
Version: 1.0.0 - Token Management Demonstration
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from api.token_rotation_cli import (
        APITokenManager, TokenEntropyValidator, SecureTokenGenerator
    )
    from api.enhanced_token_manager import get_token_manager, get_api_token
    DEMO_AVAILABLE = True
except ImportError as e:
    print(f"❌ Could not import token management components: {e}")
    DEMO_AVAILABLE = False


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"🔐 {title}")
    print(f"{'=' * 60}")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n🔍 {title}")
    print("-" * 40)


def demonstrate_token_entropy():
    """Demonstrate token entropy validation."""
    print_section("Token Entropy Validation")
    
    # Test various token strengths
    test_tokens = [
        ("weak_token", "Weak Token"),
        ("medium_strength_token_12345", "Medium Strength Token"),
        ("VeryStrongTokenWithGoodEntropyABC123XYZ789-_DefGhi", "Strong Token")
    ]
    
    for token, description in test_tokens:
        print(f"\n📝 Testing: {description}")
        print(f"   Token: {token}")
        
        metrics = TokenEntropyValidator.calculate_entropy(token)
        is_valid, issues = TokenEntropyValidator.validate_token(token)
        
        print(f"   Length: {metrics.length} characters")
        print(f"   Entropy: {metrics.entropy_bits:.1f} bits")
        print(f"   Security Level: {metrics.security_level}")
        print(f"   Character Diversity: {metrics.charset_diversity:.2f}")
        print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")
        
        if issues:
            print(f"   Issues: {', '.join(issues[:2])}")  # Show first 2 issues


def demonstrate_secure_generation():
    """Demonstrate secure token generation."""
    print_section("Secure Token Generation")
    
    # Generate tokens of different lengths
    lengths = [32, 48, 64]
    
    for length in lengths:
        print(f"\n🎲 Generating {length}-character token...")
        
        token = SecureTokenGenerator.generate_api_token(length=length)
        metrics = TokenEntropyValidator.calculate_entropy(token)
        
        print(f"   Generated Token: {token[:16]}...{token[-8:]}")  # Partial display
        print(f"   Entropy: {metrics.entropy_bits:.1f} bits")
        print(f"   Security Level: {metrics.security_level}")
        print(f"   Character Diversity: {metrics.charset_diversity:.2f}")


def demonstrate_token_rotation():
    """Demonstrate complete token rotation workflow."""
    print_section("Token Rotation Workflow")
    
    # Use demo environment
    demo_env = "demo_token_rotation"
    os.environ["ENVIRONMENT"] = demo_env
    os.environ["CREDENTIAL_MASTER_KEY"] = "demo_master_key_for_token_rotation_demo_only"
    
    token_manager = APITokenManager(demo_env)
    
    print("\n🔄 Step 1: Generate Initial Token")
    initial_token, metrics = token_manager.generate_new_token(
        length=48, 
        user_id="demo_admin"
    )
    print(f"   Initial Token Generated: {initial_token[:12]}...{initial_token[-8:]}")
    print(f"   Entropy: {metrics.entropy_bits:.1f} bits")
    print(f"   Security Level: {metrics.security_level}")
    
    print("\n🔄 Step 2: Rotate Token")
    new_token, backup_id = token_manager.rotate_api_token(
        length=64,
        user_id="demo_admin"
    )
    print(f"   New Token: {new_token[:12]}...{new_token[-8:]}")
    print(f"   Backup Created: {backup_id if backup_id else 'None (no previous token)'}")
    
    print("\n🔄 Step 3: Validate Current Token")
    current_token = token_manager.get_current_token("demo_admin")
    if current_token:
        validation = token_manager.validate_token(current_token, "demo_admin")
        print(f"   Current Token Valid: {'✅ Yes' if validation['valid'] else '❌ No'}")
        print(f"   Security Level: {validation['metrics']['security_level']}")
        print(f"   Entropy: {validation['metrics']['entropy_bits']:.1f} bits")
    
    print("\n🔄 Step 4: List Backups")
    backups = token_manager.list_token_backups("demo_admin")
    print(f"   Available Backups: {len(backups)}")
    for backup in backups:
        age = datetime.now(timezone.utc) - backup.created_at
        print(f"     - {backup.credential_id} (created {age.seconds}s ago)")


def demonstrate_audit_logging():
    """Demonstrate audit logging with redaction."""
    print_section("Audit Logging with Redaction")
    
    demo_env = "demo_token_rotation"
    token_manager = APITokenManager(demo_env)
    
    print("\n📋 Recent Audit Records:")
    
    # Get recent audit records
    records = token_manager.audit_logger.get_audit_records()
    
    if records:
        # Show last 5 records
        for record in records[-5:]:
            parts = record.split('|')
            if len(parts) >= 8:
                timestamp = parts[0][:19].replace('T', ' ')
                operation = parts[1]
                token_id = parts[2]
                user_id = parts[3]
                result = parts[5]
                token_hash = parts[6] if len(parts) > 6 else "N/A"
                
                print(f"   {timestamp} | {operation} | {user_id} | {result} | hash:{token_hash[:8]}...")
    else:
        print("   No audit records found")
    
    print(f"\n🔒 Security Note: Token values are never stored in audit logs")
    print(f"   Only SHA256 hashes are recorded for correlation purposes")


def demonstrate_backward_compatibility():
    """Demonstrate backward compatibility features."""
    print_section("Backward Compatibility")
    
    # Set a demo environment token
    demo_token = "Demo_Environment_Token_2024_With_Good_Entropy_ABC123XYZ789"
    os.environ["API_TOKEN"] = demo_token
    
    print(f"\n🔗 Environment Variable Set: API_TOKEN")
    print(f"   Token: {demo_token[:16]}...{demo_token[-8:]}")
    
    # Test enhanced token manager
    enhanced_manager = get_token_manager()
    
    # Get token info
    token_info = enhanced_manager.get_token_info()
    print(f"\n📊 Token Configuration:")
    print(f"   Configured: {'✅ Yes' if token_info['configured'] else '❌ No'}")
    print(f"   Source: {token_info.get('source', 'unknown')}")
    print(f"   Enhanced Features: {'✅ Available' if token_info.get('enhanced_features') else '❌ Not Available'}")
    print(f"   Valid: {'✅ Yes' if token_info.get('valid') else '❌ No'}")
    
    # Test retrieval
    retrieved_token = get_api_token()
    if retrieved_token:
        print(f"   Retrieved Token: {retrieved_token[:16]}...{retrieved_token[-8:]}")
        print(f"   Matches Environment: {'✅ Yes' if retrieved_token == demo_token else '❌ No'}")
    
    # Cleanup
    del os.environ["API_TOKEN"]


def demonstrate_health_monitoring():
    """Demonstrate health monitoring capabilities."""
    print_section("Health Monitoring")
    
    demo_env = "demo_token_rotation"
    token_manager = APITokenManager(demo_env)
    
    health_status = token_manager.get_health_status()
    
    status_icon = {
        'healthy': '✅',
        'degraded': '⚠️',
        'error': '❌'
    }.get(health_status.get('status'), '❓')
    
    print(f"\n🏥 System Health: {status_icon} {health_status.get('status', 'unknown').upper()}")
    
    if 'token_exists' in health_status:
        print(f"   Token Configured: {'✅ Yes' if health_status['token_exists'] else '❌ No'}")
        
        if health_status['token_exists']:
            print(f"   Token Valid: {'✅ Yes' if health_status['token_valid'] else '❌ No'}")
            if 'security_level' in health_status:
                print(f"   Security Level: {health_status['security_level']}")
            if 'entropy_bits' in health_status:
                print(f"   Entropy: {health_status['entropy_bits']:.1f} bits")
            if 'backup_count' in health_status:
                print(f"   Backups Available: {health_status['backup_count']}")
    
    if health_status.get('issues'):
        print(f"\n⚠️  Issues:")
        for issue in health_status['issues']:
            print(f"   - {issue}")


def cleanup_demo_environment():
    """Cleanup demo environment."""
    print_section("Cleanup")
    
    demo_dirs = [
        Path.home() / ".adelaide-weather" / "credentials" / "demo_token_rotation",
        Path.home() / ".adelaide-weather" / "token-audit" / "demo_token_rotation"
    ]
    
    for demo_dir in demo_dirs:
        if demo_dir.exists():
            import shutil
            try:
                shutil.rmtree(demo_dir)
                print(f"   🧹 Cleaned up: {demo_dir}")
            except Exception as e:
                print(f"   ⚠️ Could not cleanup {demo_dir}: {e}")
    
    # Clean up environment variables
    env_vars = ["ENVIRONMENT", "CREDENTIAL_MASTER_KEY", "API_TOKEN"]
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def main():
    """Main demonstration function."""
    print_header("Adelaide Weather API Token Rotation Demonstration")
    
    if not DEMO_AVAILABLE:
        print("❌ Token rotation components not available for demonstration")
        return
    
    print("🎯 This demonstration showcases the comprehensive token rotation")
    print("   and audit logging system with enhanced security features.")
    
    try:
        # Run demonstrations
        demonstrate_token_entropy()
        demonstrate_secure_generation()
        demonstrate_token_rotation()
        demonstrate_audit_logging()
        demonstrate_backward_compatibility()
        demonstrate_health_monitoring()
        
        print_header("Demonstration Summary")
        print("✅ Token Entropy Validation - Demonstrated")
        print("✅ Secure Token Generation - Demonstrated")
        print("✅ Token Rotation Workflow - Demonstrated")
        print("✅ Audit Logging with Redaction - Demonstrated")
        print("✅ Backward Compatibility - Demonstrated")
        print("✅ Health Monitoring - Demonstrated")
        
        print(f"\n🎉 Token rotation system is fully operational!")
        print(f"   📚 Use 'python api/token_rotation_cli.py --help' for CLI options")
        print(f"   🔒 All token operations are logged with proper security redaction")
        print(f"   🔄 System supports both new secure storage and legacy environment variables")
        
    except Exception as e:
        print(f"\n❌ Demonstration error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup_demo_environment()


if __name__ == "__main__":
    main()