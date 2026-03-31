"""
Regression tests for api/enhanced_token_manager.py fixes.

Covers:
  M1  - No bare except: blocks (must use except Exception:)
"""

import ast
import inspect
import pytest

from api.enhanced_token_manager import BackwardCompatibleTokenManager


# ===================================================================
# M1: No bare except: blocks
# ===================================================================

class TestM1NoBareExcept:
    """M1: enhanced_token_manager must not use bare `except:` blocks."""

    def test_regression_m1_no_bare_except_in_source(self):
        """Inspect the AST to verify no bare except handlers exist."""
        import api.enhanced_token_manager as mod
        source = inspect.getsource(mod)
        tree = ast.parse(source)

        bare_excepts = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # A bare except has node.type == None
                if node.type is None:
                    bare_excepts.append(node.lineno)

        assert len(bare_excepts) == 0, (
            f"Bare except: blocks found at lines: {bare_excepts}"
        )

    def test_regression_m1_source_text_no_bare_except(self):
        """Double-check via text search for the pattern 'except:'."""
        import api.enhanced_token_manager as mod
        source = inspect.getsource(mod)

        import re
        # Match `except:` at line start (possibly indented), but NOT `except SomeException:`
        bare_pattern = re.compile(r"^\s*except\s*:\s*$", re.MULTILINE)
        matches = bare_pattern.findall(source)
        assert len(matches) == 0, (
            f"Found {len(matches)} bare 'except:' in enhanced_token_manager.py"
        )

    def test_regression_m1_validate_token_handles_exceptions(self):
        """validate_token should catch Exception, not everything."""
        manager = BackwardCompatibleTokenManager(environment="development")
        # Should not crash on invalid input
        is_valid, details = manager.validate_token("")
        assert not is_valid

    def test_regression_m1_get_api_token_handles_exceptions(self):
        """get_api_token should work without crashing."""
        manager = BackwardCompatibleTokenManager(environment="development")
        # Should return None or a string, never raise bare exceptions
        token = manager.get_api_token()
        assert token is None or isinstance(token, str)
