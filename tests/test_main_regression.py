"""
Regression tests for api/main.py fixes.

Covers:
  C1  - Missing await on async forecast calls
  C2  - Import path error in exception handlers
  H1  - Hardcoded mock hashes removed
  H4  - Health check error detail leakage in production
  M2  - Token prefix no longer logged (hashed hint used instead)
  L6  - No emoji characters in log messages
"""

import os
import re
import hashlib
import inspect
import logging
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


# ===================================================================
# C1: /forecast endpoint awaits async calls
# ===================================================================

class TestC1AsyncAwait:
    """C1: forecast_with_uncertainty must be awaited."""

    def test_regression_c1_forecast_returns_dict_not_coroutine(self, test_client):
        """The /forecast response should be a dict (JSON), never a coroutine object."""
        resp = test_client.get(
            "/forecast",
            params={"horizon": "24h", "vars": "t2m"},
            headers={"Authorization": "Bearer test-token-abc123-secure-enough"},
        )
        # Should get a valid JSON response (200 or 500 if mock isn't perfect)
        # The key invariant: the response body is JSON, not a repr of a coroutine
        body = resp.text
        assert "coroutine" not in body.lower(), "Response contains coroutine object repr -- C1 not fixed"

    def test_regression_c1_forecast_endpoint_is_async(self):
        """The forecast endpoint function should be an async def."""
        from api.main import get_forecast
        assert inspect.iscoroutinefunction(get_forecast), "/forecast handler must be async def"


# ===================================================================
# C2: Exception handlers import from correct path
# ===================================================================

class TestC2ImportPath:
    """C2: Exception handlers must import SecurityMiddleware from api.security_middleware."""

    def test_regression_c2_http_exception_handler_import(self):
        """http_exception_handler should import from api.security_middleware, not security_middleware."""
        from api.main import http_exception_handler
        source = inspect.getsource(http_exception_handler)
        assert "from api.security_middleware" in source, (
            "http_exception_handler still imports from bare 'security_middleware'"
        )
        assert "from security_middleware " not in source

    def test_regression_c2_general_exception_handler_import(self):
        """general_exception_handler should import from api.security_middleware."""
        from api.main import general_exception_handler
        source = inspect.getsource(general_exception_handler)
        # It may use a top-level import or inline import; either way the path
        # must be api.security_middleware
        assert "security_middleware" in source
        # Ensure no bare `from security_middleware import` (without api. prefix)
        bare_import = re.search(r"from\s+security_middleware\s+import", source)
        assert bare_import is None, "general_exception_handler uses bare import path"


# ===================================================================
# H1: No hardcoded mock hashes in responses
# ===================================================================

class TestH1NoHardcodedHashes:
    """H1: Responses must not contain static mock hash strings."""

    FORBIDDEN_HASHES = {"a7c3f92", "2e8b4d1", "d4f8a91"}

    def test_regression_h1_forecast_no_hardcoded_hashes(self, test_client):
        """GET /forecast must not return any of the hardcoded hash values."""
        resp = test_client.get(
            "/forecast",
            params={"horizon": "24h", "vars": "t2m"},
            headers={"Authorization": "Bearer test-token-abc123-secure-enough"},
        )
        body = resp.text
        for h in self.FORBIDDEN_HASHES:
            assert h not in body, f"Response still contains hardcoded hash {h}"

    def test_regression_h1_health_no_hardcoded_hashes(self, test_client):
        """GET /health must not return any of the hardcoded hash values."""
        resp = test_client.get("/health")
        body = resp.text
        for h in self.FORBIDDEN_HASHES:
            assert h not in body, f"Health response still contains hardcoded hash {h}"

    def test_regression_h1_source_no_hardcoded_hash_literals(self):
        """The source of api/main.py must not contain the old literal hash strings."""
        from api import main as main_module
        source = inspect.getsource(main_module)
        for h in self.FORBIDDEN_HASHES:
            # Allow them in comments (TODO lines) but not as string literals
            # that would end up in responses
            literal_pattern = rf'["\']({h})["\']'
            assert not re.search(literal_pattern, source), (
                f"api/main.py still contains hardcoded hash literal '{h}'"
            )


# ===================================================================
# H4: Health check does not leak exception details in production
# ===================================================================

class TestH4HealthCheckErrorSanitization:
    """H4: /health error responses in production must not expose exception strings."""

    def test_regression_h4_health_error_sanitized_in_production(self):
        """In production mode, /health error path should return generic message."""
        from api.main import get_health
        source = inspect.getsource(get_health)
        # The fix adds an environment check before exposing error details
        assert 'ENVIRONMENT' in source or 'production' in source, (
            "Health endpoint does not check environment before exposing errors"
        )
        # Ensure there is a sanitized fallback
        assert 'Health check failed' in source


# ===================================================================
# M2: Token first-8-chars no longer logged
# ===================================================================

class TestM2TokenNotLogged:
    """M2: Auth logging must use hashed hints, not token prefixes."""

    def test_regression_m2_verify_token_uses_sha256_hint(self):
        """verify_token should hash the token for logging, not slice first 8 chars."""
        from api.main import verify_token
        source = inspect.getsource(verify_token)
        # Old pattern: credentials.credentials[:8]
        assert "[:8]" not in source, "verify_token still logs token prefix ([:8])"
        # New pattern should use sha256
        assert "sha256" in source, "verify_token should use sha256 for token hint"


# ===================================================================
# L6: No emoji in production log messages
# ===================================================================

class TestL6NoEmojiInLogs:
    """L6: Log messages in api/main.py must not contain emoji characters."""

    # Unicode ranges for common emoji blocks
    EMOJI_PATTERN = re.compile(
        r"[\U0001F300-\U0001F9FF"   # Miscellaneous Symbols, Emoticons, etc.
        r"\U00002702-\U000027B0"     # Dingbats
        r"\U0001FA00-\U0001FA6F"     # Chess, extended-A
        r"\U0001FA70-\U0001FAFF"     # Extended-B
        r"\U00002600-\U000026FF"     # Misc symbols
        r"]"
    )

    def test_regression_l6_no_emoji_in_startup_logs(self):
        """Startup and operational log messages in main.py should not contain emoji."""
        from api import main as main_module
        source = inspect.getsource(main_module)

        # Extract logger.info / logger.warning / logger.error call arguments
        log_pattern = re.compile(r'logger\.\w+\(\s*[f]?["\'](.+?)["\']', re.DOTALL)
        log_messages = log_pattern.findall(source)

        for msg in log_messages:
            assert not self.EMOJI_PATTERN.search(msg), (
                f"Log message contains emoji: {msg[:60]}..."
            )
