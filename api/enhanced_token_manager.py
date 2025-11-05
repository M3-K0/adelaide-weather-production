#!/usr/bin/env python3
"""
Adelaide Weather API - Enhanced Token Manager
=============================================

Provides backward compatibility layer for API token management while
integrating with the new secure credential management system.

Features:
- Seamless integration with existing API_TOKEN environment variable
- Automatic token migration to secure credential storage
- Enhanced validation with entropy checking
- Fallback mechanisms for operational continuity
- Comprehensive audit logging for security compliance

This module ensures that existing deployments continue to work while
providing enhanced security features for new installations.

Author: Security Integration Team
Version: 1.0.0 - Backward Compatible Token Management
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

# Import our token management components
try:
    from api.token_rotation_cli import APITokenManager, TokenEntropyValidator
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False
    logging.warning("Enhanced token features not available - falling back to basic validation")


class BackwardCompatibleTokenManager:
    """
    Provides backward compatibility for API token management.
    
    This class bridges the existing environment variable-based token system
    with the new secure credential management system, ensuring operational
    continuity while providing enhanced security features when available.
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self._api_token_cache: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Initialize enhanced token manager if available
        self.enhanced_manager: Optional[APITokenManager] = None
        if ENHANCED_FEATURES_AVAILABLE:
            try:
                self.enhanced_manager = APITokenManager(environment)
                logging.info("Enhanced token management features available")
            except Exception as e:
                logging.warning(f"Could not initialize enhanced token manager: {e}")
    
    def get_api_token(self) -> Optional[str]:
        """
        Get the current API token with fallback mechanisms.
        
        Priority order:
        1. Enhanced credential manager (if available and configured)
        2. Environment variable API_TOKEN
        3. Cached value (if recent)
        
        Returns:
            The current API token or None if not found
        """
        current_time = datetime.now(timezone.utc)
        
        # Check cache first (for performance)
        if (self._api_token_cache and self._cache_timestamp and 
            (current_time - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds):
            return self._api_token_cache
        
        # Try enhanced credential manager first
        if self.enhanced_manager:
            try:
                token = self.enhanced_manager.get_current_token()
                if token:
                    self._update_cache(token, current_time)
                    return token
            except Exception as e:
                logging.warning(f"Failed to retrieve token from enhanced manager: {e}")
        
        # Fallback to environment variable
        env_token = os.getenv("API_TOKEN")
        if env_token:
            # Migrate to secure storage if enhanced features are available
            if self.enhanced_manager and not self._is_token_migrated():
                try:
                    self._migrate_env_token_to_secure_storage(env_token)
                except Exception as e:
                    logging.warning(f"Failed to migrate token to secure storage: {e}")
            
            self._update_cache(env_token, current_time)
            return env_token
        
        # No token found
        return None
    
    def validate_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a token with enhanced security checks when available.
        
        Args:
            token: The token to validate
            
        Returns:
            Tuple of (is_valid, validation_details)
        """
        if not token:
            return False, {"error": "Empty token"}
        
        # Enhanced validation if available
        if self.enhanced_manager:
            try:
                validation_result = self.enhanced_manager.validate_token(token)
                return validation_result["valid"], validation_result
            except Exception as e:
                logging.warning(f"Enhanced validation failed, falling back to basic: {e}")
        
        # Basic validation fallback
        if len(token) < 8:
            return False, {"error": "Token too short"}
        
        if len(token) > 128:
            return False, {"error": "Token too long"}
        
        # Check for obvious weak patterns
        weak_patterns = ['test', 'demo', 'example', 'password', 'secret', 'admin']
        if any(pattern in token.lower() for pattern in weak_patterns):
            return False, {"error": "Token contains weak patterns"}
        
        return True, {"valid": True, "method": "basic"}
    
    def is_current_token(self, token: str) -> bool:
        """
        Check if the provided token is the current API token.
        
        Args:
            token: Token to check
            
        Returns:
            True if this is the current token
        """
        current_token = self.get_api_token()
        return current_token == token if current_token else False
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current token configuration.
        
        Returns:
            Dictionary with token configuration details
        """
        current_token = self.get_api_token()
        
        if not current_token:
            return {
                "configured": False,
                "source": "none",
                "enhanced_features": ENHANCED_FEATURES_AVAILABLE
            }
        
        info = {
            "configured": True,
            "enhanced_features": ENHANCED_FEATURES_AVAILABLE,
            "has_env_var": bool(os.getenv("API_TOKEN")),
            "cache_active": bool(self._api_token_cache)
        }
        
        # Determine source
        if self.enhanced_manager:
            try:
                secure_token = self.enhanced_manager.get_current_token()
                if secure_token:
                    info["source"] = "secure_storage"
                    if secure_token == os.getenv("API_TOKEN"):
                        info["source"] = "both"  # Available in both places
                else:
                    info["source"] = "environment"
            except:
                info["source"] = "environment"
        else:
            info["source"] = "environment"
        
        # Add validation info
        is_valid, validation_details = self.validate_token(current_token)
        info["valid"] = is_valid
        info["validation"] = validation_details
        
        return info
    
    def _update_cache(self, token: str, timestamp: datetime) -> None:
        """Update the token cache."""
        self._api_token_cache = token
        self._cache_timestamp = timestamp
    
    def _is_token_migrated(self) -> bool:
        """Check if the environment token has been migrated to secure storage."""
        if not self.enhanced_manager:
            return False
        
        try:
            secure_token = self.enhanced_manager.get_current_token()
            env_token = os.getenv("API_TOKEN")
            return secure_token == env_token if (secure_token and env_token) else False
        except:
            return False
    
    def _migrate_env_token_to_secure_storage(self, env_token: str) -> None:
        """
        Migrate environment token to secure credential storage.
        
        This is done automatically when enhanced features are available
        and the token hasn't been migrated yet.
        """
        if not self.enhanced_manager:
            return
        
        # Validate the token before migration
        is_valid, validation_details = self.validate_token(env_token)
        if not is_valid:
            logging.warning(f"Skipping migration of invalid token: {validation_details.get('error')}")
            return
        
        try:
            # Check if we already have a token in secure storage
            existing_token = self.enhanced_manager.get_current_token()
            if existing_token:
                # Don't migrate if we already have a different token
                if existing_token != env_token:
                    logging.info("Secure storage already contains a different token - skipping migration")
                    return
                else:
                    logging.info("Token already migrated to secure storage")
                    return
            
            # Perform migration
            self.enhanced_manager.rotate_api_token(
                new_token=env_token,
                user_id="auto_migration"
            )
            
            logging.info("Successfully migrated API token to secure credential storage")
            
        except Exception as e:
            logging.error(f"Failed to migrate token to secure storage: {e}")
            raise
    
    def force_cache_refresh(self) -> None:
        """Force refresh of the token cache."""
        self._api_token_cache = None
        self._cache_timestamp = None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the token management system."""
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "enhanced_features": ENHANCED_FEATURES_AVAILABLE,
            "token_configured": False,
            "token_valid": False,
            "source": "none",
            "issues": []
        }
        
        # Check token configuration
        token_info = self.get_token_info()
        status.update(token_info)
        
        if not token_info["configured"]:
            status["issues"].append("No API token configured")
            return status
        
        # Check enhanced manager health if available
        if self.enhanced_manager:
            try:
                enhanced_health = self.enhanced_manager.get_health_status()
                status["enhanced_health"] = enhanced_health
                
                if enhanced_health.get("status") != "healthy":
                    status["issues"].extend(enhanced_health.get("issues", []))
                    
            except Exception as e:
                status["issues"].append(f"Enhanced token manager error: {str(e)}")
        
        # Determine overall status
        if status["token_configured"] and status["token_valid"] and not status["issues"]:
            status["overall_status"] = "healthy"
        elif status["token_configured"] and status["token_valid"]:
            status["overall_status"] = "warning"
        else:
            status["overall_status"] = "error"
        
        return status


# Global instance for backward compatibility
_global_token_manager: Optional[BackwardCompatibleTokenManager] = None


def get_token_manager() -> BackwardCompatibleTokenManager:
    """Get the global token manager instance."""
    global _global_token_manager
    
    if _global_token_manager is None:
        environment = os.getenv("ENVIRONMENT", "production")
        _global_token_manager = BackwardCompatibleTokenManager(environment)
    
    return _global_token_manager


def get_api_token() -> Optional[str]:
    """
    Convenience function to get the current API token.
    
    This function maintains backward compatibility with existing code
    that expects to get tokens from environment variables.
    """
    return get_token_manager().get_api_token()


def validate_api_token(token: str) -> bool:
    """
    Convenience function to validate an API token.
    
    Args:
        token: Token to validate
        
    Returns:
        True if the token is valid
    """
    is_valid, _ = get_token_manager().validate_token(token)
    return is_valid


def is_current_api_token(token: str) -> bool:
    """
    Convenience function to check if a token is the current API token.
    
    Args:
        token: Token to check
        
    Returns:
        True if this is the current API token
    """
    return get_token_manager().is_current_token(token)


# Export public interface
__all__ = [
    'BackwardCompatibleTokenManager',
    'get_token_manager',
    'get_api_token',
    'validate_api_token',
    'is_current_api_token'
]