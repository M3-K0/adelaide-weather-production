#!/usr/bin/env python3
"""
Production Weather CNN Training Script - Fully Optimized
Implements all GPT-5 recommendations for maximum performance and reliability.
"""

import os
import sys
import logging
import yaml
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.cuda.amp import GradScaler, autocast
import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import warnings
import pickle
warnings.filterwarnings('ignore')

# Add models to path
sys.path.append(str(Path(__file__).parent.parent / 'models'))
from cnn_encoder import WeatherCNNEncoder as CNNEncoder

@dataclass
class ProductionTrainingConfig:
    """Production configuration implementing all GPT-5 recommendations."""
    
    # Model config
    input_shape: List[int] = None
    embedding_dim: int = 256
    lead_time_embedding_dim: int = 64
    seasonal_embedding_dim: int = 32
    
    # Training config
    batch_size: int = 128  # Optimized for A100
    learning_rate: float = 0.0003
    weight_decay: float = 0.00001
    max_epochs: int = 20
    warmup_epochs: int = 5
    min_lr: float = 1e-5
    
    # InfoNCE config with temporal positives
    temperature: float = 0.2
    temporal_window: int = 24  # Hours for positive pairs
    
    # Optimization
    gradient_clip: float = 5.0
    mixed_precision: bool = False  # Start disabled for stability
    channels_last: bool = True  # A100 optimization
    
    # Data config
    train_years: List[int] = None
    val_years: List[int] = None
    test_years: List[int] = None
    chunk_size: int = 100  # Larger chunks for vectorized loading
    
    # Paths
    surface_path: str = "data/era5/zarr/era5_surface_2010_2020.zarr"
    pressure_path: str = "data/era5/zarr/era5_pressure_2010_2019.zarr"
    
    def __post_init__(self):
        if self.input_shape is None:
            self.input_shape = [21, 21, 11]
        if self.train_years is None:
            self.train_years = [2010, 2018]
        if self.val_years is None:
            self.val_years = [2019]
        if self.test_years is None:
            self.test_years = [2020]

class WeatherDatasetProduction:
    """Production dataset with all GPT-5 optimizations implemented."""
    
    def __init__(self, config: ProductionTrainingConfig):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print(f"Loading datasets with optimized chunking (chunk_size={config.chunk_size})...")
        
        # Load with chunking for fast I/O
        self.surface_ds = xr.open_zarr(config.surface_path).chunk({"time": config.chunk_size})
        self.pressure_ds = xr.open_zarr(config.pressure_path).chunk({"time": config.chunk_size})
        
        # Pre-subset region and levels (GPT-5 recommendation A)
        print("Pre-subsetting Adelaide region and pressure levels...")
        self.surface_ds = self.surface_ds.sel(
            latitude=slice(-33, -37),
            longitude=slice(137, 141)
        )
        self.pressure_ds = self.pressure_ds.sel(
            latitude=slice(-33, -37),
            longitude=slice(137, 141),
            isobaricInhPa=[500, 850]
        )
        
        # Find actual time intersection manually
        print("Finding time intersection...")
        surface_times = set(self.surface_ds.time.values)
        pressure_times = set(self.pressure_ds.time.values)
        common_times = sorted(surface_times.intersection(pressure_times))
        
        print(f"Surface times: {len(surface_times)}, Pressure times: {len(pressure_times)}")
        print(f"Common times: {len(common_times)}")
        
        # Subset both datasets to common times
        self.surface_ds = self.surface_ds.sel(time=common_times)
        self.pressure_ds = self.pressure_ds.sel(time=common_times)
        
        print(f"Dataset aligned: {len(common_times)} timesteps")
        
        # Year-based splits (GPT-5 recommendation D)
        self._split_by_years(common_times)
        
        # Compute and cache normalization statistics (GPT-5 recommendation C)
        self._compute_normalization_stats()
        
        print(f"Train: {len(self.train_times)}, Val: {len(self.val_times)}")
        
    def _split_by_years(self, times):
        """Split data by years to prevent leakage."""
        time_df = pd.DataFrame({'time': times})
        time_df['year'] = pd.to_datetime(time_df['time']).dt.year
        
        # Filter by configured years
        train_mask = time_df['year'].isin(self.config.train_years)
        val_mask = time_df['year'].isin(self.config.val_years)
        
        self.train_times = time_df[train_mask]['time'].values
        self.val_times = time_df[val_mask]['time'].values
        
        print(f"Year-based splits: Train {self.config.train_years}, Val {self.config.val_years}")
        
    def _compute_normalization_stats(self):
        """Compute per-variable normalization statistics."""
        stats_file = "normalization_stats.pkl"
        
        if os.path.exists(stats_file):
            print("Loading cached normalization statistics...")
            with open(stats_file, 'rb') as f:
                self.norm_stats = pickle.load(f)
            return
            
        print("Computing normalization statistics on training data...")
        
        # Sample subset of training times for stats computation
        sample_times = np.random.choice(self.train_times, 
                                      min(1000, len(self.train_times)), 
                                      replace=False)
        
        # Load sample data
        surface_sample = self.surface_ds.sel(time=sample_times).load()
        pressure_sample = self.pressure_ds.sel(time=sample_times).load()
        
        # Compute stats per variable
        stats = {}
        
        # Surface variables (using actual variable names)
        surface_vars = ['msl']  # Only mean sea level pressure available
        for i, var in enumerate(surface_vars):
            if var in surface_sample.data_vars:
                data = surface_sample[var].values.flatten()
                stats[f'surface_{i}'] = {
                    'mean': float(np.nanmean(data)),
                    'std': float(np.nanstd(data) + 1e-8)  # Epsilon for numerical stability
                }
        
        # Pressure variables (using actual variable names)
        pressure_vars = ['z', 't', 'u', 'v']
        var_idx = len(surface_vars)
        for level in [500, 850]:
            for var in pressure_vars:
                if var in pressure_sample.data_vars:
                    data = pressure_sample[var].sel(isobaricInhPa=level).values.flatten()
                    stats[f'pressure_{var_idx}'] = {
                        'mean': float(np.nanmean(data)),
                        'std': float(np.nanstd(data) + 1e-8)
                    }
                    var_idx += 1
                    if var_idx >= 11:  # Only need 11 variables total
                        break
            if var_idx >= 11:
                break
        
        self.norm_stats = stats
        
        # Cache stats
        with open(stats_file, 'wb') as f:
            pickle.dump(stats, f)
        
        print(f"Computed normalization stats for {len(stats)} variables")
        
    def _normalize_variables(self, weather_array):
        """Apply per-variable normalization."""
        normalized = weather_array.copy()
        
        for i in range(min(9, weather_array.shape[-1])):
            key = None
            if i < 1:  # Only 1 surface variable
                key = f'surface_{i}'
            else:
                key = f'pressure_{i}'
            
            if key in self.norm_stats:
                mean = self.norm_stats[key]['mean']
                std = self.norm_stats[key]['std']
                normalized[..., i] = (normalized[..., i] - mean) / std
        
        return normalized
    
    def _find_temporal_positives(self, selected_times):
        """Find temporal positive pairs within the batch (GPT-5 recommendation B)."""
        pos_indices = []
        window_hours = self.config.temporal_window
        
        for i, anchor_time in enumerate(selected_times):
            anchor_dt = pd.to_datetime(anchor_time)
            
            # Find positive within temporal window
            positive_idx = i  # Default to self if no temporal neighbor found
            
            for j, candidate_time in enumerate(selected_times):
                if i == j:
                    continue
                    
                candidate_dt = pd.to_datetime(candidate_time)
                time_diff = abs((candidate_dt - anchor_dt).total_seconds() / 3600)  # Hours
                
                if time_diff <= window_hours:
                    positive_idx = j
                    break
            
            pos_indices.append(positive_idx)
        
        return torch.LongTensor(pos_indices)
    
    def get_batch(self, batch_size: Optional[int] = None, split: str = 'train', seed: Optional[int] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Vectorized batch loading with temporal positives (GPT-5 recommendations A, B, C)."""
        if batch_size is None:
            batch_size = self.config.batch_size
            
        if seed is not None:
            np.random.seed(seed)
        
        # Select times
        times = self.train_times if split == 'train' else self.val_times
        time_indices = np.random.choice(len(times), batch_size, replace=False)
        selected_times = times[time_indices]
        
        # Load data for each time individually to handle missing times
        valid_indices = []
        valid_times = []
        
        for idx, time_val in enumerate(selected_times):
            try:
                # Check if time exists in both datasets
                if (time_val in self.surface_ds.time.values and 
                    time_val in self.pressure_ds.time.values):
                    valid_indices.append(idx)
                    valid_times.append(time_val)
            except:
                continue
        
        if not valid_times:
            raise ValueError("No valid times found in selected batch")
            
        # Load data for valid times only
        surface_batch = self.surface_ds.sel(time=valid_times).load()
        pressure_batch = self.pressure_ds.sel(time=valid_times).load()
        selected_times = valid_times
        
        # Process all times vectorized
        batch_data = []
        lead_times = []
        months = []
        hours = []
        
        surface_vars = ['msl']  # Only mean sea level pressure available
        pressure_vars = ['z', 't', 'u', 'v']  # Short variable names
        
        for i, time_val in enumerate(selected_times):
            try:
                time_dt = pd.to_datetime(time_val)
                
                # Stack surface variables
                surface_arrays = []
                for var in surface_vars:
                    if var in surface_batch.data_vars:
                        data = surface_batch[var].isel(time=i).values
                        
                        # Debug: check data shape and content
                        if data.shape != (21, 21):
                            print(f"Surface {var} shape: {data.shape}, reshaping to 21x21")
                            if data.size == 0 or 0 in data.shape:
                                print(f"Error: Empty data for {var} at time {time_val}")
                                continue
                            # Ensure we have valid dimensions for zoom
                            if len(data.shape) < 2:
                                print(f"Error: Invalid data dimensions {data.shape} for {var}")
                                continue
                            from scipy.ndimage import zoom
                            zoom_factors = (21/data.shape[0], 21/data.shape[1])
                            data = zoom(data, zoom_factors, order=1)
                        surface_arrays.append(data)
                
                # Stack pressure variables
                pressure_arrays = []
                for level in [500, 850]:
                    for var in pressure_vars:
                        if var in pressure_batch.data_vars:
                            data = pressure_batch[var].sel(isobaricInhPa=level).isel(time=i).values
                            # Ensure 21x21 shape
                            if data.shape != (21, 21):
                                if data.size == 0:
                                    print(f"Warning: Empty data for {var} level {level} at time {time_val}")
                                    continue
                                from scipy.ndimage import zoom
                                zoom_factors = (21/data.shape[0], 21/data.shape[1])
                                data = zoom(data, zoom_factors, order=1)
                            pressure_arrays.append(data)
                            if len(pressure_arrays) >= 8:  # 4 vars × 2 levels = 8 pressure variables
                                break
                    if len(pressure_arrays) >= 8:
                        break
                
                # Combine variables [H, W, C] - we have 1 surface + 8 pressure = 9 total
                all_arrays = surface_arrays + pressure_arrays
                if len(all_arrays) >= 9:
                    weather_array = np.stack(all_arrays[:9], axis=-1)  # [21, 21, 9]
                    
                    # Apply normalization
                    weather_array = self._normalize_variables(weather_array)
                    
                    batch_data.append(weather_array)
                    
                    # Generate conditioning variables - fix ranges for embedding tables
                    lead_times.append(np.random.randint(0, 72))  # 0-71 for max_lead=72
                    months.append(time_dt.month - 1)  # Convert 1-12 to 0-11 for embedding  
                    hours.append(time_dt.hour)  # Already 0-23, correct
                    
            except Exception as e:
                print(f"Error processing time {time_val}: {e}")
                continue
        
        if not batch_data:
            raise ValueError("No valid data found in batch")
        
        # Find temporal positives
        pos_indices = self._find_temporal_positives(selected_times[:len(batch_data)])
        
        # Convert to tensors with pinned memory for efficient GPU transfer
        weather_array = np.array(batch_data)
        weather_tensor = torch.from_numpy(weather_array).pin_memory()
        weather_tensor = weather_tensor.to(self.device, non_blocking=True)
        
        # Convert to channels-first format [B, C, H, W] for CNN
        weather_tensor = weather_tensor.permute(0, 3, 1, 2)
        
        # Apply channels_last memory format for A100 optimization
        if self.config.channels_last:
            weather_tensor = weather_tensor.contiguous(memory_format=torch.channels_last)
        
        lead_tensor = torch.LongTensor(lead_times).to(self.device, non_blocking=True)
        month_tensor = torch.LongTensor(months).to(self.device, non_blocking=True)
        hour_tensor = torch.LongTensor(hours).to(self.device, non_blocking=True)
        pos_tensor = pos_indices.to(self.device, non_blocking=True)
        
        return weather_tensor, lead_tensor, month_tensor, hour_tensor, pos_tensor

def setup_logging(output_dir: str) -> logging.Logger:
    """Setup production logging."""
    os.makedirs(output_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"{output_dir}/training.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def log_film_gamma_stats(model: nn.Module, logger: logging.Logger, step: int):
    """Enhanced FiLM gamma statistics logging."""
    if step > 200:  # Only log for first 200 steps
        return
        
    gamma_stats = {}
    
    for name, module in model.named_modules():
        if hasattr(module, 'film_scale') and hasattr(module.film_scale, 'bias'):
            gamma = module.film_scale.bias.data  # gamma is stored in bias
            gamma_stats[name] = {
                'min': gamma.min().item(),
                'max': gamma.max().item(),
                'mean': gamma.mean().item(),
                'std': gamma.std().item()
            }
    
    if gamma_stats:
        logger.info(f"Step {step} FiLM Gamma Stats:")
        for name, stats in gamma_stats.items():
            logger.info(f"  {name}: min={stats['min']:.3f}, max={stats['max']:.3f}, "
                       f"mean={stats['mean']:.3f}, std={stats['std']:.3f}")

def log_embedding_stats(embeddings: torch.Tensor, logger: logging.Logger, step: int):
    """Enhanced embedding statistics (GPT-5 recommendation)."""
    if step % 20 != 0:
        return
        
    # Embedding norms before normalization
    embedding_norms = torch.norm(embeddings, dim=-1)
    
    # Similarity matrix statistics
    embeddings_norm = F.normalize(embeddings, dim=-1)
    similarity = torch.matmul(embeddings_norm, embeddings_norm.T)
    
    # Diagonal vs off-diagonal similarity stats
    diag_sim = torch.diag(similarity).mean().item()
    mask = ~torch.eye(similarity.size(0), dtype=torch.bool, device=similarity.device)
    off_diag_sim = similarity[mask].mean().item()
    off_diag_std = similarity[mask].std().item()
    
    logger.info(f"Step {step} Embedding Stats:")
    logger.info(f"  Norm: mean={embedding_norms.mean():.3f}, std={embedding_norms.std():.3f}")
    logger.info(f"  Similarity - Diag: {diag_sim:.3f}, Off-diag: {off_diag_sim:.3f}±{off_diag_std:.3f}")
    
    # Early warning for representation collapse
    if off_diag_sim > 0.8:
        logger.warning(f"⚠️  High off-diagonal similarity detected: {off_diag_sim:.3f} (potential collapse)")

def log_gradient_stats(model: nn.Module, logger: logging.Logger):
    """Enhanced gradient statistics."""
    total_norm = 0.0
    grad_norms = []
    zero_grad_params = 0
    total_params = 0
    
    for name, param in model.named_parameters():
        if param.grad is not None:
            param_norm = param.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
            grad_norms.append(param_norm.item())
            
            if param_norm.item() < 1e-12:
                zero_grad_params += 1
            total_params += 1
    
    total_norm = total_norm ** (1. / 2)
    
    if grad_norms:
        logger.info(f"Gradient Stats: min={min(grad_norms):.2e}, max={max(grad_norms):.2e}, "
                   f"mean={np.mean(grad_norms):.2e}")
        logger.info(f"Zero gradients: {zero_grad_params}/{total_params} parameters")
        
        if min(grad_norms) < 1e-10:
            logger.warning(f"⚠️  Very small gradients detected: min={min(grad_norms):.2e}")

def compute_infonce_loss_with_positives(embeddings: torch.Tensor, temperature: float, pos_indices: torch.Tensor) -> torch.Tensor:
    """Compute InfoNCE loss with temporal positives (GPT-5 recommendation B)."""
    batch_size = embeddings.size(0)
    
    # Normalize embeddings
    embeddings_norm = F.normalize(embeddings, dim=-1)
    
    # Compute similarity matrix
    similarity = torch.matmul(embeddings_norm, embeddings_norm.T) / temperature
    
    # Use temporal positive indices instead of identity
    loss = F.cross_entropy(similarity, pos_indices)
    
    return loss

class WarmupCosineScheduler:
    """Warmup + Cosine scheduler (GPT-5 recommendation D)."""
    
    def __init__(self, optimizer, warmup_epochs, max_epochs, eta_min, last_epoch=-1):
        self.optimizer = optimizer
        self.warmup_epochs = warmup_epochs
        self.max_epochs = max_epochs
        self.eta_min = eta_min
        self.last_epoch = last_epoch
        self.base_lrs = [group['lr'] for group in optimizer.param_groups]
        
    def get_lr(self):
        if self.last_epoch < self.warmup_epochs:
            # Linear warmup
            return [base_lr * (self.last_epoch + 1) / self.warmup_epochs for base_lr in self.base_lrs]
        else:
            # Cosine annealing
            progress = (self.last_epoch - self.warmup_epochs) / (self.max_epochs - self.warmup_epochs)
            return [self.eta_min + (base_lr - self.eta_min) * 0.5 * (1 + np.cos(np.pi * progress)) 
                   for base_lr in self.base_lrs]
    
    def step(self):
        self.last_epoch += 1
        for param_group, lr in zip(self.optimizer.param_groups, self.get_lr()):
            param_group['lr'] = lr
    
    def get_last_lr(self):
        return self.get_lr()

def smoke_test(model: nn.Module, dataset: WeatherDatasetProduction, config: ProductionTrainingConfig, 
               logger: logging.Logger) -> bool:
    """Enhanced smoke test with all optimizations."""
    logger.info("🔍 Running 200-step smoke test...")
    
    model.train()
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, 
                           weight_decay=config.weight_decay)
    
    # Create scaler once (GPT-5 recommendation F)
    scaler = GradScaler() if config.mixed_precision else None
    
    for step in range(200):
        try:
            # Get batch with temporal positives
            batch = dataset.get_batch(split='train')
            weather_data, lead_times, months, hours, pos_indices = batch
            
            # Forward pass
            optimizer.zero_grad(set_to_none=True)  # Memory optimization
            
            if config.mixed_precision and scaler:
                with autocast():
                    embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings.float()
            else:
                embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings
            
            # Compute loss with temporal positives
            loss = compute_infonce_loss_with_positives(embeddings_fp32, config.temperature, pos_indices)
            
            if torch.isnan(loss) or torch.isinf(loss):
                logger.error(f"❌ NaN/Inf loss at step {step}: {loss.item()}")
                return False
            
            # Backward pass
            if config.mixed_precision and scaler:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                optimizer.step()
            
            # Enhanced logging
            if step % 20 == 0:
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'))
                logger.info(f"Step {step}/200: Loss={loss.item():.4f}, GradNorm={grad_norm:.2e}")
                
                log_film_gamma_stats(model, logger, step)
                log_embedding_stats(embeddings_fp32, logger, step)
                log_gradient_stats(model, logger)
            
        except Exception as e:
            logger.error(f"Failed to get batch at step {step}: {e}")
            return False
    
    logger.info("✅ Smoke test passed - proceeding to full training")
    return True

def train_epoch(model: nn.Module, dataset: WeatherDatasetProduction, optimizer: optim.Optimizer,
                scheduler: WarmupCosineScheduler, config: ProductionTrainingConfig,
                logger: logging.Logger, epoch: int, scaler: Optional[GradScaler] = None) -> float:
    """Train one epoch with all optimizations."""
    model.train()
    total_loss = 0.0
    num_batches = max(1, len(dataset.train_times) // config.batch_size)
    
    for batch_idx in range(num_batches):
        try:
            # Get batch with temporal positives
            batch = dataset.get_batch(split='train')
            weather_data, lead_times, months, hours, pos_indices = batch
            
            # Forward pass
            optimizer.zero_grad(set_to_none=True)
            
            if config.mixed_precision and scaler:
                with autocast():
                    embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings.float()
            else:
                embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings
            
            # Compute loss with temporal positives
            loss = compute_infonce_loss_with_positives(embeddings_fp32, config.temperature, pos_indices)
            
            # Backward pass
            if config.mixed_precision and scaler:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                optimizer.step()
            
            total_loss += loss.item()
            
            # Log progress
            if batch_idx % 50 == 0:
                current_lr = scheduler.get_last_lr()[0]
                logger.info(f"Epoch {epoch}, Batch {batch_idx}/{num_batches}: "
                           f"Loss={loss.item():.4f}, LR={current_lr:.2e}")
                
                # Enhanced monitoring
                if batch_idx % 100 == 0:
                    log_embedding_stats(embeddings_fp32, logger, batch_idx)
            
        except Exception as e:
            logger.warning(f"Batch {batch_idx} failed: {e}")
            continue
    
    return total_loss / num_batches

def validate(model: nn.Module, dataset: WeatherDatasetProduction, config: ProductionTrainingConfig) -> float:
    """Validate model with temporal positives."""
    model.eval()
    total_loss = 0.0
    num_batches = max(1, len(dataset.val_times) // config.batch_size)
    
    with torch.no_grad():
        for _ in range(min(num_batches, 20)):  # Limit validation batches
            try:
                batch = dataset.get_batch(split='val')
                weather_data, lead_times, months, hours, pos_indices = batch
                
                embeddings = model(weather_data, lead_times, months, hours)
                loss = compute_infonce_loss_with_positives(embeddings, config.temperature, pos_indices)
                total_loss += loss.item()
                
            except Exception:
                continue
    
    return total_loss / min(num_batches, 20)

def main():
    """Main training function with all GPT-5 optimizations implemented."""
    # Set optimization flags (GPT-5 recommendation E)
    torch.backends.cudnn.benchmark = True
    
    # Set seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(42)
    
    # Load configuration
    with open('configs/model.yaml', 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # Create production config with all parameters
    config = ProductionTrainingConfig(
        input_shape=config_dict['encoder']['input_shape'],
        embedding_dim=config_dict['encoder']['embedding_dim'],
        batch_size=config_dict['training']['batch_size'],
        learning_rate=config_dict['training']['learning_rate'],
        weight_decay=config_dict['training']['weight_decay'],
        max_epochs=config_dict['training']['max_epochs'],
        warmup_epochs=config_dict['training']['warmup_epochs'],
        temperature=config_dict['contrastive']['temperature'],
        temporal_window=config_dict['contrastive']['temporal_window'],
        train_years=config_dict['training']['train_years'],
        val_years=config_dict['training']['val_years'],
        test_years=config_dict['training']['test_years']
    )
    
    # Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"outputs/training_production_{timestamp}"
    logger = setup_logging(output_dir)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"🚀 Starting Production Weather CNN Training")
    logger.info(f"Device: {device}")
    logger.info(f"Learning Rate: {config.learning_rate}")
    logger.info(f"Temperature: {config.temperature}")
    logger.info(f"Mixed Precision: {config.mixed_precision}")
    logger.info(f"Batch Size: {config.batch_size}")
    logger.info(f"Channels Last: {config.channels_last}")
    logger.info(f"Temporal Window: {config.temporal_window}h")
    logger.info(f"Output Dir: {output_dir}")
    
    # Load dataset
    logger.info("Loading dataset...")
    dataset = WeatherDatasetProduction(config)
    
    # Load model
    logger.info("Loading model...")
    model = CNNEncoder(config_path='configs/model.yaml').to(device)
    
    # Apply channels_last memory format (GPT-5 recommendation E)
    if config.channels_last:
        model = model.to(memory_format=torch.channels_last)
        logger.info("Applied channels_last memory format")
    
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {total_params/1e6:.2f}M")
    
    # Run smoke test
    smoke_success = smoke_test(model, dataset, config, logger)
    if not smoke_success:
        logger.error("❌ Smoke test failed - aborting training")
        return
    
    # Setup training with warmup scheduler
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    
    scheduler = WarmupCosineScheduler(
        optimizer,
        warmup_epochs=config.warmup_epochs,
        max_epochs=config.max_epochs,
        eta_min=config.min_lr
    )
    
    scaler = GradScaler() if config.mixed_precision else None
    
    # Training loop with early stopping
    logger.info("🚀 Starting full training...")
    best_val_loss = float('inf')
    patience_counter = 0
    patience = 10  # Early stopping patience
    
    for epoch in range(config.max_epochs):
        logger.info(f"Epoch {epoch+1}/{config.max_epochs}")
        
        # Train
        train_loss = train_epoch(model, dataset, optimizer, scheduler, config, logger, epoch, scaler)
        
        # Validate
        val_loss = validate(model, dataset, config)
        
        # Update scheduler
        scheduler.step()
        
        # Logging
        current_lr = scheduler.get_last_lr()[0]
        logger.info(f"Epoch {epoch+1}: Train Loss={train_loss:.4f}, Val Loss={val_loss:.4f}, LR={current_lr:.2e}")
        
        # Early stopping and checkpointing
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            
            # Save best model
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'config': config,
                'normalization_stats': dataset.norm_stats
            }, f"{output_dir}/best_model.pt")
            logger.info(f"💾 Saved best model (val_loss={val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping triggered after {patience} epochs without improvement")
                break
    
    logger.info("🎉 Training completed!")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Model saved to: {output_dir}/best_model.pt")

if __name__ == "__main__":
    main()