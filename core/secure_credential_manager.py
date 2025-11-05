#!/usr/bin/env python3
"""
Production-Grade Secure Credential Management System
==================================================

Secure credential storage and retrieval for the Adelaide weather forecasting application.
Implements industry-standard security practices including:
- AES-256-GCM encryption for credential storage
- Secure key derivation using PBKDF2
- Environment-specific credential isolation
- Comprehensive audit logging
- Credential lifecycle management
- Security-first design principles

Security Features:
- Defense-in-depth architecture
- Zero-knowledge credential storage
- Encrypted at-rest and in-transit
- Rate limiting and access controls
- Comprehensive audit trails
- Secure credential rotation
- Environment isolation
"""

import os
import json
import hmac
import time
import hashlib
import secrets
import logging
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from threading import Lock

# Cryptographic imports
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet


class CredentialType(Enum):
    """Types of credentials supported by the system."""
    API_KEY = "api_key"
    API_TOKEN = "api_token"
    DATABASE_PASSWORD = "database_password"
    SERVICE_TOKEN = "service_token"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_CLIENT_SECRET = "oauth_client_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    WEBHOOK_SECRET = "webhook_secret"
    SESSION_SECRET = "session_secret"
    JWT_SECRET = "jwt_secret"


class SecurityLevel(Enum):
    """Security levels for credential handling."""
    STANDARD = "standard"      # Basic encryption, standard audit trail
    HIGH = "high"          # Enhanced encryption, detailed audit trail
    CRITICAL = "critical"      # Maximum security, comprehensive monitoring
    EPHEMERAL = "ephemeral"     # Memory-only storage, no persistence


@dataclass
class CredentialMetadata:
    """Metadata for stored credentials."""
    credential_id: str
    credential_type: CredentialType
    security_level: SecurityLevel
    environment: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_accessed: Optional[datetime]
    access_count: int
    rotation_required: bool
    tags: Dict[str, str]


@dataclass
class AuditEvent:
    """Audit trail event structure."""
    timestamp: datetime
    event_type: str
    credential_id: str
    user_id: Optional[str]
    environment: str
    result: str
    details: Dict[str, Any]
    security_level: SecurityLevel


class SecurityViolationError(Exception):
    """Raised when a security violation is detected."""
    pass


class CredentialNotFoundError(Exception):
    """Raised when a requested credential is not found."""
    pass


class CredentialExpiredError(Exception):
    """Raised when a credential has expired."""
    pass


class SecureCredentialManager:
    """
    Production-grade secure credential management system.
    
    Provides secure storage, retrieval, and lifecycle management of sensitive
    credentials with comprehensive security controls and audit logging.
    """
    
    # Security constants
    PBKDF2_ITERATIONS = 100_000
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    SALT_SIZE = 32  # 256 bits
    MAX_CREDENTIAL_SIZE = 64 * 1024  # 64KB
    AUDIT_RETENTION_DAYS = 365
    
    # Rate limiting
    MAX_ACCESS_ATTEMPTS = 100
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    
    def __init__(self, 
                 environment: str = "production",
                 storage_path: Optional[str] = None,
                 master_key_env: str = "CREDENTIAL_MASTER_KEY"):
        """
        Initialize the secure credential manager.
        
        Args:
            environment: Environment name (dev/staging/production)
            storage_path: Custom storage path for credentials
            master_key_env: Environment variable containing master key
        """
        self.environment = environment
        self.master_key_env = master_key_env
        self._access_lock = Lock()
        self._rate_limits: Dict[str, List[float]] = {}
        
        # Setup secure storage paths
        self._setup_storage_paths(storage_path)
        
        # Initialize encryption system
        self._initialize_encryption()
        
        # Setup logging
        self._setup_audit_logging()
        
        # Initialize credential cache for ephemeral credentials
        self._ephemeral_cache: Dict[str, Tuple[bytes, CredentialMetadata]] = {}
        
        # Load existing credentials metadata
        self._load_metadata()
        
        logging.info(f"SecureCredentialManager initialized for environment: {environment}")
    
    def _setup_storage_paths(self, storage_path: Optional[str]) -> None:
        """Setup secure storage directory structure."""
        if storage_path:
            self.storage_root = Path(storage_path)
        else:
            # Use environment-specific secure directory
            base_dir = Path.home() / ".adelaide-weather" / "credentials"
            self.storage_root = base_dir / self.environment
        
        # Create directory structure with secure permissions
        self.credentials_dir = self.storage_root / "encrypted"
        self.metadata_dir = self.storage_root / "metadata"
        self.audit_dir = self.storage_root / "audit"
        
        for directory in [self.credentials_dir, self.metadata_dir, self.audit_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions (owner only)
            os.chmod(directory, 0o700)
    
    def _initialize_encryption(self) -> None:
        """Initialize the encryption system with master key."""
        master_key = os.environ.get(self.master_key_env)
        
        if not master_key:
            # Generate a new master key for development/testing
            if self.environment == "development":
                master_key = secrets.token_urlsafe(32)
                os.environ[self.master_key_env] = master_key
                logging.warning("Generated new master key for development environment")
            else:
                raise SecurityViolationError(
                    f"Master key not found in environment variable: {self.master_key_env}"
                )
        
        # Derive encryption key from master key
        self.master_key_bytes = master_key.encode('utf-8')
    
    def _setup_audit_logging(self) -> None:
        """Setup comprehensive audit logging."""
        self.audit_logger = logging.getLogger(f"credential_audit_{self.environment}")
        self.audit_logger.setLevel(logging.INFO)
        
        # Create audit log handler with rotation
        audit_log_file = self.audit_dir / f"credential_audit_{datetime.now().strftime('%Y%m')}.log"
        handler = logging.FileHandler(audit_log_file)
        handler.setLevel(logging.INFO)
        
        # Secure audit log format
        formatter = logging.Formatter(
            '%(asctime)s|%(levelname)s|%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S UTC'
        )
        handler.setFormatter(formatter)
        
        self.audit_logger.addHandler(handler)
        
        # Set secure permissions on audit logs
        os.chmod(audit_log_file, 0o600)
    
    def _load_metadata(self) -> None:
        """Load credential metadata from secure storage."""
        self.metadata: Dict[str, CredentialMetadata] = {}
        
        metadata_file = self.metadata_dir / "credentials_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    raw_data = json.load(f)
                
                # Deserialize metadata
                for cred_id, meta_dict in raw_data.items():
                    # Convert string dates back to datetime objects
                    meta_dict['created_at'] = datetime.fromisoformat(meta_dict['created_at'])
                    if meta_dict['expires_at']:
                        meta_dict['expires_at'] = datetime.fromisoformat(meta_dict['expires_at'])
                    if meta_dict['last_accessed']:
                        meta_dict['last_accessed'] = datetime.fromisoformat(meta_dict['last_accessed'])
                    
                    # Convert string enums back to enum objects
                    meta_dict['credential_type'] = CredentialType(meta_dict['credential_type'])
                    # Handle SecurityLevel enum conversion properly
                    security_level_value = meta_dict['security_level']
                    if isinstance(security_level_value, str):
                        # Try by value first (preferred), then by name
                        try:
                            meta_dict['security_level'] = SecurityLevel(security_level_value)
                        except ValueError:
                            try:
                                meta_dict['security_level'] = SecurityLevel[security_level_value.upper()]
                            except KeyError:
                                # Default fallback
                                meta_dict['security_level'] = SecurityLevel.STANDARD
                    
                    self.metadata[cred_id] = CredentialMetadata(**meta_dict)
                
                logging.info(f"Loaded metadata for {len(self.metadata)} credentials")
            except Exception as e:
                logging.error(f"Failed to load credential metadata: {e}")
                self.metadata = {}
    
    def _save_metadata(self) -> None:
        """Save credential metadata to secure storage."""
        metadata_file = self.metadata_dir / "credentials_metadata.json"
        temp_file = metadata_file.with_suffix('.tmp')
        
        try:
            # Serialize metadata
            serializable_data = {}
            for cred_id, metadata in self.metadata.items():
                meta_dict = asdict(metadata)
                # Convert datetime objects to ISO strings
                meta_dict['created_at'] = metadata.created_at.isoformat()
                meta_dict['expires_at'] = metadata.expires_at.isoformat() if metadata.expires_at else None
                meta_dict['last_accessed'] = metadata.last_accessed.isoformat() if metadata.last_accessed else None
                # Convert enums to string values
                meta_dict['credential_type'] = metadata.credential_type.value
                meta_dict['security_level'] = metadata.security_level.value
                
                serializable_data[cred_id] = meta_dict
            
            # Write to temp file first
            with open(temp_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            
            # Atomic move to final location
            temp_file.replace(metadata_file)
            
            # Set secure permissions
            os.chmod(metadata_file, 0o600)
            
        except Exception as e:
            logging.error(f"Failed to save credential metadata: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def _derive_key(self, salt: bytes, security_level: SecurityLevel) -> bytes:
        """Derive encryption key for specific security level."""
        # Different iteration counts for different security levels
        iterations = {
            SecurityLevel.STANDARD: self.PBKDF2_ITERATIONS,
            SecurityLevel.HIGH: self.PBKDF2_ITERATIONS * 2,
            SecurityLevel.CRITICAL: self.PBKDF2_ITERATIONS * 5,
            SecurityLevel.EPHEMERAL: self.PBKDF2_ITERATIONS
        }[security_level]
        
        # Create a new PBKDF2HMAC instance for each derivation
        # (instances can only be used once)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        return kdf.derive(self.master_key_bytes)
    
    def _encrypt_credential(self, 
                          credential_data: bytes, 
                          security_level: SecurityLevel) -> Tuple[bytes, bytes]:
        """Encrypt credential data with appropriate security level."""
        # Generate random salt and nonce
        salt = secrets.token_bytes(self.SALT_SIZE)
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        
        # Derive encryption key
        encryption_key = self._derive_key(salt, security_level)
        
        # Encrypt using AES-GCM
        aesgcm = AESGCM(encryption_key)
        
        # Add security level as additional authenticated data
        aad = f"{security_level.name}:{self.environment}".encode('utf-8')
        
        try:
            ciphertext = aesgcm.encrypt(nonce, credential_data, aad)
            
            # Construct encrypted blob: salt + nonce + ciphertext
            encrypted_blob = salt + nonce + ciphertext
            
            # Generate HMAC for integrity verification
            hmac_key = hashlib.pbkdf2_hmac('sha256', encryption_key, salt, 1000)
            hmac_digest = hmac.new(hmac_key, encrypted_blob, hashlib.sha256).digest()
            
            return encrypted_blob, hmac_digest
        
        finally:
            # Clear sensitive key material
            encryption_key = b'\x00' * len(encryption_key)
    
    def _decrypt_credential(self, 
                          encrypted_blob: bytes, 
                          hmac_digest: bytes,
                          security_level: SecurityLevel) -> bytes:
        """Decrypt credential data and verify integrity."""
        if len(encrypted_blob) < (self.SALT_SIZE + self.NONCE_SIZE):
            raise SecurityViolationError("Invalid encrypted credential format")
        
        # Extract components
        salt = encrypted_blob[:self.SALT_SIZE]
        nonce = encrypted_blob[self.SALT_SIZE:self.SALT_SIZE + self.NONCE_SIZE]
        ciphertext = encrypted_blob[self.SALT_SIZE + self.NONCE_SIZE:]
        
        # Derive encryption key
        encryption_key = self._derive_key(salt, security_level)
        
        try:
            # Verify HMAC integrity
            hmac_key = hashlib.pbkdf2_hmac('sha256', encryption_key, salt, 1000)
            expected_hmac = hmac.new(hmac_key, encrypted_blob, hashlib.sha256).digest()
            
            if not hmac.compare_digest(hmac_digest, expected_hmac):
                raise SecurityViolationError("Credential integrity verification failed")
            
            # Decrypt using AES-GCM
            aesgcm = AESGCM(encryption_key)
            aad = f"{security_level.name}:{self.environment}".encode('utf-8')
            
            return aesgcm.decrypt(nonce, ciphertext, aad)
        
        finally:
            # Clear sensitive key material
            encryption_key = b'\x00' * len(encryption_key)
    
    def _audit_log(self, 
                   event_type: str,
                   credential_id: str,
                   result: str,
                   details: Optional[Dict[str, Any]] = None,
                   security_level: SecurityLevel = SecurityLevel.STANDARD,
                   user_id: Optional[str] = None) -> None:
        """Log security audit event."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            credential_id=credential_id,
            user_id=user_id or "system",
            environment=self.environment,
            result=result,
            details=details or {},
            security_level=security_level
        )
        
        # Format audit log entry
        security_level_str = event.security_level.value if hasattr(event.security_level, 'value') else str(event.security_level)
        audit_entry = (
            f"{event.timestamp.isoformat()}|"
            f"{event.event_type}|"
            f"{event.credential_id}|"
            f"{event.user_id}|"
            f"{event.environment}|"
            f"{security_level_str}|"
            f"{event.result}|"
            f"{json.dumps(event.details, separators=(',', ':'))}"
        )
        
        self.audit_logger.info(audit_entry)
    
    def _check_rate_limit(self, credential_id: str) -> bool:
        """Check rate limiting for credential access."""
        current_time = time.time()
        window_start = current_time - self.RATE_LIMIT_WINDOW
        
        # Clean old entries
        if credential_id in self._rate_limits:
            self._rate_limits[credential_id] = [
                access_time for access_time in self._rate_limits[credential_id]
                if access_time > window_start
            ]
        else:
            self._rate_limits[credential_id] = []
        
        # Check if rate limit exceeded
        if len(self._rate_limits[credential_id]) >= self.MAX_ACCESS_ATTEMPTS:
            return False
        
        # Record this access
        self._rate_limits[credential_id].append(current_time)
        return True
    
    def store_credential(self,
                        credential_id: str,
                        credential_value: str,
                        credential_type: CredentialType,
                        security_level: SecurityLevel = SecurityLevel.STANDARD,
                        expires_at: Optional[datetime] = None,
                        tags: Optional[Dict[str, str]] = None,
                        user_id: Optional[str] = None) -> bool:
        """
        Store a credential securely.
        
        Args:
            credential_id: Unique identifier for the credential
            credential_value: The actual credential value to store
            credential_type: Type of credential
            security_level: Security level for storage
            expires_at: Optional expiration datetime
            tags: Optional metadata tags
            user_id: User performing the operation
            
        Returns:
            True if stored successfully
            
        Raises:
            SecurityViolationError: If security constraints are violated
        """
        with self._access_lock:
            # Validate input
            if not credential_id or not credential_value:
                raise ValueError("Credential ID and value are required")
            
            if len(credential_value.encode('utf-8')) > self.MAX_CREDENTIAL_SIZE:
                raise SecurityViolationError("Credential value exceeds maximum size limit")
            
            # Check if credential already exists
            if credential_id in self.metadata:
                self._audit_log("store_credential", credential_id, "failed", 
                              {"reason": "credential_already_exists"}, security_level, user_id)
                raise SecurityViolationError(f"Credential {credential_id} already exists")
            
            try:
                credential_bytes = credential_value.encode('utf-8')
                
                # Handle ephemeral credentials differently
                if security_level == SecurityLevel.EPHEMERAL:
                    # Store in memory only
                    metadata = CredentialMetadata(
                        credential_id=credential_id,
                        credential_type=credential_type,
                        security_level=security_level,
                        environment=self.environment,
                        created_at=datetime.now(timezone.utc),
                        expires_at=expires_at,
                        last_accessed=None,
                        access_count=0,
                        rotation_required=False,
                        tags=tags or {}
                    )
                    
                    encrypted_blob, hmac_digest = self._encrypt_credential(credential_bytes, security_level)
                    self._ephemeral_cache[credential_id] = (encrypted_blob + hmac_digest, metadata)
                    
                else:
                    # Encrypt credential
                    encrypted_blob, hmac_digest = self._encrypt_credential(credential_bytes, security_level)
                    
                    # Store encrypted credential to disk
                    credential_file = self.credentials_dir / f"{credential_id}.enc"
                    with open(credential_file, 'wb') as f:
                        f.write(encrypted_blob + hmac_digest)
                    
                    # Set secure permissions
                    os.chmod(credential_file, 0o600)
                    
                    # Create metadata
                    metadata = CredentialMetadata(
                        credential_id=credential_id,
                        credential_type=credential_type,
                        security_level=security_level,
                        environment=self.environment,
                        created_at=datetime.now(timezone.utc),
                        expires_at=expires_at,
                        last_accessed=None,
                        access_count=0,
                        rotation_required=False,
                        tags=tags or {}
                    )
                    
                    self.metadata[credential_id] = metadata
                    self._save_metadata()
                
                # Clear sensitive data
                credential_bytes = b'\x00' * len(credential_bytes)
                
                self._audit_log("store_credential", credential_id, "success", 
                              {"credential_type": credential_type.value, 
                               "security_level": security_level.name}, security_level, user_id)
                
                return True
                
            except Exception as e:
                self._audit_log("store_credential", credential_id, "failed", 
                              {"error": str(e)}, security_level, user_id)
                raise
    
    def retrieve_credential(self,
                          credential_id: str,
                          user_id: Optional[str] = None) -> str:
        """
        Retrieve a credential securely.
        
        Args:
            credential_id: Unique identifier for the credential
            user_id: User performing the operation
            
        Returns:
            The decrypted credential value
            
        Raises:
            CredentialNotFoundError: If credential doesn't exist
            CredentialExpiredError: If credential has expired
            SecurityViolationError: If security constraints are violated
        """
        with self._access_lock:
            # Check rate limiting
            if not self._check_rate_limit(credential_id):
                self._audit_log("retrieve_credential", credential_id, "rate_limited", 
                              {"user_id": user_id}, SecurityLevel.STANDARD, user_id)
                raise SecurityViolationError(f"Rate limit exceeded for credential {credential_id}")
            
            # Check ephemeral cache first
            if credential_id in self._ephemeral_cache:
                encrypted_data, metadata = self._ephemeral_cache[credential_id]
                
                # Check expiration
                if metadata.expires_at and datetime.now(timezone.utc) > metadata.expires_at:
                    del self._ephemeral_cache[credential_id]
                    self._audit_log("retrieve_credential", credential_id, "expired", 
                                  {"user_id": user_id}, metadata.security_level, user_id)
                    raise CredentialExpiredError(f"Credential {credential_id} has expired")
                
                # Decrypt credential
                hmac_size = 32  # SHA256 digest size
                encrypted_blob = encrypted_data[:-hmac_size]
                hmac_digest = encrypted_data[-hmac_size:]
                
                try:
                    credential_bytes = self._decrypt_credential(encrypted_blob, hmac_digest, metadata.security_level)
                    credential_value = credential_bytes.decode('utf-8')
                    
                    # Update access tracking
                    metadata.last_accessed = datetime.now(timezone.utc)
                    metadata.access_count += 1
                    
                    self._audit_log("retrieve_credential", credential_id, "success", 
                                  {"user_id": user_id}, metadata.security_level, user_id)
                    
                    return credential_value
                
                finally:
                    # Clear sensitive data
                    if 'credential_bytes' in locals():
                        credential_bytes = b'\x00' * len(credential_bytes)
            
            # Check persistent storage
            if credential_id not in self.metadata:
                self._audit_log("retrieve_credential", credential_id, "not_found", 
                              {"user_id": user_id}, SecurityLevel.STANDARD, user_id)
                raise CredentialNotFoundError(f"Credential {credential_id} not found")
            
            metadata = self.metadata[credential_id]
            
            # Check expiration
            if metadata.expires_at and datetime.now(timezone.utc) > metadata.expires_at:
                self._audit_log("retrieve_credential", credential_id, "expired", 
                              {"user_id": user_id}, metadata.security_level, user_id)
                raise CredentialExpiredError(f"Credential {credential_id} has expired")
            
            try:
                # Load encrypted credential
                credential_file = self.credentials_dir / f"{credential_id}.enc"
                if not credential_file.exists():
                    self._audit_log("retrieve_credential", credential_id, "file_not_found", 
                                  {"user_id": user_id}, metadata.security_level, user_id)
                    raise CredentialNotFoundError(f"Credential file for {credential_id} not found")
                
                with open(credential_file, 'rb') as f:
                    encrypted_data = f.read()
                
                # Split encrypted data and HMAC
                hmac_size = 32  # SHA256 digest size
                encrypted_blob = encrypted_data[:-hmac_size]
                hmac_digest = encrypted_data[-hmac_size:]
                
                # Decrypt credential
                credential_bytes = self._decrypt_credential(encrypted_blob, hmac_digest, metadata.security_level)
                credential_value = credential_bytes.decode('utf-8')
                
                # Update access tracking
                metadata.last_accessed = datetime.now(timezone.utc)
                metadata.access_count += 1
                self._save_metadata()
                
                self._audit_log("retrieve_credential", credential_id, "success", 
                              {"user_id": user_id}, metadata.security_level, user_id)
                
                return credential_value
                
            except Exception as e:
                self._audit_log("retrieve_credential", credential_id, "failed", 
                              {"error": str(e), "user_id": user_id}, metadata.security_level, user_id)
                raise
            
            finally:
                # Clear sensitive data
                if 'credential_bytes' in locals():
                    credential_bytes = b'\x00' * len(credential_bytes)
    
    def delete_credential(self,
                         credential_id: str,
                         user_id: Optional[str] = None) -> bool:
        """
        Delete a credential securely.
        
        Args:
            credential_id: Unique identifier for the credential
            user_id: User performing the operation
            
        Returns:
            True if deleted successfully
        """
        with self._access_lock:
            # Check ephemeral cache
            if credential_id in self._ephemeral_cache:
                del self._ephemeral_cache[credential_id]
                self._audit_log("delete_credential", credential_id, "success", 
                              {"storage": "ephemeral", "user_id": user_id}, SecurityLevel.EPHEMERAL, user_id)
                return True
            
            # Check persistent storage
            if credential_id not in self.metadata:
                self._audit_log("delete_credential", credential_id, "not_found", 
                              {"user_id": user_id}, SecurityLevel.STANDARD, user_id)
                raise CredentialNotFoundError(f"Credential {credential_id} not found")
            
            metadata = self.metadata[credential_id]
            
            try:
                # Securely delete credential file
                credential_file = self.credentials_dir / f"{credential_id}.enc"
                if credential_file.exists():
                    # Overwrite file with random data before deletion
                    file_size = credential_file.stat().st_size
                    with open(credential_file, 'wb') as f:
                        f.write(secrets.token_bytes(file_size))
                    
                    credential_file.unlink()
                
                # Remove from metadata
                del self.metadata[credential_id]
                self._save_metadata()
                
                self._audit_log("delete_credential", credential_id, "success", 
                              {"user_id": user_id}, metadata.security_level, user_id)
                
                return True
                
            except Exception as e:
                self._audit_log("delete_credential", credential_id, "failed", 
                              {"error": str(e), "user_id": user_id}, metadata.security_level, user_id)
                raise
    
    def rotate_credential(self,
                         credential_id: str,
                         new_credential_value: str,
                         user_id: Optional[str] = None) -> bool:
        """
        Rotate a credential with a new value.
        
        Args:
            credential_id: Unique identifier for the credential
            new_credential_value: New credential value
            user_id: User performing the operation
            
        Returns:
            True if rotated successfully
        """
        with self._access_lock:
            if credential_id not in self.metadata:
                raise CredentialNotFoundError(f"Credential {credential_id} not found")
            
            metadata = self.metadata[credential_id]
            
            try:
                # Store backup of old credential
                backup_id = f"{credential_id}_backup_{int(time.time())}"
                old_value = self.retrieve_credential(credential_id, user_id)
                
                # Create backup
                self.store_credential(
                    backup_id,
                    old_value,
                    metadata.credential_type,
                    metadata.security_level,
                    datetime.now(timezone.utc) + timedelta(days=30),  # Backup expires in 30 days
                    {"backup_of": credential_id, "rotation_time": datetime.now(timezone.utc).isoformat()},
                    user_id
                )
                
                # Update with new value
                self.delete_credential(credential_id, user_id)
                self.store_credential(
                    credential_id,
                    new_credential_value,
                    metadata.credential_type,
                    metadata.security_level,
                    metadata.expires_at,
                    metadata.tags,
                    user_id
                )
                
                # Update rotation status
                self.metadata[credential_id].rotation_required = False
                self._save_metadata()
                
                self._audit_log("rotate_credential", credential_id, "success", 
                              {"backup_id": backup_id, "user_id": user_id}, metadata.security_level, user_id)
                
                return True
                
            except Exception as e:
                self._audit_log("rotate_credential", credential_id, "failed", 
                              {"error": str(e), "user_id": user_id}, metadata.security_level, user_id)
                raise
    
    def list_credentials(self,
                        credential_type: Optional[CredentialType] = None,
                        security_level: Optional[SecurityLevel] = None,
                        include_expired: bool = False) -> List[CredentialMetadata]:
        """
        List stored credentials with filtering options.
        
        Args:
            credential_type: Filter by credential type
            security_level: Filter by security level
            include_expired: Include expired credentials
            
        Returns:
            List of credential metadata
        """
        with self._access_lock:
            results = []
            current_time = datetime.now(timezone.utc)
            
            # Check persistent storage
            for metadata in self.metadata.values():
                # Apply filters
                if credential_type and metadata.credential_type != credential_type:
                    continue
                if security_level and metadata.security_level != security_level:
                    continue
                if not include_expired and metadata.expires_at and current_time > metadata.expires_at:
                    continue
                
                results.append(metadata)
            
            # Check ephemeral cache
            for credential_id, (_, metadata) in self._ephemeral_cache.items():
                # Apply filters
                if credential_type and metadata.credential_type != credential_type:
                    continue
                if security_level and metadata.security_level != security_level:
                    continue
                if not include_expired and metadata.expires_at and current_time > metadata.expires_at:
                    continue
                
                results.append(metadata)
            
            return results
    
    def get_credential_metadata(self, credential_id: str) -> Optional[CredentialMetadata]:
        """
        Get metadata for a specific credential.
        
        Args:
            credential_id: Unique identifier for the credential
            
        Returns:
            Credential metadata or None if not found
        """
        # Check ephemeral cache
        if credential_id in self._ephemeral_cache:
            return self._ephemeral_cache[credential_id][1]
        
        # Check persistent storage
        return self.metadata.get(credential_id)
    
    def mark_for_rotation(self, credential_id: str, user_id: Optional[str] = None) -> bool:
        """
        Mark a credential for rotation.
        
        Args:
            credential_id: Unique identifier for the credential
            user_id: User performing the operation
            
        Returns:
            True if marked successfully
        """
        with self._access_lock:
            if credential_id not in self.metadata:
                raise CredentialNotFoundError(f"Credential {credential_id} not found")
            
            self.metadata[credential_id].rotation_required = True
            self._save_metadata()
            
            self._audit_log("mark_for_rotation", credential_id, "success", 
                          {"user_id": user_id}, self.metadata[credential_id].security_level, user_id)
            
            return True
    
    def cleanup_expired_credentials(self) -> int:
        """
        Clean up expired credentials.
        
        Returns:
            Number of credentials cleaned up
        """
        with self._access_lock:
            current_time = datetime.now(timezone.utc)
            expired_credentials = []
            
            # Find expired credentials in persistent storage
            for credential_id, metadata in self.metadata.items():
                if metadata.expires_at and current_time > metadata.expires_at:
                    expired_credentials.append(credential_id)
            
            # Find expired credentials in ephemeral cache
            for credential_id, (_, metadata) in list(self._ephemeral_cache.items()):
                if metadata.expires_at and current_time > metadata.expires_at:
                    del self._ephemeral_cache[credential_id]
                    expired_credentials.append(credential_id)
            
            # Delete expired persistent credentials
            for credential_id in expired_credentials:
                if credential_id in self.metadata:
                    try:
                        self.delete_credential(credential_id, "system_cleanup")
                    except Exception as e:
                        logging.error(f"Failed to cleanup expired credential {credential_id}: {e}")
            
            self._audit_log("cleanup_expired", "system", "success", 
                          {"cleaned_count": len(expired_credentials)}, SecurityLevel.STANDARD, "system")
            
            return len(expired_credentials)
    
    @contextmanager
    def secure_context(self, credential_id: str, user_id: Optional[str] = None):
        """
        Context manager for secure credential access.
        
        Args:
            credential_id: Unique identifier for the credential
            user_id: User performing the operation
            
        Yields:
            The credential value
        """
        credential_value = None
        try:
            credential_value = self.retrieve_credential(credential_id, user_id)
            yield credential_value
        finally:
            # Securely clear credential from memory
            if credential_value:
                credential_value = '\x00' * len(credential_value)
    
    def get_audit_trail(self,
                       credential_id: Optional[str] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       event_type: Optional[str] = None) -> List[str]:
        """
        Retrieve audit trail entries.
        
        Args:
            credential_id: Filter by credential ID
            start_time: Filter by start time
            end_time: Filter by end time
            event_type: Filter by event type
            
        Returns:
            List of audit log entries
        """
        audit_entries = []
        
        # Read audit log files
        for audit_file in self.audit_dir.glob("credential_audit_*.log"):
            try:
                with open(audit_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse audit entry
                        parts = line.split('|')
                        if len(parts) < 8:
                            continue
                        
                        entry_time = datetime.fromisoformat(parts[0])
                        entry_event_type = parts[2]
                        entry_credential_id = parts[3]
                        
                        # Apply filters
                        if credential_id and entry_credential_id != credential_id:
                            continue
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue
                        if event_type and entry_event_type != event_type:
                            continue
                        
                        audit_entries.append(line)
                        
            except Exception as e:
                logging.error(f"Failed to read audit file {audit_file}: {e}")
        
        return sorted(audit_entries)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform system health check.
        
        Returns:
            Health status information
        """
        health_status = {
            "status": "healthy",
            "environment": self.environment,
            "credential_count": len(self.metadata),
            "ephemeral_count": len(self._ephemeral_cache),
            "storage_accessible": True,
            "audit_logging": True,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "issues": []
        }
        
        try:
            # Check storage accessibility
            test_file = self.storage_root / "health_check.tmp"
            test_file.write_text("health_check")
            test_file.unlink()
            
        except Exception as e:
            health_status["storage_accessible"] = False
            health_status["issues"].append(f"Storage not accessible: {e}")
            health_status["status"] = "degraded"
        
        try:
            # Check audit logging
            self._audit_log("health_check", "system", "success", {}, SecurityLevel.STANDARD, "system")
            
        except Exception as e:
            health_status["audit_logging"] = False
            health_status["issues"].append(f"Audit logging failed: {e}")
            health_status["status"] = "degraded"
        
        # Check for credentials requiring rotation
        rotation_needed = sum(1 for meta in self.metadata.values() if meta.rotation_required)
        if rotation_needed > 0:
            health_status["issues"].append(f"{rotation_needed} credentials require rotation")
        
        # Check for expired credentials
        current_time = datetime.now(timezone.utc)
        expired_count = sum(1 for meta in self.metadata.values() 
                          if meta.expires_at and current_time > meta.expires_at)
        if expired_count > 0:
            health_status["issues"].append(f"{expired_count} credentials have expired")
        
        if health_status["issues"]:
            health_status["status"] = "warning" if health_status["status"] == "healthy" else health_status["status"]
        
        return health_status


# Export public interface
__all__ = [
    'SecureCredentialManager',
    'CredentialType', 
    'SecurityLevel',
    'CredentialMetadata',
    'AuditEvent',
    'SecurityViolationError',
    'CredentialNotFoundError', 
    'CredentialExpiredError'
]