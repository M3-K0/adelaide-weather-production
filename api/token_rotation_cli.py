#!/usr/bin/env python3
"""
Adelaide Weather API - Token Rotation CLI
==========================================

Secure command-line interface for API token lifecycle management.
Provides comprehensive token rotation, validation, and audit capabilities.

Features:
- Cryptographically secure token generation with configurable entropy
- Automated token rotation with backup and rollback capabilities
- Comprehensive audit logging with token redaction for security
- Integration with existing secure credential manager
- Entropy validation and minimum security requirements
- Backward compatibility with API_TOKEN environment variable
- Automated operational workflows for production use

Security Features:
- Tokens generated with 256-bit cryptographic randomness
- All token operations logged with redacted values
- PBKDF2-based key derivation for storage encryption
- Audit trails include user attribution and outcome tracking
- Rate limiting protection against brute force attacks
- Secure token validation with format and entropy checks

Author: Security Operations Team
Version: 1.0.0 - Production Token Management
"""

import os
import sys
import json
import time
import math
import secrets
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.secure_credential_manager import (
    SecureCredentialManager, CredentialType, SecurityLevel,
    CredentialMetadata, SecurityViolationError, CredentialNotFoundError
)


@dataclass
class TokenMetrics:
    """Token security metrics and entropy analysis."""
    length: int
    character_set_size: int
    entropy_bits: float
    charset_diversity: float
    pattern_score: float
    security_level: str


@dataclass
class AuditRecord:
    """Audit record for token operations with redaction."""
    timestamp: datetime
    operation: str
    token_id: str
    user_id: str
    environment: str
    success: bool
    token_hash: str  # SHA256 hash of token for correlation
    entropy_bits: Optional[float]
    security_level: str
    details: Dict[str, Any]


class TokenEntropyValidator:
    """Validates token entropy and security characteristics."""
    
    # Minimum security requirements
    MIN_TOKEN_LENGTH = 32
    MIN_ENTROPY_BITS = 128.0
    MIN_CHARSET_DIVERSITY = 0.75
    
    # Character sets for entropy calculation
    LOWERCASE = set('abcdefghijklmnopqrstuvwxyz')
    UPPERCASE = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    DIGITS = set('0123456789')
    SPECIAL = set('-_.')
    
    @classmethod
    def calculate_entropy(cls, token: str) -> TokenMetrics:
        """Calculate comprehensive entropy metrics for a token."""
        # Basic metrics
        length = len(token)
        token_set = set(token)
        
        # Character set analysis
        charset_count = 0
        if token_set & cls.LOWERCASE:
            charset_count += len(cls.LOWERCASE)
        if token_set & cls.UPPERCASE:
            charset_count += len(cls.UPPERCASE)
        if token_set & cls.DIGITS:
            charset_count += len(cls.DIGITS)
        if token_set & cls.SPECIAL:
            charset_count += len(cls.SPECIAL)
        
        # Shannon entropy calculation
        entropy_bits = length * math.log2(charset_count) if charset_count > 0 else 0.0
        
        # Character set diversity
        used_charsets = 0
        if token_set & cls.LOWERCASE:
            used_charsets += 1
        if token_set & cls.UPPERCASE:
            used_charsets += 1
        if token_set & cls.DIGITS:
            used_charsets += 1
        if token_set & cls.SPECIAL:
            used_charsets += 1
        
        charset_diversity = used_charsets / 4.0
        
        # Pattern analysis (detect simple patterns)
        pattern_score = cls._analyze_patterns(token)
        
        # Security level determination
        if entropy_bits >= 256 and charset_diversity >= 0.75 and pattern_score >= 0.8:
            security_level = "EXCELLENT"
        elif entropy_bits >= 192 and charset_diversity >= 0.5 and pattern_score >= 0.6:
            security_level = "GOOD"
        elif entropy_bits >= cls.MIN_ENTROPY_BITS and charset_diversity >= cls.MIN_CHARSET_DIVERSITY:
            security_level = "ACCEPTABLE"
        else:
            security_level = "WEAK"
        
        return TokenMetrics(
            length=length,
            character_set_size=charset_count,
            entropy_bits=entropy_bits,
            charset_diversity=charset_diversity,
            pattern_score=pattern_score,
            security_level=security_level
        )
    
    @classmethod
    def _analyze_patterns(cls, token: str) -> float:
        """Analyze token for common weak patterns."""
        if len(token) < 4:
            return 0.0
        
        # Check for repeated characters
        repeated_chars = sum(1 for i in range(1, len(token)) if token[i] == token[i-1])
        repeat_penalty = repeated_chars / len(token)
        
        # Check for sequential patterns
        sequential = 0
        for i in range(2, len(token)):
            if ord(token[i]) == ord(token[i-1]) + 1 == ord(token[i-2]) + 2:
                sequential += 1
        
        sequence_penalty = sequential / max(1, len(token) - 2)
        
        # Calculate pattern score (higher is better)
        pattern_score = 1.0 - min(1.0, repeat_penalty + sequence_penalty)
        
        return pattern_score
    
    @classmethod
    def validate_token(cls, token: str) -> Tuple[bool, List[str]]:
        """Validate token meets minimum security requirements."""
        issues = []
        
        if len(token) < cls.MIN_TOKEN_LENGTH:
            issues.append(f"Token too short (minimum {cls.MIN_TOKEN_LENGTH} characters)")
        
        metrics = cls.calculate_entropy(token)
        
        if metrics.entropy_bits < cls.MIN_ENTROPY_BITS:
            issues.append(f"Insufficient entropy ({metrics.entropy_bits:.1f} < {cls.MIN_ENTROPY_BITS} bits)")
        
        if metrics.charset_diversity < cls.MIN_CHARSET_DIVERSITY:
            issues.append(f"Low character set diversity ({metrics.charset_diversity:.2f} < {cls.MIN_CHARSET_DIVERSITY})")
        
        if metrics.pattern_score < 0.5:
            issues.append("Token contains weak patterns")
        
        # Check for common weak tokens
        weak_patterns = ['test', 'demo', 'example', 'password', 'secret', 'admin']
        if any(pattern in token.lower() for pattern in weak_patterns):
            issues.append("Token contains common weak patterns")
        
        return len(issues) == 0, issues


class SecureTokenGenerator:
    """Cryptographically secure token generator with configurable parameters."""
    
    # Character sets for token generation
    ALPHANUMERIC = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    EXTENDED = ALPHANUMERIC + '-_.'
    
    @classmethod
    def generate_api_token(cls, 
                          length: int = 64,
                          charset: str = None,
                          ensure_diversity: bool = True) -> str:
        """Generate a cryptographically secure API token."""
        if charset is None:
            charset = cls.EXTENDED
        
        if length < TokenEntropyValidator.MIN_TOKEN_LENGTH:
            raise ValueError(f"Token length must be at least {TokenEntropyValidator.MIN_TOKEN_LENGTH}")
        
        # Generate base token
        token = ''.join(secrets.choice(charset) for _ in range(length))
        
        # Ensure character set diversity if requested
        if ensure_diversity:
            token = cls._ensure_diversity(token, charset)
        
        # Validate the generated token
        is_valid, issues = TokenEntropyValidator.validate_token(token)
        if not is_valid:
            # Regenerate if validation fails (rare with proper entropy)
            return cls.generate_api_token(length, charset, ensure_diversity)
        
        return token
    
    @classmethod
    def _ensure_diversity(cls, token: str, charset: str) -> str:
        """Ensure the token uses diverse character sets."""
        token_list = list(token)
        
        # Character sets to ensure
        required_sets = [
            ('abcdefghijklmnopqrstuvwxyz', 'lowercase'),
            ('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'uppercase'),
            ('0123456789', 'digits'),
            ('-_.', 'special')
        ]
        
        # Check which sets are missing
        for char_set, name in required_sets:
            if any(c in charset for c in char_set):  # Only if charset supports it
                if not any(c in char_set for c in token):
                    # Replace a random character with one from missing set
                    available_chars = [c for c in char_set if c in charset]
                    if available_chars:
                        pos = secrets.randbelow(len(token_list))
                        token_list[pos] = secrets.choice(available_chars)
        
        return ''.join(token_list)


class TokenRotationAuditLogger:
    """Specialized audit logger for token operations with redaction."""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.audit_dir = Path.home() / ".adelaide-weather" / "token-audit" / environment
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions
        os.chmod(self.audit_dir, 0o700)
        
        # Setup logging
        self.logger = logging.getLogger(f"token_rotation_audit_{environment}")
        self.logger.setLevel(logging.INFO)
        
        # Create audit log handler
        log_file = self.audit_dir / f"token_rotation_{datetime.now().strftime('%Y%m')}.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Secure audit format with ISO format
        formatter = logging.Formatter(
            '%(asctime)s|%(levelname)s|%(message)s'
        )
        formatter.datefmt = None  # Use default ISO format
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        
        # Set secure permissions on log file
        if log_file.exists():
            os.chmod(log_file, 0o600)
    
    def log_token_operation(self, 
                           operation: str,
                           token_id: str,
                           token_value: str,
                           user_id: str,
                           success: bool,
                           details: Dict[str, Any] = None) -> None:
        """Log token operation with proper redaction."""
        # Create redacted token hash for correlation
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()[:16]
        
        # Calculate entropy for audit
        metrics = TokenEntropyValidator.calculate_entropy(token_value)
        
        # Create audit record
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc),
            operation=operation,
            token_id=token_id,
            user_id=user_id,
            environment=self.environment,
            success=success,
            token_hash=token_hash,
            entropy_bits=metrics.entropy_bits,
            security_level=metrics.security_level,
            details=details or {}
        )
        
        # Format audit entry (token value never logged)
        audit_entry = (
            f"{record.timestamp.isoformat()}|"
            f"{record.operation}|"
            f"{record.token_id}|"
            f"{record.user_id}|"
            f"{record.environment}|"
            f"{'SUCCESS' if record.success else 'FAILED'}|"
            f"hash:{record.token_hash}|"
            f"entropy:{record.entropy_bits:.1f}|"
            f"security:{record.security_level}|"
            f"{json.dumps(record.details, separators=(',', ':'))}"
        )
        
        self.logger.info(audit_entry)
    
    def get_audit_records(self, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         operation: Optional[str] = None,
                         token_id: Optional[str] = None) -> List[str]:
        """Retrieve audit records with filtering."""
        records = []
        
        for log_file in self.audit_dir.glob("token_rotation_*.log"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse audit entry
                        parts = line.split('|')
                        if len(parts) < 9:
                            continue
                        
                        entry_time = datetime.fromisoformat(parts[0])
                        entry_operation = parts[1]
                        entry_token_id = parts[2]
                        
                        # Apply filters
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue
                        if operation and entry_operation != operation:
                            continue
                        if token_id and entry_token_id != token_id:
                            continue
                        
                        records.append(line)
            except Exception as e:
                logging.error(f"Failed to read audit file {log_file}: {e}")
        
        return sorted(records)


class APITokenManager:
    """Comprehensive API token management with rotation and audit capabilities."""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        
        # Initialize credential manager
        self.credential_manager = SecureCredentialManager(
            environment=environment,
            master_key_env="CREDENTIAL_MASTER_KEY"
        )
        
        # Initialize audit logger
        self.audit_logger = TokenRotationAuditLogger(environment)
        
        # Token configuration
        self.api_token_id = "adelaide_weather_api_token"
        self.backup_retention_days = 30
    
    def generate_new_token(self, 
                          length: int = 64,
                          user_id: str = "system") -> Tuple[str, TokenMetrics]:
        """Generate a new API token with comprehensive validation."""
        try:
            # Generate cryptographically secure token
            token = SecureTokenGenerator.generate_api_token(length=length)
            
            # Calculate metrics
            metrics = TokenEntropyValidator.calculate_entropy(token)
            
            # Validate token meets requirements
            is_valid, issues = TokenEntropyValidator.validate_token(token)
            if not is_valid:
                raise SecurityViolationError(f"Generated token failed validation: {', '.join(issues)}")
            
            # Log generation
            self.audit_logger.log_token_operation(
                operation="generate_token",
                token_id=self.api_token_id,
                token_value=token,
                user_id=user_id,
                success=True,
                details={
                    "length": length,
                    "entropy_bits": metrics.entropy_bits,
                    "security_level": metrics.security_level,
                    "charset_diversity": metrics.charset_diversity
                }
            )
            
            return token, metrics
            
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="generate_token",
                token_id=self.api_token_id,
                token_value="",
                user_id=user_id,
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def rotate_api_token(self, 
                        new_token: Optional[str] = None,
                        length: int = 64,
                        user_id: str = "system") -> Tuple[str, str]:
        """Rotate the API token with backup and audit trail."""
        try:
            # Generate new token if not provided
            if new_token is None:
                new_token, metrics = self.generate_new_token(length, user_id)
            else:
                # Validate provided token
                is_valid, issues = TokenEntropyValidator.validate_token(new_token)
                if not is_valid:
                    raise SecurityViolationError(f"Provided token failed validation: {', '.join(issues)}")
                metrics = TokenEntropyValidator.calculate_entropy(new_token)
            
            # Get current token for backup (if exists)
            old_token = None
            try:
                old_token = self.credential_manager.retrieve_credential(self.api_token_id, user_id)
            except CredentialNotFoundError:
                pass  # No existing token to backup
            
            # Create backup of old token if it exists
            backup_id = None
            if old_token:
                backup_id = f"{self.api_token_id}_backup_{int(time.time())}"
                try:
                    self.credential_manager.store_credential(
                        credential_id=backup_id,
                        credential_value=old_token,
                        credential_type=CredentialType.API_KEY,
                        security_level=SecurityLevel.HIGH,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=self.backup_retention_days),
                        tags={
                            "backup_of": self.api_token_id,
                            "rotation_time": datetime.now(timezone.utc).isoformat(),
                            "user_id": user_id
                        },
                        user_id=user_id
                    )
                except Exception as e:
                    logging.warning(f"Failed to create backup: {e}")
                    # Continue with rotation even if backup fails
                    backup_id = None
            
            # Store new token
            if old_token:
                # Delete old token first
                self.credential_manager.delete_credential(self.api_token_id, user_id)
            
            self.credential_manager.store_credential(
                credential_id=self.api_token_id,
                credential_value=new_token,
                credential_type=CredentialType.API_KEY,
                security_level=SecurityLevel.HIGH,
                tags={
                    "created_by": user_id,
                    "rotation_time": datetime.now(timezone.utc).isoformat(),
                    "entropy_bits": str(metrics.entropy_bits),
                    "security_level": metrics.security_level
                },
                user_id=user_id
            )
            
            # Log successful rotation
            self.audit_logger.log_token_operation(
                operation="rotate_token",
                token_id=self.api_token_id,
                token_value=new_token,
                user_id=user_id,
                success=True,
                details={
                    "backup_id": backup_id,
                    "entropy_bits": metrics.entropy_bits,
                    "security_level": metrics.security_level,
                    "had_previous_token": old_token is not None
                }
            )
            
            return new_token, backup_id
            
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="rotate_token",
                token_id=self.api_token_id,
                token_value="",
                user_id=user_id,
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def get_current_token(self, user_id: str = "system") -> Optional[str]:
        """Retrieve the current API token."""
        try:
            token = self.credential_manager.retrieve_credential(self.api_token_id, user_id)
            
            self.audit_logger.log_token_operation(
                operation="retrieve_token",
                token_id=self.api_token_id,
                token_value=token,
                user_id=user_id,
                success=True,
                details={}
            )
            
            return token
            
        except CredentialNotFoundError:
            return None
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="retrieve_token",
                token_id=self.api_token_id,
                token_value="",
                user_id=user_id,
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def validate_token(self, token: str, user_id: str = "system") -> Dict[str, Any]:
        """Validate a token and return detailed analysis."""
        try:
            # Calculate metrics
            metrics = TokenEntropyValidator.calculate_entropy(token)
            
            # Validate against requirements
            is_valid, issues = TokenEntropyValidator.validate_token(token)
            
            # Check if it's the current token
            current_token = self.get_current_token(user_id)
            is_current = current_token == token if current_token else False
            
            result = {
                "valid": is_valid,
                "issues": issues,
                "is_current_token": is_current,
                "metrics": {
                    "length": metrics.length,
                    "entropy_bits": metrics.entropy_bits,
                    "security_level": metrics.security_level,
                    "charset_diversity": metrics.charset_diversity,
                    "pattern_score": metrics.pattern_score
                }
            }
            
            self.audit_logger.log_token_operation(
                operation="validate_token",
                token_id="validation_request",
                token_value=token,
                user_id=user_id,
                success=True,
                details=result
            )
            
            return result
            
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="validate_token",
                token_id="validation_request",
                token_value="",
                user_id=user_id,
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def list_token_backups(self, user_id: str = "system") -> List[CredentialMetadata]:
        """List available token backups."""
        try:
            backups = self.credential_manager.list_credentials(
                credential_type=CredentialType.API_KEY
            )
            
            # Filter for backups of our API token
            token_backups = [
                backup for backup in backups
                if backup.credential_id.startswith(f"{self.api_token_id}_backup_")
            ]
            
            return sorted(token_backups, key=lambda x: x.created_at, reverse=True)
            
        except Exception as e:
            logging.error(f"Failed to list token backups: {e}")
            return []
    
    def restore_from_backup(self, backup_id: str, user_id: str = "system") -> str:
        """Restore API token from a backup."""
        try:
            # Retrieve backup token
            backup_token = self.credential_manager.retrieve_credential(backup_id, user_id)
            
            # Validate backup token
            is_valid, issues = TokenEntropyValidator.validate_token(backup_token)
            if not is_valid:
                raise SecurityViolationError(f"Backup token failed validation: {', '.join(issues)}")
            
            # Rotate to backup token
            self.rotate_api_token(new_token=backup_token, user_id=user_id)
            
            self.audit_logger.log_token_operation(
                operation="restore_from_backup",
                token_id=self.api_token_id,
                token_value=backup_token,
                user_id=user_id,
                success=True,
                details={"backup_id": backup_id}
            )
            
            return backup_token
            
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="restore_from_backup",
                token_id=self.api_token_id,
                token_value="",
                user_id=user_id,
                success=False,
                details={"backup_id": backup_id, "error": str(e)}
            )
            raise
    
    def export_for_environment(self, target_env_var: str = "API_TOKEN") -> str:
        """Export current token for environment variable use."""
        try:
            token = self.get_current_token()
            if not token:
                raise ValueError("No current API token found")
            
            export_command = f"export {target_env_var}='{token}'"
            
            self.audit_logger.log_token_operation(
                operation="export_token",
                token_id=self.api_token_id,
                token_value=token,
                user_id="system",
                success=True,
                details={"target_env_var": target_env_var}
            )
            
            return export_command
            
        except Exception as e:
            self.audit_logger.log_token_operation(
                operation="export_token",
                token_id=self.api_token_id,
                token_value="",
                user_id="system",
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get token management system health status."""
        try:
            # Check if token exists and is valid
            current_token = self.get_current_token()
            
            if current_token:
                validation = self.validate_token(current_token)
                
                # Check token metadata
                metadata = self.credential_manager.get_credential_metadata(self.api_token_id)
                
                # Check for upcoming expiration
                expires_soon = False
                if metadata and metadata.expires_at:
                    time_to_expiry = metadata.expires_at - datetime.now(timezone.utc)
                    expires_soon = time_to_expiry.days < 30
                
                # Count backups
                backups = self.list_token_backups()
                
                return {
                    "status": "healthy" if validation["valid"] else "degraded",
                    "token_exists": True,
                    "token_valid": validation["valid"],
                    "security_level": validation["metrics"]["security_level"],
                    "entropy_bits": validation["metrics"]["entropy_bits"],
                    "expires_soon": expires_soon,
                    "backup_count": len(backups),
                    "issues": validation.get("issues", [])
                }
            else:
                return {
                    "status": "degraded",
                    "token_exists": False,
                    "token_valid": False,
                    "issues": ["No API token configured"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


def create_cli_parser() -> argparse.ArgumentParser:
    """Create comprehensive CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Adelaide Weather API Token Rotation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate new token
  python token_rotation_cli.py generate --length 64

  # Rotate API token
  python token_rotation_cli.py rotate --user admin

  # Validate current token
  python token_rotation_cli.py validate

  # Export for environment
  python token_rotation_cli.py export

  # List backups
  python token_rotation_cli.py list-backups

  # Restore from backup
  python token_rotation_cli.py restore --backup-id adelaide_weather_api_token_backup_1699123456

  # Health check
  python token_rotation_cli.py health

  # View audit trail
  python token_rotation_cli.py audit --operation rotate_token --days 7
        """
    )
    
    parser.add_argument(
        '--environment', '-e',
        default=os.getenv('ENVIRONMENT', 'production'),
        help='Environment name (default: production)'
    )
    
    parser.add_argument(
        '--user', '-u',
        default=os.getenv('USER', 'system'),
        help='User ID for audit trail (default: system)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate new API token')
    generate_parser.add_argument(
        '--length', '-l',
        type=int,
        default=64,
        help='Token length (default: 64)'
    )
    generate_parser.add_argument(
        '--show-token',
        action='store_true',
        help='Display the generated token (security risk in logs)'
    )
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate API token')
    rotate_parser.add_argument(
        '--token',
        help='Specific token to rotate to (if not provided, generates new)'
    )
    rotate_parser.add_argument(
        '--length', '-l',
        type=int,
        default=64,
        help='Token length if generating new (default: 64)'
    )
    rotate_parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backup of old token (default: True)'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate token')
    validate_parser.add_argument(
        '--token',
        help='Token to validate (if not provided, validates current)'
    )
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export token for environment')
    export_parser.add_argument(
        '--env-var',
        default='API_TOKEN',
        help='Environment variable name (default: API_TOKEN)'
    )
    
    # List backups command
    subparsers.add_parser('list-backups', help='List available token backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument(
        '--backup-id',
        required=True,
        help='Backup ID to restore from'
    )
    
    # Health command
    subparsers.add_parser('health', help='Check token management health')
    
    # Audit command
    audit_parser = subparsers.add_parser('audit', help='View audit trail')
    audit_parser.add_argument(
        '--operation',
        help='Filter by operation type'
    )
    audit_parser.add_argument(
        '--token-id',
        help='Filter by token ID'
    )
    audit_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back (default: 30)'
    )
    audit_parser.add_argument(
        '--format',
        choices=['raw', 'table', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize token manager
        token_manager = APITokenManager(environment=args.environment)
        
        # Execute command
        if args.command == 'generate':
            token, metrics = token_manager.generate_new_token(
                length=args.length,
                user_id=args.user
            )
            
            print(f"✅ Generated new API token:")
            print(f"   Length: {metrics.length} characters")
            print(f"   Entropy: {metrics.entropy_bits:.1f} bits")
            print(f"   Security Level: {metrics.security_level}")
            print(f"   Character Diversity: {metrics.charset_diversity:.2f}")
            
            if args.show_token:
                print(f"\n⚠️  TOKEN (SENSITIVE): {token}")
                print("   ⚠️  This token should be stored securely and not logged!")
            else:
                print(f"\n🔒 Token generated but not displayed for security.")
                print("   Use 'export' command to get environment variable format.")
        
        elif args.command == 'rotate':
            new_token, backup_id = token_manager.rotate_api_token(
                new_token=args.token,
                length=args.length,
                user_id=args.user
            )
            
            print(f"✅ Successfully rotated API token")
            if backup_id:
                print(f"   📦 Backup created: {backup_id}")
            
            metrics = TokenEntropyValidator.calculate_entropy(new_token)
            print(f"   🔐 New token entropy: {metrics.entropy_bits:.1f} bits")
            print(f"   🛡️  Security level: {metrics.security_level}")
        
        elif args.command == 'validate':
            if args.token:
                token_to_validate = args.token
            else:
                token_to_validate = token_manager.get_current_token(args.user)
                if not token_to_validate:
                    print("❌ No current API token found")
                    return
            
            validation = token_manager.validate_token(token_to_validate, args.user)
            
            print(f"🔍 Token Validation Results:")
            print(f"   Valid: {'✅ Yes' if validation['valid'] else '❌ No'}")
            print(f"   Current Token: {'✅ Yes' if validation['is_current_token'] else '❌ No'}")
            print(f"   Length: {validation['metrics']['length']} characters")
            print(f"   Entropy: {validation['metrics']['entropy_bits']:.1f} bits")
            print(f"   Security Level: {validation['metrics']['security_level']}")
            print(f"   Pattern Score: {validation['metrics']['pattern_score']:.2f}")
            
            if validation['issues']:
                print(f"\n⚠️  Issues found:")
                for issue in validation['issues']:
                    print(f"   - {issue}")
        
        elif args.command == 'export':
            export_cmd = token_manager.export_for_environment(args.env_var)
            print(f"🔄 Environment variable export command:")
            print(f"   {export_cmd}")
            print(f"\n💡 To use: eval \"$(python {sys.argv[0]} export)\"")
        
        elif args.command == 'list-backups':
            backups = token_manager.list_token_backups(args.user)
            
            if not backups:
                print("📦 No token backups found")
                return
            
            print(f"📦 Available Token Backups ({len(backups)}):")
            print()
            for backup in backups:
                age = datetime.now(timezone.utc) - backup.created_at
                expires_in = backup.expires_at - datetime.now(timezone.utc) if backup.expires_at else None
                
                print(f"   🔑 {backup.credential_id}")
                print(f"      Created: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')} ({age.days} days ago)")
                if expires_in:
                    print(f"      Expires: {backup.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')} (in {expires_in.days} days)")
                print(f"      Access Count: {backup.access_count}")
                print()
        
        elif args.command == 'restore':
            restored_token = token_manager.restore_from_backup(args.backup_id, args.user)
            print(f"✅ Successfully restored API token from backup: {args.backup_id}")
            
            metrics = TokenEntropyValidator.calculate_entropy(restored_token)
            print(f"   🔐 Restored token entropy: {metrics.entropy_bits:.1f} bits")
            print(f"   🛡️  Security level: {metrics.security_level}")
        
        elif args.command == 'health':
            health = token_manager.get_health_status()
            
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️',
                'error': '❌'
            }.get(health.get('status'), '❓')
            
            print(f"{status_icon} Token Management Health: {health.get('status', 'unknown').upper()}")
            print()
            
            if 'token_exists' in health:
                print(f"   Token Exists: {'✅ Yes' if health['token_exists'] else '❌ No'}")
                
                if health['token_exists']:
                    print(f"   Token Valid: {'✅ Yes' if health['token_valid'] else '❌ No'}")
                    if 'security_level' in health:
                        print(f"   Security Level: {health['security_level']}")
                    if 'entropy_bits' in health:
                        print(f"   Entropy: {health['entropy_bits']:.1f} bits")
                    if 'backup_count' in health:
                        print(f"   Backups Available: {health['backup_count']}")
                    if health.get('expires_soon'):
                        print(f"   ⚠️  Token expires soon!")
            
            if health.get('issues'):
                print(f"\n⚠️  Issues:")
                for issue in health['issues']:
                    print(f"   - {issue}")
            
            if 'error' in health:
                print(f"\n❌ Error: {health['error']}")
        
        elif args.command == 'audit':
            # Calculate date range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=args.days)
            
            records = token_manager.audit_logger.get_audit_records(
                start_time=start_time,
                end_time=end_time,
                operation=args.operation,
                token_id=args.token_id
            )
            
            if not records:
                print(f"📋 No audit records found for the specified criteria")
                return
            
            print(f"📋 Audit Trail ({len(records)} records, last {args.days} days):")
            print()
            
            if args.format == 'raw':
                for record in records:
                    print(record)
            elif args.format == 'json':
                parsed_records = []
                for record in records:
                    parts = record.split('|')
                    if len(parts) >= 9:
                        parsed_records.append({
                            'timestamp': parts[0],
                            'operation': parts[1],
                            'token_id': parts[2],
                            'user_id': parts[3],
                            'environment': parts[4],
                            'result': parts[5],
                            'token_hash': parts[6],
                            'entropy': parts[7],
                            'security_level': parts[8],
                            'details': parts[9] if len(parts) > 9 else '{}'
                        })
                print(json.dumps(parsed_records, indent=2))
            else:  # table format
                print(f"{'Timestamp':<20} {'Operation':<15} {'User':<10} {'Result':<8} {'Security':<12} {'Details'}")
                print("-" * 90)
                
                for record in records:
                    parts = record.split('|')
                    if len(parts) >= 9:
                        timestamp = parts[0][:19].replace('T', ' ')
                        operation = parts[1][:14]
                        user = parts[3][:9]
                        result = parts[5][:7]
                        security = parts[8][:11]
                        
                        # Parse details for key info
                        details_str = ""
                        try:
                            details = json.loads(parts[9] if len(parts) > 9 else '{}')
                            if 'entropy_bits' in details:
                                details_str = f"entropy:{details['entropy_bits']:.0f}"
                            elif 'error' in details:
                                details_str = f"error:{details['error'][:20]}"
                        except:
                            pass
                        
                        print(f"{timestamp} {operation:<15} {user:<10} {result:<8} {security:<12} {details_str}")
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()