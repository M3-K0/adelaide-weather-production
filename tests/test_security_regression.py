"""
Regression tests for security fixes across multiple files.

Covers:
  H3  - No active CORS wildcard in nginx.conf
  M4  - variables.py uses regex validation (not .replace chain)
  L2  - ForecastCache respects max_size
  L3  - CSP header does not contain unsafe-inline
  L4  - SQL injection regex uses word boundaries
"""

import re
import inspect
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ===================================================================
# H3: No active CORS wildcard in nginx.conf
# ===================================================================

class TestH3NginxCORS:
    """H3: nginx.conf must not have active Access-Control-Allow-Origin directives."""

    def test_regression_h3_no_cors_wildcard_in_nginx(self):
        """nginx.conf must not contain active Access-Control-Allow-Origin headers."""
        nginx_path = PROJECT_ROOT / "nginx" / "nginx.conf"
        if not nginx_path.exists():
            pytest.skip("nginx.conf not found")

        content = nginx_path.read_text()
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip commented-out lines
            if stripped.startswith("#"):
                continue
            assert "Access-Control-Allow-Origin" not in stripped, (
                f"nginx.conf line {i} has active CORS header: {stripped}"
            )


# ===================================================================
# M4: Variable validation uses regex, not .replace chain
# ===================================================================

class TestM4VariableValidation:
    """M4: Variable name validation should use regex, not a chain of .replace calls."""

    def test_regression_m4_parse_variables_uses_regex(self):
        """parse_variables should validate variable names with regex pattern."""
        from api.variables import parse_variables
        source = inspect.getsource(parse_variables)
        assert "re.match" in source or "VARIABLE_PATTERN" in source, (
            "parse_variables does not use regex for variable name validation"
        )

    def test_regression_m4_security_config_uses_regex(self):
        """SecurityConfig.VARIABLE_PATTERN should be a compiled regex."""
        from api.security_middleware import SecurityConfig
        assert hasattr(SecurityConfig, "VARIABLE_PATTERN")
        assert hasattr(SecurityConfig.VARIABLE_PATTERN, "match"), (
            "VARIABLE_PATTERN is not a compiled regex"
        )

    def test_regression_m4_variable_pattern_rejects_injection(self):
        """VARIABLE_PATTERN should reject injection attempts."""
        from api.security_middleware import SecurityConfig
        pattern = SecurityConfig.VARIABLE_PATTERN

        # Valid names
        assert pattern.match("t2m")
        assert pattern.match("z500")
        assert pattern.match("cape")

        # Invalid names
        assert not pattern.match("t2m; DROP TABLE")
        assert not pattern.match("<script>alert(1)</script>")
        assert not pattern.match("a" * 21)  # > 20 chars
        assert not pattern.match("")


# ===================================================================
# L2: ForecastCache respects max_size
# ===================================================================

class TestL2CacheMaxSize:
    """L2: ForecastCache must enforce max_size limit."""

    def test_regression_l2_cache_evicts_at_max_size(self):
        """Cache should not grow beyond max_size entries."""
        from api.performance_middleware import ForecastCache

        cache = ForecastCache(default_ttl=300, max_size=5)

        # Insert more than max_size entries
        for i in range(10):
            cache.set(f"horizon_{i}", f"vars_{i}", {"data": i})

        assert len(cache.cache) <= 5, (
            f"Cache has {len(cache.cache)} entries, max_size is 5"
        )

    def test_regression_l2_cache_constructor_accepts_max_size(self):
        """ForecastCache constructor must accept max_size parameter."""
        from api.performance_middleware import ForecastCache
        cache = ForecastCache(max_size=100)
        assert cache.max_size == 100

    def test_regression_l2_cache_eviction_preserves_newest(self):
        """After eviction, the most recent entries should remain."""
        from api.performance_middleware import ForecastCache

        cache = ForecastCache(default_ttl=300, max_size=3)

        cache.set("h1", "v1", {"data": 1})
        cache.set("h2", "v2", {"data": 2})
        cache.set("h3", "v3", {"data": 3})
        cache.set("h4", "v4", {"data": 4})  # Should evict oldest

        assert len(cache.cache) <= 3
        # The newest entry should still be present
        assert cache.get("h4", "v4") is not None


# ===================================================================
# L3: CSP header must not contain unsafe-inline
# ===================================================================

class TestL3CSPHeader:
    """L3: Content-Security-Policy must not include unsafe-inline."""

    def test_regression_l3_csp_no_unsafe_inline(self):
        """SecurityConfig.SECURITY_HEADERS CSP must not contain 'unsafe-inline'."""
        from api.security_middleware import SecurityConfig

        csp = SecurityConfig.SECURITY_HEADERS.get("Content-Security-Policy", "")
        assert "unsafe-inline" not in csp, (
            f"CSP still contains 'unsafe-inline': {csp}"
        )

    def test_regression_l3_csp_has_default_src(self):
        """CSP must include default-src directive."""
        from api.security_middleware import SecurityConfig
        csp = SecurityConfig.SECURITY_HEADERS.get("Content-Security-Policy", "")
        assert "default-src" in csp


# ===================================================================
# L4: SQL injection regex uses word boundaries
# ===================================================================

class TestL4SQLInjectionRegex:
    """L4: SQL injection patterns should use word boundaries to reduce false positives."""

    def test_regression_l4_sql_patterns_use_word_boundaries(self):
        """SQL injection regex patterns should include \\b for word boundaries."""
        from api.security_middleware import SecurityConfig

        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            pattern_str = pattern.pattern
            # At least the first pattern (keyword matching) should use \b
            if "select" in pattern_str.lower() or "union" in pattern_str.lower():
                assert r"\b" in pattern_str, (
                    f"SQL pattern missing word boundaries: {pattern_str}"
                )

    def test_regression_l4_no_false_positive_on_selection(self):
        """The word 'selection' (containing 'select') should not trigger if boundaries are used."""
        from api.security_middleware import SecurityConfig

        # With word boundaries, 'selection' should not match \bselect\b
        test_input = "variable_selection"
        first_pattern = SecurityConfig.SQL_INJECTION_PATTERNS[0]
        match = first_pattern.search(test_input)
        assert match is None, (
            f"'variable_selection' falsely matched SQL injection pattern"
        )
