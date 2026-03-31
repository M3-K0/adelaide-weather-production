"""
Regression tests for core/model_loader.py fixes.

Covers:
  C3  - Variable count mismatch (9 vs 11)
  C4  - Unsafe pickle loading gated by env var
"""

import os
import tempfile
import pytest
import torch
import torch.nn as nn
from unittest.mock import patch
from core.model_loader import (
    WeatherCNNEncoder,
    _load_checkpoint_safe,
    load_model_safe,
)


# ===================================================================
# C3: Variable count — model must default to 9
# ===================================================================

class TestC3VariableCount:
    """C3: CNN model must use num_variables=9 consistently."""

    def test_regression_c3_default_num_variables(self):
        """WeatherCNNEncoder default num_variables must be 9."""
        model = WeatherCNNEncoder()
        assert model.num_variables == 9, (
            f"Default num_variables={model.num_variables}, expected 9"
        )

    def test_regression_c3_accepts_9_channel_input(self, weather_cnn_encoder):
        """Model must accept (B, 9, 16, 16) input without error."""
        batch_size = 2
        x = torch.randn(batch_size, 9, 16, 16)
        lead_times = torch.tensor([6, 12])
        months = torch.tensor([0, 6])
        hours = torch.tensor([0, 12])

        with torch.no_grad():
            output = weather_cnn_encoder(x, lead_times, months, hours)

        assert output.shape == (batch_size, 256), f"Output shape {output.shape}, expected ({batch_size}, 256)"

    def test_regression_c3_output_l2_normalized(self, weather_cnn_encoder):
        """Output embeddings must be L2-normalized (unit norm)."""
        x = torch.randn(4, 9, 16, 16)
        lead_times = torch.tensor([6, 12, 24, 48])
        months = torch.tensor([0, 3, 6, 9])
        hours = torch.tensor([0, 6, 12, 18])

        with torch.no_grad():
            output = weather_cnn_encoder(x, lead_times, months, hours)

        norms = output.norm(dim=1)
        assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5), (
            f"Embedding norms not ~1.0: {norms.tolist()}"
        )

    def test_regression_c3_rejects_11_channel_input(self):
        """Passing 11-channel input to a 9-channel model should raise."""
        model = WeatherCNNEncoder(num_variables=9)
        x = torch.randn(1, 11, 16, 16)
        lead_times = torch.tensor([6])
        months = torch.tensor([0])
        hours = torch.tensor([0])

        with pytest.raises(RuntimeError):
            model(x, lead_times, months, hours)

    def test_regression_c3_first_conv_layer_in_channels(self, weather_cnn_encoder):
        """First convolutional layer must have in_channels=9."""
        first_stage = weather_cnn_encoder.stages[0]
        in_channels = first_stage.conv.in_channels
        assert in_channels == 9, f"First conv in_channels={in_channels}, expected 9"

    def test_regression_c3_embedding_dim_256(self, weather_cnn_encoder):
        """Default embedding_dim must be 256."""
        assert weather_cnn_encoder.embedding_dim == 256


# ===================================================================
# C4: Safe model loading — weights_only=True by default
# ===================================================================

class TestC4SafeModelLoading:
    """C4: Model loading must use weights_only=True by default."""

    def test_regression_c4_safe_load_with_pure_weights(self, tmp_path):
        """A checkpoint with only tensors should load with weights_only=True."""
        # Create a minimal state_dict checkpoint
        model = WeatherCNNEncoder(num_variables=9)
        checkpoint_path = tmp_path / "safe_model.pt"
        torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)

        # Should succeed without ALLOW_UNSAFE_MODEL_LOAD
        loaded = _load_checkpoint_safe(checkpoint_path)
        assert "model_state_dict" in loaded

    def test_regression_c4_unsafe_load_blocked_without_env_var(self, tmp_path):
        """Without ALLOW_UNSAFE_MODEL_LOAD, unsafe checkpoints must raise RuntimeError."""
        # Use ProductionTrainingConfig (a module-level class) to create an unsafe
        # checkpoint that requires weights_only=False to deserialize.
        from core.model_loader import ProductionTrainingConfig

        checkpoint_path = tmp_path / "unsafe_model.pt"
        torch.save(
            {"config": ProductionTrainingConfig(epochs=10), "model_state_dict": {}},
            checkpoint_path,
        )

        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("ALLOW_UNSAFE_MODEL_LOAD", None)

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="unsafe loading is not permitted"):
                _load_checkpoint_safe(checkpoint_path)

    def test_regression_c4_unsafe_load_allowed_with_env_var(self, tmp_path):
        """With ALLOW_UNSAFE_MODEL_LOAD=true, unsafe checkpoints should load."""
        # Create a checkpoint that requires unsafe loading
        import sys
        from core.model_loader import ProductionTrainingConfig

        checkpoint_path = tmp_path / "legacy_model.pt"
        config = ProductionTrainingConfig(epochs=100, lr=0.001)
        model = WeatherCNNEncoder(num_variables=9)
        torch.save(
            {"config": config, "model_state_dict": model.state_dict()},
            checkpoint_path,
        )

        with patch.dict(os.environ, {"ALLOW_UNSAFE_MODEL_LOAD": "true"}):
            loaded = _load_checkpoint_safe(checkpoint_path)
            assert "model_state_dict" in loaded

    def test_regression_c4_load_model_safe_returns_correct_architecture(self, tmp_path):
        """load_model_safe should return a model with num_variables=9."""
        model = WeatherCNNEncoder(num_variables=9)
        checkpoint_path = tmp_path / "model.pt"
        torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)

        loaded_model = load_model_safe(str(checkpoint_path), require_exact_match=True)
        assert loaded_model is not None
        assert loaded_model.num_variables == 9

    def test_regression_c4_source_does_not_hardcode_weights_only_false(self):
        """_load_checkpoint_safe should try weights_only=True first."""
        import inspect
        source = inspect.getsource(_load_checkpoint_safe)
        assert "weights_only=True" in source, (
            "_load_checkpoint_safe does not attempt weights_only=True"
        )
