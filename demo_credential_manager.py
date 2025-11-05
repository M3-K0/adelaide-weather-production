#!/usr/bin/env python3
"""
Adelaide Weather Credential Management Demo
=========================================

Demonstration of the secure credential management system for the Adelaide
weather forecasting application. Shows practical usage patterns and integration
with the weather API system.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the core module to path
sys.path.append(str(Path(__file__).parent / "core"))

from core.secure_credential_manager import (
    SecureCredentialManager,
    CredentialType,
    SecurityLevel,
    SecurityViolationError,
    CredentialNotFoundError
)


def demo_basic_credential_operations():
    """Demonstrate basic credential operations."""
    print("=== Basic Credential Operations Demo ===\n")
    
    # Initialize credential manager for development environment
    os.environ["ADELAIDE_WEATHER_MASTER_KEY"] = "dev-master-key-for-demonstration-only"
    
    credential_manager = SecureCredentialManager(
        environment="development",
        master_key_env="ADELAIDE_WEATHER_MASTER_KEY"
    )
    
    print("1. Storing weather API credentials...")
    
    # Store weather API credentials
    credentials_to_store = [
        {
            "id": "openweather_api_key",
            "value": "your-openweather-api-key-here",
            "type": CredentialType.API_KEY,
            "security_level": SecurityLevel.STANDARD,
            "tags": {"service": "openweather", "environment": "dev"}
        },
        {
            "id": "database_password", 
            "value": "secure-postgres-password-123",
            "type": CredentialType.DATABASE_PASSWORD,
            "security_level": SecurityLevel.HIGH,
            "tags": {"service": "postgresql", "database": "weather_data"}
        },
        {
            "id": "jwt_signing_secret",
            "value": "super-secret-jwt-signing-key-do-not-share",
            "type": CredentialType.JWT_SECRET,
            "security_level": SecurityLevel.CRITICAL,
            "expires_at": datetime.utcnow() + timedelta(days=90),
            "tags": {"service": "authentication", "rotation_period": "90days"}
        },
        {
            "id": "session_encryption_key",
            "value": "ephemeral-session-key-for-runtime-only",
            "type": CredentialType.SESSION_SECRET,
            "security_level": SecurityLevel.EPHEMERAL,
            "tags": {"service": "web_sessions", "temporary": "true"}
        }
    ]
    
    for cred in credentials_to_store:
        try:
            credential_manager.store_credential(
                credential_id=cred["id"],
                credential_value=cred["value"],
                credential_type=cred["type"],
                security_level=cred["security_level"],
                expires_at=cred.get("expires_at"),
                tags=cred["tags"],
                user_id="demo_user"
            )
            print(f"✓ Stored {cred['id']} with {cred['security_level'].name} security")
        except Exception as e:
            print(f"✗ Failed to store {cred['id']}: {e}")
    
    print("\n2. Retrieving credentials...")
    
    # Demonstrate credential retrieval
    credentials_to_retrieve = ["openweather_api_key", "database_password", "jwt_signing_secret"]
    
    for cred_id in credentials_to_retrieve:
        try:
            # Using secure context manager (recommended)
            with credential_manager.secure_context(cred_id, "demo_user") as credential_value:
                print(f"✓ Retrieved {cred_id}: {credential_value[:10]}...{credential_value[-5:]}")
                # Credential is automatically cleared after this block
        except Exception as e:
            print(f"✗ Failed to retrieve {cred_id}: {e}")
    
    print("\n3. Listing stored credentials...")
    
    # List all credentials
    all_credentials = credential_manager.list_credentials()
    print(f"Total credentials: {len(all_credentials)}")
    
    for metadata in all_credentials:
        status = "EXPIRED" if metadata.expires_at and datetime.utcnow() > metadata.expires_at else "ACTIVE"
        rotation = "NEEDS ROTATION" if metadata.rotation_required else "OK"
        print(f"  - {metadata.credential_id}: {metadata.credential_type.value} "
              f"({metadata.security_level.name}) [{status}] [{rotation}]")
    
    return credential_manager


def demo_security_features(credential_manager):
    """Demonstrate advanced security features."""
    print("\n=== Advanced Security Features Demo ===\n")
    
    print("1. Security level filtering...")
    
    # Filter by security level
    critical_credentials = credential_manager.list_credentials(
        security_level=SecurityLevel.CRITICAL
    )
    print(f"Critical security credentials: {len(critical_credentials)}")
    for cred in critical_credentials:
        print(f"  - {cred.credential_id}")
    
    print("\n2. Credential rotation...")
    
    # Mark credential for rotation
    try:
        credential_manager.mark_for_rotation("jwt_signing_secret", "security_admin")
        print("✓ Marked JWT signing secret for rotation")
        
        # Perform rotation
        new_jwt_secret = "new-super-secret-jwt-signing-key-rotated"
        credential_manager.rotate_credential("jwt_signing_secret", new_jwt_secret, "security_admin")
        print("✓ Rotated JWT signing secret")
        
        # Verify new value
        with credential_manager.secure_context("jwt_signing_secret") as new_value:
            print(f"✓ Verified new JWT secret: {new_value[:15]}...")
            
    except Exception as e:
        print(f"✗ Rotation failed: {e}")
    
    print("\n3. Rate limiting demonstration...")
    
    try:
        # Store a test credential
        credential_manager.store_credential(
            credential_id="rate_limit_test",
            credential_value="test-secret-for-rate-limiting",
            credential_type=CredentialType.API_KEY
        )
        
        # Attempt many rapid accesses
        print("Attempting rapid access to test rate limiting...")
        access_count = 0
        
        for i in range(credential_manager.MAX_ACCESS_ATTEMPTS + 5):
            try:
                credential_manager.retrieve_credential("rate_limit_test")
                access_count += 1
            except SecurityViolationError as e:
                if "Rate limit exceeded" in str(e):
                    print(f"✓ Rate limit triggered after {access_count} accesses")
                    break
                else:
                    raise
        
    except Exception as e:
        print(f"✗ Rate limiting test failed: {e}")
    
    print("\n4. Audit trail examination...")
    
    # Get audit trail
    audit_entries = credential_manager.get_audit_trail(
        credential_id="jwt_signing_secret"
    )
    print(f"Audit entries for JWT signing secret: {len(audit_entries)}")
    
    for entry in audit_entries[-3:]:  # Show last 3 entries
        parts = entry.split('|')
        if len(parts) >= 7:
            timestamp = parts[0]
            event_type = parts[2]
            user_id = parts[4]
            result = parts[6]
            print(f"  - {timestamp} | {event_type} | {user_id} | {result}")


def demo_weather_api_integration(credential_manager):
    """Demonstrate integration with weather API components."""
    print("\n=== Weather API Integration Demo ===\n")
    
    print("1. Setting up weather service credentials...")
    
    # Weather service specific credentials
    weather_credentials = [
        {
            "id": "gfs_data_api_key",
            "value": "gfs-weather-data-api-key-12345",
            "type": CredentialType.API_KEY,
            "tags": {"service": "gfs", "data_source": "noaa"}
        },
        {
            "id": "era5_access_token",
            "value": "era5-copernicus-access-token-67890",
            "type": CredentialType.SERVICE_TOKEN,
            "tags": {"service": "era5", "data_source": "copernicus"}
        },
        {
            "id": "redis_connection_password",
            "value": "redis-cache-password-for-forecasts",
            "type": CredentialType.DATABASE_PASSWORD,
            "security_level": SecurityLevel.HIGH,
            "tags": {"service": "redis", "purpose": "forecast_cache"}
        },
        {
            "id": "webhook_verification_secret",
            "value": "webhook-secret-for-forecast-notifications",
            "type": CredentialType.WEBHOOK_SECRET,
            "tags": {"service": "notifications", "purpose": "webhook_verification"}
        }
    ]
    
    for cred in weather_credentials:
        try:
            credential_manager.store_credential(
                credential_id=cred["id"],
                credential_value=cred["value"],
                credential_type=cred["type"],
                security_level=cred.get("security_level", SecurityLevel.STANDARD),
                tags=cred["tags"],
                user_id="weather_service"
            )
            print(f"✓ Stored {cred['id']} for weather service")
        except Exception as e:
            print(f"✗ Failed to store {cred['id']}: {e}")
    
    print("\n2. Simulating weather API credential usage...")
    
    def simulate_weather_data_fetch():
        """Simulate fetching weather data with credentials."""
        try:
            # Get GFS API credentials
            with credential_manager.secure_context("gfs_data_api_key") as api_key:
                print(f"📡 Fetching GFS data with API key: {api_key[:8]}...")
                # In real application, would use this key for HTTP requests
                
            # Get Redis connection credentials
            with credential_manager.secure_context("redis_connection_password") as redis_password:
                print(f"🔄 Connecting to Redis cache with password: {redis_password[:6]}...")
                # In real application, would connect to Redis
                
            print("✓ Weather data fetch simulation completed")
            
        except Exception as e:
            print(f"✗ Weather data fetch failed: {e}")
    
    simulate_weather_data_fetch()
    
    print("\n3. Credential management by service type...")
    
    # Group credentials by service
    all_credentials = credential_manager.list_credentials()
    services = {}
    
    for cred in all_credentials:
        service = cred.tags.get("service", "unknown")
        if service not in services:
            services[service] = []
        services[service].append(cred)
    
    print("Credentials grouped by service:")
    for service, creds in services.items():
        print(f"  {service}:")
        for cred in creds:
            print(f"    - {cred.credential_id} ({cred.credential_type.value})")


def demo_health_and_maintenance(credential_manager):
    """Demonstrate health monitoring and maintenance features."""
    print("\n=== Health Monitoring and Maintenance Demo ===\n")
    
    print("1. System health check...")
    
    health_status = credential_manager.health_check()
    print(f"System status: {health_status['status']}")
    print(f"Environment: {health_status['environment']}")
    print(f"Total credentials: {health_status['credential_count']}")
    print(f"Ephemeral credentials: {health_status['ephemeral_count']}")
    print(f"Storage accessible: {health_status['storage_accessible']}")
    print(f"Audit logging: {health_status['audit_logging']}")
    
    if health_status['issues']:
        print("Issues detected:")
        for issue in health_status['issues']:
            print(f"  ⚠️  {issue}")
    else:
        print("✓ No issues detected")
    
    print("\n2. Credential expiration management...")
    
    # Create an expired credential for demonstration
    try:
        past_time = datetime.utcnow() - timedelta(minutes=1)
        credential_manager.store_credential(
            credential_id="expired_demo_credential",
            credential_value="this-credential-is-expired",
            credential_type=CredentialType.API_KEY,
            expires_at=past_time
        )
        print("✓ Created expired credential for demo")
        
        # Attempt to access expired credential
        try:
            credential_manager.retrieve_credential("expired_demo_credential")
        except CredentialExpiredError:
            print("✓ Expired credential access correctly blocked")
        
        # Cleanup expired credentials
        cleaned_count = credential_manager.cleanup_expired_credentials()
        print(f"✓ Cleaned up {cleaned_count} expired credential(s)")
        
    except Exception as e:
        print(f"✗ Expiration management demo failed: {e}")
    
    print("\n3. Audit trail analysis...")
    
    # Get recent audit entries
    recent_entries = credential_manager.get_audit_trail()[-10:]  # Last 10 entries
    print(f"Recent audit entries ({len(recent_entries)} shown):")
    
    for entry in recent_entries:
        parts = entry.split('|')
        if len(parts) >= 7:
            timestamp = parts[0].split('T')[1][:8]  # Time only
            event_type = parts[2]
            credential_id = parts[3][:20]  # Truncate long IDs
            result = parts[6]
            print(f"  {timestamp} | {event_type:15} | {credential_id:20} | {result}")


def demo_error_handling():
    """Demonstrate comprehensive error handling."""
    print("\n=== Error Handling Demo ===\n")
    
    # Initialize a fresh credential manager
    os.environ["DEMO_MASTER_KEY"] = "demo-error-handling-key"
    
    credential_manager = SecureCredentialManager(
        environment="demo",
        master_key_env="DEMO_MASTER_KEY"
    )
    
    print("1. Testing various error conditions...")
    
    # Test duplicate credential
    try:
        credential_manager.store_credential(
            credential_id="duplicate_test",
            credential_value="first-value",
            credential_type=CredentialType.API_KEY
        )
        
        credential_manager.store_credential(
            credential_id="duplicate_test",
            credential_value="second-value",
            credential_type=CredentialType.API_KEY
        )
    except SecurityViolationError as e:
        print(f"✓ Duplicate credential properly rejected: {e}")
    
    # Test oversized credential
    try:
        oversized_value = "x" * (65 * 1024)  # 65KB
        credential_manager.store_credential(
            credential_id="oversized_test",
            credential_value=oversized_value,
            credential_type=CredentialType.API_KEY
        )
    except SecurityViolationError as e:
        print(f"✓ Oversized credential properly rejected: {e}")
    
    # Test non-existent credential
    try:
        credential_manager.retrieve_credential("nonexistent_credential")
    except CredentialNotFoundError as e:
        print(f"✓ Non-existent credential properly handled: {e}")
    
    # Test invalid input
    try:
        credential_manager.store_credential(
            credential_id="",
            credential_value="valid-value",
            credential_type=CredentialType.API_KEY
        )
    except ValueError as e:
        print(f"✓ Invalid input properly rejected: {e}")
    
    print("\n2. Testing security violation scenarios...")
    
    # Store a credential and trigger rate limiting
    credential_manager.store_credential(
        credential_id="rate_limit_victim",
        credential_value="will-be-rate-limited",
        credential_type=CredentialType.API_KEY
    )
    
    # Exhaust rate limit
    try:
        for i in range(credential_manager.MAX_ACCESS_ATTEMPTS + 1):
            credential_manager.retrieve_credential("rate_limit_victim")
    except SecurityViolationError as e:
        if "Rate limit exceeded" in str(e):
            print(f"✓ Rate limiting properly enforced: {e}")
    
    print("✓ Error handling demonstration completed")


def main():
    """Main demonstration function."""
    print("Adelaide Weather Forecasting System")
    print("Secure Credential Management Demo")
    print("=" * 50)
    
    try:
        # Run comprehensive demonstrations
        credential_manager = demo_basic_credential_operations()
        demo_security_features(credential_manager)
        demo_weather_api_integration(credential_manager)
        demo_health_and_maintenance(credential_manager)
        demo_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ All demonstrations completed successfully!")
        print("\nThe secure credential management system is ready for use")
        print("in the Adelaide weather forecasting application.")
        
        # Final system status
        final_health = credential_manager.health_check()
        print(f"\nFinal system status: {final_health['status']}")
        print(f"Total credentials managed: {final_health['credential_count']}")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())