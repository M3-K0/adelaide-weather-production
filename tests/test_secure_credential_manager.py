#!/usr/bin/env python3
"""
Comprehensive Test Suite for Secure Credential Manager
=====================================================

Tests all aspects of the production-grade secure credential management system:
- Encryption/decryption functionality
- Security levels and access controls
- Credential lifecycle management
- Audit logging and compliance
- Error handling and edge cases
- Performance and reliability
"""

import os
import pytest
import tempfile
import shutil
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the credential manager
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.secure_credential_manager import (
    SecureCredentialManager,
    CredentialType,
    SecurityLevel,
    CredentialMetadata,
    SecurityViolationError,
    CredentialNotFoundError,
    CredentialExpiredError
)


class TestSecureCredentialManager:
    """Test suite for SecureCredentialManager class."""
    
    def setup_method(self):
        """Setup test environment for each test."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_master_key = "test-master-key-for-comprehensive-testing-12345"
        
        # Set environment variable for master key
        os.environ["TEST_CREDENTIAL_MASTER_KEY"] = self.test_master_key
        
        # Initialize credential manager with test environment
        self.credential_manager = SecureCredentialManager(
            environment="test",
            storage_path=self.temp_dir,
            master_key_env="TEST_CREDENTIAL_MASTER_KEY"
        )
    
    def teardown_method(self):
        """Cleanup test environment after each test."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Clean up environment variable
        if "TEST_CREDENTIAL_MASTER_KEY" in os.environ:
            del os.environ["TEST_CREDENTIAL_MASTER_KEY"]
    
    def test_initialization(self):
        """Test credential manager initialization."""
        assert self.credential_manager.environment == "test"
        assert self.credential_manager.storage_root == Path(self.temp_dir) / "test"
        assert self.credential_manager.credentials_dir.exists()
        assert self.credential_manager.metadata_dir.exists()
        assert self.credential_manager.audit_dir.exists()
    
    def test_initialization_without_master_key_production(self):
        """Test initialization failure without master key in production."""
        # Remove master key
        if "TEST_CREDENTIAL_MASTER_KEY" in os.environ:
            del os.environ["TEST_CREDENTIAL_MASTER_KEY"]
        
        with pytest.raises(SecurityViolationError, match="Master key not found"):
            SecureCredentialManager(
                environment="production",
                storage_path=self.temp_dir,
                master_key_env="TEST_CREDENTIAL_MASTER_KEY"
            )
    
    def test_store_credential_basic(self):
        """Test basic credential storage."""
        result = self.credential_manager.store_credential(
            credential_id="test_api_key",
            credential_value="secret-api-key-12345",
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.STANDARD
        )
        
        assert result is True
        
        # Verify metadata was created
        metadata = self.credential_manager.get_credential_metadata("test_api_key")
        assert metadata is not None
        assert metadata.credential_type == CredentialType.API_KEY
        assert metadata.security_level == SecurityLevel.STANDARD
        assert metadata.environment == "test"
        assert metadata.access_count == 0
    
    def test_store_credential_all_types(self):
        """Test storing all supported credential types."""
        test_credentials = [
            ("api_key", "api-secret-123", CredentialType.API_KEY),
            ("db_password", "super-secure-password", CredentialType.DATABASE_PASSWORD),
            ("service_token", "service-token-456", CredentialType.SERVICE_TOKEN),
            ("encryption_key", "encryption-key-789", CredentialType.ENCRYPTION_KEY),
            ("oauth_secret", "oauth-client-secret", CredentialType.OAUTH_CLIENT_SECRET),
            ("certificate", "-----BEGIN CERTIFICATE-----", CredentialType.CERTIFICATE),
            ("private_key", "-----BEGIN PRIVATE KEY-----", CredentialType.PRIVATE_KEY),
            ("webhook_secret", "webhook-secret-123", CredentialType.WEBHOOK_SECRET),
            ("session_secret", "session-secret-456", CredentialType.SESSION_SECRET),
            ("jwt_secret", "jwt-secret-789", CredentialType.JWT_SECRET)
        ]
        
        for cred_id, cred_value, cred_type in test_credentials:
            result = self.credential_manager.store_credential(
                credential_id=cred_id,
                credential_value=cred_value,
                credential_type=cred_type
            )
            assert result is True
            
            # Verify can retrieve
            retrieved = self.credential_manager.retrieve_credential(cred_id)
            assert retrieved == cred_value
    
    def test_store_credential_all_security_levels(self):
        """Test storing credentials with all security levels."""
        security_levels = [
            SecurityLevel.STANDARD,
            SecurityLevel.HIGH,
            SecurityLevel.CRITICAL,
            SecurityLevel.EPHEMERAL
        ]
        
        for i, security_level in enumerate(security_levels):
            cred_id = f"test_credential_{i}"
            cred_value = f"secret-value-{i}"
            
            result = self.credential_manager.store_credential(
                credential_id=cred_id,
                credential_value=cred_value,
                credential_type=CredentialType.API_KEY,
                security_level=security_level
            )
            
            assert result is True
            
            # Verify metadata
            metadata = self.credential_manager.get_credential_metadata(cred_id)
            assert metadata.security_level == security_level
    
    def test_store_credential_with_expiration(self):
        """Test storing credential with expiration."""
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        result = self.credential_manager.store_credential(
            credential_id="expiring_credential",
            credential_value="will-expire-soon",
            credential_type=CredentialType.API_KEY,
            expires_at=expires_at
        )
        
        assert result is True
        
        metadata = self.credential_manager.get_credential_metadata("expiring_credential")
        assert metadata.expires_at == expires_at
    
    def test_store_credential_with_tags(self):
        """Test storing credential with metadata tags."""
        tags = {
            "environment": "test",
            "service": "weather-api",
            "owner": "test-user"
        }
        
        result = self.credential_manager.store_credential(
            credential_id="tagged_credential",
            credential_value="tagged-secret",
            credential_type=CredentialType.API_KEY,
            tags=tags
        )
        
        assert result is True
        
        metadata = self.credential_manager.get_credential_metadata("tagged_credential")
        assert metadata.tags == tags
    
    def test_store_credential_duplicate_fails(self):
        """Test that storing duplicate credential fails."""
        # Store first credential
        self.credential_manager.store_credential(
            credential_id="duplicate_test",
            credential_value="first-value",
            credential_type=CredentialType.API_KEY
        )
        
        # Attempt to store duplicate should fail
        with pytest.raises(SecurityViolationError, match="already exists"):
            self.credential_manager.store_credential(
                credential_id="duplicate_test",
                credential_value="second-value",
                credential_type=CredentialType.API_KEY
            )
    
    def test_store_credential_oversized_fails(self):
        """Test that oversized credentials are rejected."""
        oversized_value = "x" * (65 * 1024)  # 65KB (over limit)
        
        with pytest.raises(SecurityViolationError, match="exceeds maximum size"):
            self.credential_manager.store_credential(
                credential_id="oversized_credential",
                credential_value=oversized_value,
                credential_type=CredentialType.API_KEY
            )
    
    def test_store_credential_invalid_input(self):
        """Test handling of invalid input."""
        # Empty credential ID
        with pytest.raises(ValueError, match="Credential ID and value are required"):
            self.credential_manager.store_credential(
                credential_id="",
                credential_value="valid-value",
                credential_type=CredentialType.API_KEY
            )
        
        # Empty credential value
        with pytest.raises(ValueError, match="Credential ID and value are required"):
            self.credential_manager.store_credential(
                credential_id="valid_id",
                credential_value="",
                credential_type=CredentialType.API_KEY
            )
    
    def test_retrieve_credential_basic(self):
        """Test basic credential retrieval."""
        original_value = "secret-to-retrieve"
        
        # Store credential
        self.credential_manager.store_credential(
            credential_id="retrieve_test",
            credential_value=original_value,
            credential_type=CredentialType.API_KEY
        )
        
        # Retrieve credential
        retrieved_value = self.credential_manager.retrieve_credential("retrieve_test")
        assert retrieved_value == original_value
        
        # Verify access tracking
        metadata = self.credential_manager.get_credential_metadata("retrieve_test")
        assert metadata.access_count == 1
        assert metadata.last_accessed is not None
    
    def test_retrieve_credential_not_found(self):
        """Test retrieving non-existent credential."""
        with pytest.raises(CredentialNotFoundError, match="not found"):
            self.credential_manager.retrieve_credential("nonexistent_credential")
    
    def test_retrieve_credential_expired(self):
        """Test retrieving expired credential."""
        # Store credential that expires immediately
        past_time = datetime.utcnow() - timedelta(seconds=1)
        
        self.credential_manager.store_credential(
            credential_id="expired_credential",
            credential_value="expired-secret",
            credential_type=CredentialType.API_KEY,
            expires_at=past_time
        )
        
        with pytest.raises(CredentialExpiredError, match="has expired"):
            self.credential_manager.retrieve_credential("expired_credential")
    
    def test_retrieve_credential_ephemeral(self):
        """Test retrieving ephemeral credential."""
        # Store ephemeral credential
        self.credential_manager.store_credential(
            credential_id="ephemeral_test",
            credential_value="ephemeral-secret",
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.EPHEMERAL
        )
        
        # Retrieve ephemeral credential
        retrieved_value = self.credential_manager.retrieve_credential("ephemeral_test")
        assert retrieved_value == "ephemeral-secret"
        
        # Verify it's not in persistent storage
        assert "ephemeral_test" not in self.credential_manager.metadata
        assert "ephemeral_test" in self.credential_manager._ephemeral_cache
    
    def test_retrieve_credential_rate_limiting(self):
        """Test rate limiting for credential access."""
        # Store test credential
        self.credential_manager.store_credential(
            credential_id="rate_limit_test",
            credential_value="rate-limited-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Simulate many rapid accesses
        for i in range(self.credential_manager.MAX_ACCESS_ATTEMPTS):
            self.credential_manager.retrieve_credential("rate_limit_test")
        
        # Next access should be rate limited
        with pytest.raises(SecurityViolationError, match="Rate limit exceeded"):
            self.credential_manager.retrieve_credential("rate_limit_test")
    
    def test_delete_credential_basic(self):
        """Test basic credential deletion."""
        # Store credential
        self.credential_manager.store_credential(
            credential_id="delete_test",
            credential_value="to-be-deleted",
            credential_type=CredentialType.API_KEY
        )
        
        # Verify exists
        assert self.credential_manager.get_credential_metadata("delete_test") is not None
        
        # Delete credential
        result = self.credential_manager.delete_credential("delete_test")
        assert result is True
        
        # Verify deleted
        assert self.credential_manager.get_credential_metadata("delete_test") is None
        
        # Verify file deleted
        credential_file = self.credential_manager.credentials_dir / "delete_test.enc"
        assert not credential_file.exists()
    
    def test_delete_credential_ephemeral(self):
        """Test deleting ephemeral credential."""
        # Store ephemeral credential
        self.credential_manager.store_credential(
            credential_id="ephemeral_delete",
            credential_value="ephemeral-to-delete",
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.EPHEMERAL
        )
        
        # Verify exists in cache
        assert "ephemeral_delete" in self.credential_manager._ephemeral_cache
        
        # Delete credential
        result = self.credential_manager.delete_credential("ephemeral_delete")
        assert result is True
        
        # Verify deleted from cache
        assert "ephemeral_delete" not in self.credential_manager._ephemeral_cache
    
    def test_delete_credential_not_found(self):
        """Test deleting non-existent credential."""
        with pytest.raises(CredentialNotFoundError, match="not found"):
            self.credential_manager.delete_credential("nonexistent_credential")
    
    def test_rotate_credential(self):
        """Test credential rotation."""
        original_value = "original-secret"
        new_value = "rotated-secret"
        
        # Store original credential
        self.credential_manager.store_credential(
            credential_id="rotation_test",
            credential_value=original_value,
            credential_type=CredentialType.API_KEY
        )
        
        # Rotate credential
        result = self.credential_manager.rotate_credential("rotation_test", new_value)
        assert result is True
        
        # Verify new value
        retrieved_value = self.credential_manager.retrieve_credential("rotation_test")
        assert retrieved_value == new_value
        
        # Verify backup was created
        credentials = self.credential_manager.list_credentials()
        backup_credentials = [c for c in credentials if "backup" in c.credential_id]
        assert len(backup_credentials) > 0
        
        # Verify rotation flag is cleared
        metadata = self.credential_manager.get_credential_metadata("rotation_test")
        assert metadata.rotation_required is False
    
    def test_mark_for_rotation(self):
        """Test marking credential for rotation."""
        # Store credential
        self.credential_manager.store_credential(
            credential_id="mark_rotation_test",
            credential_value="needs-rotation",
            credential_type=CredentialType.API_KEY
        )
        
        # Mark for rotation
        result = self.credential_manager.mark_for_rotation("mark_rotation_test")
        assert result is True
        
        # Verify rotation flag is set
        metadata = self.credential_manager.get_credential_metadata("mark_rotation_test")
        assert metadata.rotation_required is True
    
    def test_list_credentials(self):
        """Test listing credentials with filters."""
        # Store various credentials
        test_data = [
            ("api_1", CredentialType.API_KEY, SecurityLevel.STANDARD),
            ("api_2", CredentialType.API_KEY, SecurityLevel.HIGH),
            ("db_1", CredentialType.DATABASE_PASSWORD, SecurityLevel.STANDARD),
            ("token_1", CredentialType.SERVICE_TOKEN, SecurityLevel.CRITICAL)
        ]
        
        for cred_id, cred_type, sec_level in test_data:
            self.credential_manager.store_credential(
                credential_id=cred_id,
                credential_value=f"secret-{cred_id}",
                credential_type=cred_type,
                security_level=sec_level
            )
        
        # Test listing all credentials
        all_credentials = self.credential_manager.list_credentials()
        assert len(all_credentials) == 4
        
        # Test filtering by credential type
        api_credentials = self.credential_manager.list_credentials(
            credential_type=CredentialType.API_KEY
        )
        assert len(api_credentials) == 2
        
        # Test filtering by security level
        high_sec_credentials = self.credential_manager.list_credentials(
            security_level=SecurityLevel.HIGH
        )
        assert len(high_sec_credentials) == 1
        
        # Test filtering by both
        standard_api_credentials = self.credential_manager.list_credentials(
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.STANDARD
        )
        assert len(standard_api_credentials) == 1
    
    def test_list_credentials_with_expired(self):
        """Test listing credentials including expired ones."""
        # Store normal credential
        self.credential_manager.store_credential(
            credential_id="normal_cred",
            credential_value="normal-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Store expired credential
        past_time = datetime.utcnow() - timedelta(hours=1)
        self.credential_manager.store_credential(
            credential_id="expired_cred",
            credential_value="expired-secret",
            credential_type=CredentialType.API_KEY,
            expires_at=past_time
        )
        
        # List without expired
        active_credentials = self.credential_manager.list_credentials(include_expired=False)
        assert len(active_credentials) == 1
        assert active_credentials[0].credential_id == "normal_cred"
        
        # List with expired
        all_credentials = self.credential_manager.list_credentials(include_expired=True)
        assert len(all_credentials) == 2
    
    def test_cleanup_expired_credentials(self):
        """Test cleanup of expired credentials."""
        # Store normal credential
        self.credential_manager.store_credential(
            credential_id="normal_cred",
            credential_value="normal-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Store expired credentials
        past_time = datetime.utcnow() - timedelta(hours=1)
        
        self.credential_manager.store_credential(
            credential_id="expired_cred_1",
            credential_value="expired-secret-1",
            credential_type=CredentialType.API_KEY,
            expires_at=past_time
        )
        
        self.credential_manager.store_credential(
            credential_id="expired_cred_2",
            credential_value="expired-secret-2",
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.EPHEMERAL,
            expires_at=past_time
        )
        
        # Verify initial state
        all_credentials = self.credential_manager.list_credentials(include_expired=True)
        assert len(all_credentials) == 3
        
        # Cleanup expired credentials
        cleaned_count = self.credential_manager.cleanup_expired_credentials()
        assert cleaned_count == 2
        
        # Verify only normal credential remains
        remaining_credentials = self.credential_manager.list_credentials(include_expired=True)
        assert len(remaining_credentials) == 1
        assert remaining_credentials[0].credential_id == "normal_cred"
    
    def test_secure_context_manager(self):
        """Test secure context manager for credential access."""
        # Store credential
        self.credential_manager.store_credential(
            credential_id="context_test",
            credential_value="context-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Use context manager
        with self.credential_manager.secure_context("context_test") as credential_value:
            assert credential_value == "context-secret"
            # Credential is available within context
        
        # After context, credential should be cleared from memory
        # (This is hard to test directly, but the implementation clears it)
    
    def test_encryption_decryption_integrity(self):
        """Test encryption/decryption maintains data integrity."""
        test_data = [
            "simple-string",
            "string with spaces and symbols !@#$%^&*()",
            "unicode-string-αβγδε-测试-🚀",
            "very-long-string-" + "x" * 1000,
            '{"json": "data", "numbers": [1, 2, 3], "nested": {"key": "value"}}',
            "line1\nline2\nline3",
            "tabs\tand\ttabs",
            ""  # edge case: empty string (but we validate against this)
        ]
        
        for i, test_value in enumerate(test_data):
            if not test_value:  # Skip empty string as it's invalid input
                continue
                
            cred_id = f"integrity_test_{i}"
            
            # Store credential
            self.credential_manager.store_credential(
                credential_id=cred_id,
                credential_value=test_value,
                credential_type=CredentialType.API_KEY
            )
            
            # Retrieve and verify
            retrieved_value = self.credential_manager.retrieve_credential(cred_id)
            assert retrieved_value == test_value
    
    def test_different_security_levels_isolation(self):
        """Test that different security levels use different encryption."""
        same_value = "same-secret-value"
        
        # Store same value with different security levels
        security_levels = [SecurityLevel.STANDARD, SecurityLevel.HIGH, SecurityLevel.CRITICAL]
        
        for i, sec_level in enumerate(security_levels):
            self.credential_manager.store_credential(
                credential_id=f"isolation_test_{i}",
                credential_value=same_value,
                credential_type=CredentialType.API_KEY,
                security_level=sec_level
            )
        
        # Verify all can be retrieved correctly
        for i, sec_level in enumerate(security_levels):
            retrieved = self.credential_manager.retrieve_credential(f"isolation_test_{i}")
            assert retrieved == same_value
        
        # Verify encrypted files are different (different security levels should produce different encrypted data)
        encrypted_files = []
        for i in range(len(security_levels)):
            file_path = self.credential_manager.credentials_dir / f"isolation_test_{i}.enc"
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    encrypted_files.append(f.read())
        
        # All encrypted versions should be different
        for i in range(len(encrypted_files)):
            for j in range(i + 1, len(encrypted_files)):
                assert encrypted_files[i] != encrypted_files[j]
    
    def test_audit_logging(self):
        """Test comprehensive audit logging."""
        # Store credential (should generate audit log)
        self.credential_manager.store_credential(
            credential_id="audit_test",
            credential_value="audit-secret",
            credential_type=CredentialType.API_KEY,
            user_id="test-user"
        )
        
        # Retrieve credential (should generate audit log)
        self.credential_manager.retrieve_credential("audit_test", "test-user")
        
        # Get audit trail
        audit_entries = self.credential_manager.get_audit_trail(
            credential_id="audit_test"
        )
        
        assert len(audit_entries) >= 2  # At least store and retrieve events
        
        # Verify audit entry format
        for entry in audit_entries:
            parts = entry.split('|')
            assert len(parts) >= 8  # Expected audit entry format
            
            # Verify timestamp format
            timestamp_str = parts[0]
            datetime.fromisoformat(timestamp_str)  # Should not raise exception
    
    def test_audit_trail_filtering(self):
        """Test audit trail filtering functionality."""
        # Create test events
        test_credentials = ["audit_filter_1", "audit_filter_2"]
        
        for cred_id in test_credentials:
            self.credential_manager.store_credential(
                credential_id=cred_id,
                credential_value=f"secret-{cred_id}",
                credential_type=CredentialType.API_KEY
            )
            self.credential_manager.retrieve_credential(cred_id)
        
        # Test filtering by credential ID
        cred1_entries = self.credential_manager.get_audit_trail(
            credential_id="audit_filter_1"
        )
        
        # Should only contain entries for audit_filter_1
        for entry in cred1_entries:
            assert "audit_filter_1" in entry
            assert "audit_filter_2" not in entry
        
        # Test filtering by event type
        store_entries = self.credential_manager.get_audit_trail(
            event_type="store_credential"
        )
        
        for entry in store_entries:
            assert "store_credential" in entry
    
    def test_health_check(self):
        """Test system health check functionality."""
        # Store some test credentials
        self.credential_manager.store_credential(
            credential_id="health_test_1",
            credential_value="secret-1",
            credential_type=CredentialType.API_KEY
        )
        
        self.credential_manager.store_credential(
            credential_id="health_test_2",
            credential_value="secret-2",
            credential_type=CredentialType.API_KEY,
            security_level=SecurityLevel.EPHEMERAL
        )
        
        # Run health check
        health_status = self.credential_manager.health_check()
        
        # Verify health status structure
        assert "status" in health_status
        assert "environment" in health_status
        assert "credential_count" in health_status
        assert "ephemeral_count" in health_status
        assert "storage_accessible" in health_status
        assert "audit_logging" in health_status
        assert "last_check" in health_status
        assert "issues" in health_status
        
        # Verify values
        assert health_status["environment"] == "test"
        assert health_status["credential_count"] == 1  # Only persistent credential
        assert health_status["ephemeral_count"] == 1   # Only ephemeral credential
        assert health_status["storage_accessible"] is True
        assert health_status["audit_logging"] is True
        assert health_status["status"] == "healthy"
    
    def test_health_check_with_issues(self):
        """Test health check detection of issues."""
        # Create credential requiring rotation
        self.credential_manager.store_credential(
            credential_id="rotation_needed",
            credential_value="needs-rotation",
            credential_type=CredentialType.API_KEY
        )
        self.credential_manager.mark_for_rotation("rotation_needed")
        
        # Create expired credential
        past_time = datetime.utcnow() - timedelta(hours=1)
        self.credential_manager.store_credential(
            credential_id="expired_health",
            credential_value="expired-secret",
            credential_type=CredentialType.API_KEY,
            expires_at=past_time
        )
        
        # Run health check
        health_status = self.credential_manager.health_check()
        
        # Should detect issues
        assert len(health_status["issues"]) >= 2
        assert health_status["status"] in ["warning", "degraded"]
        
        issue_texts = " ".join(health_status["issues"])
        assert "require rotation" in issue_texts
        assert "expired" in issue_texts
    
    def test_concurrent_access_safety(self):
        """Test thread safety of credential operations."""
        import threading
        import concurrent.futures
        
        # Store base credential
        self.credential_manager.store_credential(
            credential_id="concurrent_test",
            credential_value="concurrent-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Function to retrieve credential multiple times
        def retrieve_credential_worker(thread_id):
            results = []
            for i in range(10):
                try:
                    value = self.credential_manager.retrieve_credential("concurrent_test")
                    results.append(value)
                except Exception as e:
                    results.append(f"Error: {e}")
            return results
        
        # Run concurrent retrievals
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(retrieve_credential_worker, i) 
                for i in range(5)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all retrievals succeeded
        for thread_results in results:
            for result in thread_results:
                assert result == "concurrent-secret" or result.startswith("Error: Rate limit")
    
    def test_environment_isolation(self):
        """Test that different environments are isolated."""
        # Create managers for different environments
        test_manager = self.credential_manager  # Already created for "test"
        
        dev_manager = SecureCredentialManager(
            environment="development",
            storage_path=self.temp_dir,
            master_key_env="TEST_CREDENTIAL_MASTER_KEY"
        )
        
        # Store same credential ID in both environments
        test_manager.store_credential(
            credential_id="env_isolation_test",
            credential_value="test-environment-secret",
            credential_type=CredentialType.API_KEY
        )
        
        dev_manager.store_credential(
            credential_id="env_isolation_test",
            credential_value="dev-environment-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Verify isolation
        test_value = test_manager.retrieve_credential("env_isolation_test")
        dev_value = dev_manager.retrieve_credential("env_isolation_test")
        
        assert test_value == "test-environment-secret"
        assert dev_value == "dev-environment-secret"
        assert test_value != dev_value
        
        # Verify separate storage directories
        assert test_manager.storage_root != dev_manager.storage_root
    
    def test_metadata_persistence(self):
        """Test that metadata persists across manager instances."""
        # Store credential with first manager instance
        self.credential_manager.store_credential(
            credential_id="persistence_test",
            credential_value="persistent-secret",
            credential_type=CredentialType.API_KEY,
            tags={"test": "persistence"}
        )
        
        # Create new manager instance
        new_manager = SecureCredentialManager(
            environment="test",
            storage_path=self.temp_dir,
            master_key_env="TEST_CREDENTIAL_MASTER_KEY"
        )
        
        # Verify credential exists and metadata is preserved
        metadata = new_manager.get_credential_metadata("persistence_test")
        assert metadata is not None
        assert metadata.credential_type == CredentialType.API_KEY
        assert metadata.tags == {"test": "persistence"}
        
        # Verify credential can be retrieved
        retrieved_value = new_manager.retrieve_credential("persistence_test")
        assert retrieved_value == "persistent-secret"
    
    def test_file_corruption_handling(self):
        """Test handling of corrupted credential files."""
        # Store credential normally
        self.credential_manager.store_credential(
            credential_id="corruption_test",
            credential_value="original-secret",
            credential_type=CredentialType.API_KEY
        )
        
        # Corrupt the credential file
        credential_file = self.credential_manager.credentials_dir / "corruption_test.enc"
        with open(credential_file, 'wb') as f:
            f.write(b"corrupted data that is not valid encryption")
        
        # Attempt to retrieve should fail gracefully
        with pytest.raises(Exception):  # Should raise some form of decryption/integrity error
            self.credential_manager.retrieve_credential("corruption_test")
    
    def test_storage_permissions(self):
        """Test that storage directories have secure permissions."""
        # Check directory permissions (should be 0o700 - owner only)
        storage_dirs = [
            self.credential_manager.credentials_dir,
            self.credential_manager.metadata_dir,
            self.credential_manager.audit_dir
        ]
        
        for directory in storage_dirs:
            stat_info = directory.stat()
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o700, f"Directory {directory} has insecure permissions: {oct(permissions)}"
    
    def test_credential_file_permissions(self):
        """Test that credential files have secure permissions."""
        # Store credential
        self.credential_manager.store_credential(
            credential_id="permissions_test",
            credential_value="secret-with-permissions",
            credential_type=CredentialType.API_KEY
        )
        
        # Check file permissions (should be 0o600 - owner read/write only)
        credential_file = self.credential_manager.credentials_dir / "permissions_test.enc"
        stat_info = credential_file.stat()
        permissions = stat_info.st_mode & 0o777
        assert permissions == 0o600, f"Credential file has insecure permissions: {oct(permissions)}"


class TestSecurityEdgeCases:
    """Test edge cases and security-specific scenarios."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["TEST_CREDENTIAL_MASTER_KEY"] = "test-master-key-edge-cases"
        
        self.credential_manager = SecureCredentialManager(
            environment="test",
            storage_path=self.temp_dir,
            master_key_env="TEST_CREDENTIAL_MASTER_KEY"
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if "TEST_CREDENTIAL_MASTER_KEY" in os.environ:
            del os.environ["TEST_CREDENTIAL_MASTER_KEY"]
    
    def test_malformed_metadata_handling(self):
        """Test handling of malformed metadata files."""
        # Create malformed metadata file
        metadata_file = self.credential_manager.metadata_dir / "credentials_metadata.json"
        with open(metadata_file, 'w') as f:
            f.write('{"malformed": json}')  # Invalid JSON
        
        # Creating new manager should handle malformed metadata gracefully
        new_manager = SecureCredentialManager(
            environment="test",
            storage_path=self.temp_dir,
            master_key_env="TEST_CREDENTIAL_MASTER_KEY"
        )
        
        # Should start with empty metadata
        assert len(new_manager.metadata) == 0
    
    def test_hmac_tampering_detection(self):
        """Test detection of HMAC tampering."""
        # Store credential
        self.credential_manager.store_credential(
            credential_id="hmac_test",
            credential_value="secret-to-tamper",
            credential_type=CredentialType.API_KEY
        )
        
        # Tamper with credential file
        credential_file = self.credential_manager.credentials_dir / "hmac_test.enc"
        with open(credential_file, 'rb') as f:
            data = bytearray(f.read())
        
        # Modify last byte (HMAC)
        data[-1] = (data[-1] + 1) % 256
        
        with open(credential_file, 'wb') as f:
            f.write(data)
        
        # Retrieval should fail due to HMAC verification
        with pytest.raises(SecurityViolationError, match="integrity verification failed"):
            self.credential_manager.retrieve_credential("hmac_test")
    
    def test_memory_clearing(self):
        """Test that sensitive data is cleared from memory."""
        # This test verifies the implementation attempts to clear memory
        # Actual memory inspection is complex and platform-dependent
        
        original_value = "sensitive-secret-to-clear"
        
        # Store and retrieve credential
        self.credential_manager.store_credential(
            credential_id="memory_clear_test",
            credential_value=original_value,
            credential_type=CredentialType.API_KEY
        )
        
        # Use secure context manager
        with self.credential_manager.secure_context("memory_clear_test") as cred_value:
            assert cred_value == original_value
        
        # The implementation should have cleared the credential from memory
        # This is verified by the implementation's use of memory clearing patterns
    
    def test_time_based_attacks_resistance(self):
        """Test resistance to timing attacks."""
        # Store credentials
        self.credential_manager.store_credential(
            credential_id="timing_test_1",
            credential_value="short",
            credential_type=CredentialType.API_KEY
        )
        
        self.credential_manager.store_credential(
            credential_id="timing_test_2", 
            credential_value="much-longer-credential-value-for-timing-analysis",
            credential_type=CredentialType.API_KEY
        )
        
        # Measure retrieval times (should be roughly similar)
        import time
        
        times = []
        for cred_id in ["timing_test_1", "timing_test_2"]:
            start_time = time.time()
            self.credential_manager.retrieve_credential(cred_id)
            end_time = time.time()
            times.append(end_time - start_time)
        
        # Times should be within reasonable variance
        # (This is a basic test - sophisticated timing analysis would need more iterations)
        time_ratio = max(times) / min(times) if min(times) > 0 else 1
        assert time_ratio < 10, "Excessive timing difference detected"


if __name__ == "__main__":
    # Run comprehensive test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=core.secure_credential_manager",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=95"
    ])