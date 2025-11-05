#!/usr/bin/env python3
"""
Standalone Model Loader
=======================

Loads the trained CNN model without requiring training dependencies.
Handles checkpoint loading issues by extracting just the model weights.
Implements the exact architecture from the trained model with robust loading.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import pickle
import math
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class ProductionTrainingConfig:
    """Dummy config class to handle checkpoint loading."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation layer."""
    
    def __init__(self, feature_dim, condition_dim):
        super().__init__()
        self.scale = nn.Linear(condition_dim, feature_dim)
        self.shift = nn.Linear(condition_dim, feature_dim)
        
        # Safe initialization for gradient flow
        self.scale.weight.data.zero_()
        self.scale.bias.data.fill_(1.0)  # gamma = 1
        self.shift.weight.data.zero_()  
        self.shift.bias.data.fill_(0.0)  # beta = 0
        
    def forward(self, x, condition):
        """
        Apply FiLM conditioning.
        x: (B, C, H, W) feature maps
        condition: (B, condition_dim) conditioning vector
        """
        gamma = self.scale(condition).unsqueeze(-1).unsqueeze(-1)  # (B, C, 1, 1)
        beta = self.shift(condition).unsqueeze(-1).unsqueeze(-1)    # (B, C, 1, 1)
        return gamma * x + beta

class ASPPModule(nn.Module):
    """Atrous Spatial Pyramid Pooling module."""
    
    def __init__(self, in_channels, out_channels, dilation_rates):
        super().__init__()
        
        self.convs = nn.ModuleList()
        
        # 1x1 convolution
        self.convs.append(nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        ))
        
        # Dilated convolutions
        for rate in dilation_rates:
            self.convs.append(nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 3, padding=rate, dilation=rate),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            ))
        
        # Global average pooling
        self.global_pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
        # Final projection
        total_channels = out_channels * (len(dilation_rates) + 2)  # +2 for 1x1 and global pool
        self.project = nn.Sequential(
            nn.Conv2d(total_channels, out_channels, 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
    
    def forward(self, x):
        results = []
        
        # Apply all dilated convolutions
        for conv in self.convs:
            results.append(conv(x))
        
        # Global average pooling
        global_feat = self.global_pool(x)
        global_feat = F.interpolate(global_feat, size=x.shape[2:], mode='bilinear', align_corners=False)
        results.append(global_feat)
        
        # Concatenate and project
        out = torch.cat(results, dim=1)
        out = self.project(out)
        
        return out

class LeadTimeEmbedding(nn.Module):
    """Sinusoidal position encoding for lead time."""
    
    def __init__(self, embedding_dim, max_lead_time=72):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.max_lead_time = max_lead_time
        
        # Create sinusoidal embeddings
        position = torch.arange(0, max_lead_time + 1, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, embedding_dim, 2).float() * 
                           (-math.log(10000.0) / embedding_dim))
        
        pe = torch.zeros(max_lead_time + 1, embedding_dim)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe)
    
    def forward(self, lead_times):
        """lead_times: (B,) tensor of lead times in hours"""
        lead_times = torch.clamp(lead_times, 0, self.max_lead_time).long()
        return self.pe[lead_times]

class SeasonalEmbedding(nn.Module):
    """Learnable embeddings for seasonal information."""
    
    def __init__(self, embedding_dim):
        super().__init__()
        self.month_embed = nn.Embedding(12, embedding_dim // 2)
        self.hour_embed = nn.Embedding(24, embedding_dim // 2)
    
    def forward(self, months, hours):
        """
        months: (B,) tensor of months (0-11)
        hours: (B,) tensor of hours (0-23)
        """
        month_emb = self.month_embed(months)
        hour_emb = self.hour_embed(hours)
        return torch.cat([month_emb, hour_emb], dim=1)

class CNNEncoderStage(nn.Module):
    """Single stage of CNN encoder with optional FiLM conditioning."""
    
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=2, 
                 use_film=False, condition_dim=None):
        super().__init__()
        
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, 
                             stride=stride, padding=kernel_size//2)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.use_film = use_film
        if use_film and condition_dim is not None:
            self.film = FiLMLayer(out_channels, condition_dim)
    
    def forward(self, x, condition=None):
        x = self.conv(x)
        x = self.bn(x)
        
        if self.use_film and condition is not None:
            x = self.film(x, condition)
        
        x = self.relu(x)
        return x

class WeatherCNNEncoder(nn.Module):
    """CNN encoder for weather pattern embeddings with FiLM conditioning.
    
    This matches the exact architecture from the training checkpoint.
    """
    
    def __init__(self, embedding_dim=256, num_variables=11):
        super().__init__()
        
        self.embedding_dim = embedding_dim
        self.num_variables = num_variables
        
        # Build conditioning embeddings (matches config)
        lead_embed_dim = 64
        seasonal_embed_dim = 32
        
        self.lead_time_embedding = LeadTimeEmbedding(lead_embed_dim, max_lead_time=72)
        self.seasonal_embedding = SeasonalEmbedding(seasonal_embed_dim)
        
        # Total conditioning dimension
        self.condition_dim = lead_embed_dim + seasonal_embed_dim  # 96
        
        # CNN stages (matches config architecture)
        self.stages = nn.ModuleList()
        film_layers = [1, 2, 3, 4]  # Apply FiLM to all stages
        
        # Stage configurations from model.yaml
        stage_configs = [
            {'in_ch': num_variables, 'out_ch': 32, 'kernel': 5, 'stride': 2},
            {'in_ch': 32, 'out_ch': 64, 'kernel': 3, 'stride': 2},
            {'in_ch': 64, 'out_ch': 128, 'kernel': 3, 'stride': 2},
            {'in_ch': 128, 'out_ch': 256, 'kernel': 3, 'stride': 2}
        ]
        
        for i, config in enumerate(stage_configs, 1):
            use_film = i in film_layers
            stage = CNNEncoderStage(
                config['in_ch'], config['out_ch'], config['kernel'], config['stride'],
                use_film=use_film, condition_dim=self.condition_dim if use_film else None
            )
            self.stages.append(stage)
        
        # ASPP module (matches config)
        self.aspp = ASPPModule(
            in_channels=256, 
            out_channels=256,
            dilation_rates=[6, 12, 18]
        )
        
        # Global context and final projection
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        self.final_projection = nn.Sequential(
            nn.Linear(256, self.embedding_dim * 2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(self.embedding_dim * 2, self.embedding_dim)
        )
        
    def forward(self, x, lead_times, months, hours):
        """
        Forward pass.
        
        Args:
            x: (B, C, H, W) weather data
            lead_times: (B,) lead times in hours
            months: (B,) months (0-11)
            hours: (B,) hours (0-23)
        
        Returns:
            embeddings: (B, embedding_dim) normalized embeddings
        """
        batch_size = x.size(0)
        
        # Create conditioning vector
        lead_emb = self.lead_time_embedding(lead_times)
        seasonal_emb = self.seasonal_embedding(months, hours)
        condition = torch.cat([lead_emb, seasonal_emb], dim=1)
        
        # Pass through CNN stages
        for i, stage in enumerate(self.stages):
            if hasattr(stage, 'use_film') and stage.use_film:
                x = stage(x, condition)
            else:
                x = stage(x)
        
        # ASPP module
        x = self.aspp(x)
        
        # Global average pooling
        x = self.global_pool(x)  # (B, C, 1, 1)
        x = x.view(batch_size, -1)  # (B, C)
        
        # Final projection
        embeddings = self.final_projection(x)
        
        # L2 normalize embeddings
        embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return embeddings

def calculate_model_hash(state_dict: Dict[str, torch.Tensor]) -> str:
    """Calculate SHA256 hash of model weights for reproducibility."""
    hash_obj = hashlib.sha256()
    
    # Sort keys for consistent hashing
    for key in sorted(state_dict.keys()):
        tensor = state_dict[key]
        # Convert to bytes and update hash
        hash_obj.update(key.encode('utf-8'))
        hash_obj.update(tensor.detach().cpu().numpy().tobytes())
    
    return hash_obj.hexdigest()

def validate_weight_loading(model: nn.Module, checkpoint_dict: Dict[str, torch.Tensor], 
                          matched_dict: Dict[str, torch.Tensor]) -> Tuple[bool, Dict[str, float]]:
    """Validate that weights were loaded correctly."""
    
    model_dict = model.state_dict()
    stats = {
        'total_model_params': len(model_dict),
        'total_checkpoint_params': len(checkpoint_dict),
        'matched_params': len(matched_dict),
        'match_percentage': len(matched_dict) / len(model_dict) * 100,
        'weight_norm_before': 0.0,
        'weight_norm_after': 0.0
    }
    
    # Calculate weight norms before/after (skip non-float tensors like num_batches_tracked)
    stats['weight_norm_before'] = sum(torch.norm(v.float()).item() for v in model_dict.values() if v.dtype.is_floating_point)
    
    # Check if critical layers are matched
    critical_layers = ['stages.0.conv.weight', 'stages.1.conv.weight', 'final_projection.0.weight']
    matched_critical = sum(1 for layer in critical_layers if layer in matched_dict)
    stats['critical_layers_matched'] = matched_critical / len(critical_layers) * 100
    
    # Validation thresholds
    success = (
        stats['match_percentage'] >= 90.0 and  # Hard gate: >=90% layers matched
        stats['critical_layers_matched'] >= 100.0  # All critical layers must match
    )
    
    return success, stats

def load_model_safe(model_path: Optional[str] = None, device: str = 'cpu', 
                   require_exact_match: bool = True) -> Optional[WeatherCNNEncoder]:
    """Safely load the trained model with robust validation.
    
    Args:
        model_path: Path to checkpoint file
        device: Device to load model on
        require_exact_match: If True, fails if <90% layers matched (expert threshold)
    
    Returns:
        Loaded model or None if loading failed validation
    """
    
    if model_path is None:
        # Find production model
        project_root = Path(__file__).parent.parent
        production_models = list(project_root.glob('outputs/training_production_*/best_model.pt'))
        if production_models:
            model_path = max(production_models, key=lambda p: p.stat().st_mtime)  # Most recent
            logger.info(f"Found production model: {model_path}")
        else:
            logger.error("No trained model found")
            return None
    
    model_path = Path(model_path)
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return None
    
    try:
        # Create model instance with correct architecture
        model = WeatherCNNEncoder(embedding_dim=256, num_variables=11)
        model_dict = model.state_dict()
        
        logger.info(f"Loading model from {model_path}")
        logger.info(f"Model expects {len(model_dict)} parameters")
        
        # Add the dummy config class to handle pickle loading
        import sys
        sys.modules['__main__'].ProductionTrainingConfig = ProductionTrainingConfig
        
        # Load checkpoint
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        # Extract state dict
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            logger.info(f"Found model_state_dict with {len(state_dict)} parameters")
        elif 'model' in checkpoint:
            state_dict = checkpoint['model']
            logger.info(f"Found model dict with {len(state_dict)} parameters")
        else:
            state_dict = checkpoint
            logger.info(f"Using checkpoint directly with {len(state_dict)} parameters")
        
        # Map checkpoint weights to model (direct mapping - architectures should match)
        filtered_dict = {}
        unmatched_checkpoint = []
        unmatched_model = []
        
        for k, v in state_dict.items():
            if k in model_dict:
                if model_dict[k].shape == v.shape:
                    filtered_dict[k] = v
                else:
                    logger.warning(f"Shape mismatch for {k}: model={model_dict[k].shape}, checkpoint={v.shape}")
                    unmatched_checkpoint.append(k)
            else:
                unmatched_checkpoint.append(k)
        
        # Check which model parameters weren't matched
        for k in model_dict:
            if k not in filtered_dict:
                unmatched_model.append(k)
        
        # Validate weight loading
        success, stats = validate_weight_loading(model, state_dict, filtered_dict)
        
        # Log detailed results
        logger.info(f"Weight Loading Results:")
        logger.info(f"  - Matched parameters: {stats['matched_params']}/{stats['total_model_params']} ({stats['match_percentage']:.1f}%)")
        logger.info(f"  - Critical layers matched: {stats['critical_layers_matched']:.1f}%")
        
        if unmatched_model:
            logger.warning(f"Unmatched model parameters ({len(unmatched_model)}): {unmatched_model[:10]}{'...' if len(unmatched_model) > 10 else ''}")
        
        if unmatched_checkpoint:
            logger.info(f"Unmatched checkpoint parameters ({len(unmatched_checkpoint)}): {unmatched_checkpoint[:10]}{'...' if len(unmatched_checkpoint) > 10 else ''}")
        
        # Apply hard gate for expert threshold
        if require_exact_match and not success:
            logger.error(f"CRITICAL: Weight loading failed validation!")
            logger.error(f"  - Only {stats['match_percentage']:.1f}% layers matched (required: ≥90%)")
            logger.error(f"  - Critical layers: {stats['critical_layers_matched']:.1f}% matched (required: 100%)")
            logger.error(f"  - Cannot use model with random weights - forecasts would be invalid")
            return None
        
        # Load the weights
        missing_keys, unexpected_keys = model.load_state_dict(filtered_dict, strict=False)
        
        # Calculate model hash for reproducibility
        model_hash = calculate_model_hash(model.state_dict())
        
        # Set to eval mode
        model.eval()
        model.to(device)
        
        logger.info(f"Model loaded successfully!")
        logger.info(f"  - Model hash: {model_hash[:16]}...")
        logger.info(f"  - Missing keys: {len(missing_keys)}")
        logger.info(f"  - Unexpected keys: {len(unexpected_keys)}")
        
        # Store metadata
        model._checkpoint_info = {
            'source_path': str(model_path),
            'match_percentage': stats['match_percentage'],
            'model_hash': model_hash,
            'validation_passed': success
        }
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        if require_exact_match:
            logger.error("require_exact_match=True: Refusing to create dummy model with random weights")
            return None
        
        # Fallback: create dummy model for testing only
        logger.warning("Creating dummy model for testing (WEIGHTS ARE RANDOM!)")
        model = WeatherCNNEncoder(embedding_dim=256, num_variables=11)
        model.eval()
        model.to(device)
        model._checkpoint_info = {
            'source_path': 'dummy',
            'match_percentage': 0.0,
            'model_hash': 'dummy',
            'validation_passed': False
        }
        return model

def test_model():
    """Test model loading and inference with comprehensive validation."""
    print("🧪 Testing Model Loader with Architecture Validation...")
    
    # Test with strict validation
    model = load_model_safe(require_exact_match=True)
    if model is None:
        print("❌ Model loading failed strict validation")
        print("   This indicates the checkpoint doesn't match the expected architecture")
        return False
    
    # Check checkpoint info
    if hasattr(model, '_checkpoint_info'):
        info = model._checkpoint_info
        print(f"📊 Checkpoint Info:")
        print(f"   - Source: {info['source_path']}")
        print(f"   - Match percentage: {info['match_percentage']:.1f}%")
        print(f"   - Model hash: {info['model_hash'][:16]}...")
        print(f"   - Validation passed: {info['validation_passed']}")
    
    # Test inference with correct input format
    try:
        batch_size = 4
        dummy_weather = torch.randn(batch_size, 9, 16, 16)
        dummy_lead_times = torch.tensor([6, 12, 24, 48])  # Hours
        dummy_months = torch.tensor([0, 3, 6, 9])  # Jan, Apr, Jul, Oct
        dummy_hours = torch.tensor([0, 6, 12, 18])  # 0, 6, 12, 18 UTC
        
        with torch.no_grad():
            embeddings = model(dummy_weather, dummy_lead_times, dummy_months, dummy_hours)
        
        print(f"✅ Model inference successful: {embeddings.shape}")
        print(f"   L2 norms: {[f'{norm:.3f}' for norm in embeddings.norm(dim=1).tolist()]}")
        print(f"   Embedding range: [{embeddings.min():.3f}, {embeddings.max():.3f}]")
        
        # Verify embeddings are properly normalized
        norms = embeddings.norm(dim=1)
        if torch.allclose(norms, torch.ones_like(norms), atol=1e-5):
            print(f"✅ Embeddings are properly L2-normalized")
        else:
            print(f"⚠️  Embeddings may not be properly normalized: {norms}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model inference failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def get_model_info(model_path: Optional[str] = None) -> Dict:
    """Get detailed information about a model checkpoint."""
    
    if model_path is None:
        project_root = Path(__file__).parent.parent
        production_models = list(project_root.glob('outputs/training_production_*/best_model.pt'))
        if production_models:
            model_path = max(production_models, key=lambda p: p.stat().st_mtime)
        else:
            return {'error': 'No trained model found'}
    
    model_path = Path(model_path)
    if not model_path.exists():
        return {'error': f'Model file not found: {model_path}'}
    
    try:
        # Load checkpoint metadata
        import sys
        sys.modules['__main__'].ProductionTrainingConfig = ProductionTrainingConfig
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        info = {
            'path': str(model_path),
            'file_size_mb': model_path.stat().st_size / (1024 * 1024),
            'checkpoint_keys': list(checkpoint.keys()) if isinstance(checkpoint, dict) else ['single_tensor'],
        }
        
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            info['model_parameters'] = len(state_dict)
            info['sample_keys'] = list(state_dict.keys())[:10]
            
            # Calculate total parameter count
            total_params = sum(v.numel() for v in state_dict.values())
            info['total_parameter_count'] = total_params
            info['total_parameter_count_human'] = f"{total_params:,}"
        
        if 'config' in checkpoint:
            info['training_config'] = str(type(checkpoint['config']))
        
        if 'epoch' in checkpoint:
            info['epoch'] = checkpoint['epoch']
        
        if 'train_loss' in checkpoint:
            info['train_loss'] = checkpoint['train_loss']
        
        if 'val_loss' in checkpoint:
            info['val_loss'] = checkpoint['val_loss']
        
        return info
        
    except Exception as e:
        return {'error': f'Failed to load checkpoint: {e}'}

if __name__ == "__main__":
    print("=== Weather CNN Model Loader Analysis ===\n")
    
    # Get detailed model information
    print("📋 Checkpoint Information:")
    info = get_model_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*50 + "\n")
    
    # Test model loading
    success = test_model()
    
    if success:
        print("\n🎉 Model loading and validation successful!")
        print("   The model is ready for production use.")
    else:
        print("\n💥 Model loading failed!")
        print("   Check the checkpoint architecture compatibility.")