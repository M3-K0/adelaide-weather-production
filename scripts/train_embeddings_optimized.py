#!/usr/bin/env python3
"""
Optimized Weather CNN Training Script - A100/A6000 Ready
All fixes consolidated from H200 testing.
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
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import warnings
warnings.filterwarnings('ignore')

# Add models to path
sys.path.append(str(Path(__file__).parent.parent / 'models'))
from cnn_encoder import CNNEncoder

@dataclass
class OptimizedTrainingConfig:
    """Optimized configuration for A100/A6000 training."""
    
    # Model config
    input_shape: List[int] = None
    embedding_dim: int = 256
    lead_time_embedding_dim: int = 64
    seasonal_embedding_dim: int = 32
    
    # Training config
    batch_size: int = 32  # Optimized for A100
    learning_rate: float = 0.0003
    weight_decay: float = 0.00001
    max_epochs: int = 20
    warmup_epochs: int = 2
    min_lr: float = 1e-5
    
    # InfoNCE config
    temperature: float = 0.2
    
    # Optimization
    gradient_clip: float = 5.0
    mixed_precision: bool = False  # Start disabled for stability
    
    # Data config
    train_split: float = 0.9
    chunk_size: int = 50  # Zarr chunking for fast I/O
    
    # Paths
    surface_path: str = "data/era5/zarr/era5_surface_2010_2020.zarr"
    pressure_path: str = "data/era5/zarr/era5_pressure_2010_2020.zarr"
    
    def __post_init__(self):
        if self.input_shape is None:
            self.input_shape = [21, 21, 11]

class WeatherDatasetOptimized:
    """Optimized dataset with chunked zarr loading and efficient batching."""
    
    def __init__(self, config: OptimizedTrainingConfig):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print(f"Loading datasets with chunking (chunk_size={config.chunk_size})...")
        
        # Load with chunking for fast I/O
        self.surface_ds = xr.open_zarr(config.surface_path).chunk({"time": config.chunk_size})
        self.pressure_ds = xr.open_zarr(config.pressure_path).chunk({"time": config.chunk_size})
        
        # Align datasets by time intersection
        surface_times = set(self.surface_ds.time.values)
        pressure_times = set(self.pressure_ds.time.values)
        common_times = sorted(surface_times.intersection(pressure_times))
        
        # Filter to common times
        self.surface_ds = self.surface_ds.sel(time=common_times)
        self.pressure_ds = self.pressure_ds.sel(time=common_times)
        
        print(f"Dataset aligned: {len(common_times)} timesteps")
        
        # Split times
        split_idx = int(len(common_times) * config.train_split)
        self.train_times = np.array(common_times[:split_idx])
        self.val_times = np.array(common_times[split_idx:])
        
        print(f"Train: {len(self.train_times)}, Val: {len(self.val_times)}")
        
        # Adelaide coordinates
        self.adelaide_lat = -34.9285
        self.adelaide_lon = 138.6007
        
    def get_batch(self, batch_size: Optional[int] = None, split: str = 'train', seed: Optional[int] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Get optimized batch with efficient data loading."""
        if batch_size is None:
            batch_size = self.config.batch_size
            
        if seed is not None:
            np.random.seed(seed)
        
        # Select times
        times = self.train_times if split == 'train' else self.val_times
        time_indices = np.random.choice(len(times), batch_size, replace=False)
        selected_times = times[time_indices]
        
        batch_data = []
        lead_times = []
        months = []
        hours = []
        
        for time_val in selected_times:
            try:
                # Convert time properly
                time_dt = np.datetime64(time_val).astype('datetime64[s]').astype(object)
                
                # Get surface data (Adelaide region)
                surface_data = self.surface_ds.sel(
                    time=time_val,
                    latitude=slice(-36, -33),
                    longitude=slice(137, 140),
                    method='nearest'
                ).load()
                
                # Get pressure data
                pressure_data = self.pressure_ds.sel(
                    time=time_val,
                    latitude=slice(-36, -33),
                    longitude=slice(137, 140),
                    level=[500, 850],
                    method='nearest'
                ).load()
                
                # Stack surface variables
                surface_vars = []
                for var in ['2m_temperature', 'mean_sea_level_pressure', '10m_u_component_of_wind', 
                           '10m_v_component_of_wind', 'total_precipitation']:
                    if var in surface_data.data_vars:
                        surface_vars.append(surface_data[var].values)
                
                # Stack pressure variables
                pressure_vars = []
                for level in [500, 850]:
                    for var in ['geopotential', 'temperature', 'u_component_of_wind', 'v_component_of_wind']:
                        if var in pressure_data.data_vars:
                            level_data = pressure_data[var].sel(level=level).values
                            pressure_vars.append(level_data)
                
                # Combine all variables
                all_vars = surface_vars + pressure_vars
                if len(all_vars) >= 11:
                    weather_array = np.stack(all_vars[:11], axis=-1)  # Take first 11 variables
                    
                    # Ensure correct shape [21, 21, 11]
                    if weather_array.shape != (21, 21, 11):
                        # Resize if needed
                        from scipy.ndimage import zoom
                        target_shape = (21, 21, 11)
                        if weather_array.shape[2] == 11:
                            # Only resize spatial dimensions
                            weather_array = zoom(weather_array, 
                                               (target_shape[0]/weather_array.shape[0],
                                                target_shape[1]/weather_array.shape[1], 1))
                        else:
                            weather_array = zoom(weather_array, 
                                               (target_shape[0]/weather_array.shape[0],
                                                target_shape[1]/weather_array.shape[1],
                                                target_shape[2]/weather_array.shape[2]))
                    
                    batch_data.append(weather_array)
                    
                    # Generate conditioning variables
                    lead_times.append(np.random.randint(6, 73))  # 6-72 hour forecast
                    months.append(time_dt.month)
                    hours.append(time_dt.hour)
                    
            except Exception as e:
                print(f"Error processing time {time_val}: {e}")
                continue
        
        if not batch_data:
            raise ValueError("No valid data found in batch")
        
        # Convert to tensors with efficient GPU transfer
        weather_tensor = torch.FloatTensor(np.array(batch_data)).to(self.device, non_blocking=True)
        lead_tensor = torch.LongTensor(lead_times).to(self.device, non_blocking=True)
        month_tensor = torch.LongTensor(months).to(self.device, non_blocking=True)
        hour_tensor = torch.LongTensor(hours).to(self.device, non_blocking=True)
        
        return weather_tensor, lead_tensor, month_tensor, hour_tensor

def setup_logging(output_dir: str) -> logging.Logger:
    """Setup optimized logging."""
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
    """Log FiLM gamma statistics for monitoring."""
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

def log_gradient_stats(model: nn.Module, logger: logging.Logger):
    """Log gradient statistics."""
    total_norm = 0.0
    grad_norms = []
    
    for name, param in model.named_parameters():
        if param.grad is not None:
            param_norm = param.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
            grad_norms.append(param_norm.item())
    
    total_norm = total_norm ** (1. / 2)
    
    if grad_norms:
        logger.info(f"Gradient Stats: min={min(grad_norms):.2e}, max={max(grad_norms):.2e}, "
                   f"mean={np.mean(grad_norms):.2e}")
        
        if min(grad_norms) < 1e-10:
            logger.warning(f"⚠️  Very small gradients detected: min={min(grad_norms):.2e}")

def compute_infonce_loss(embeddings: torch.Tensor, temperature: float) -> torch.Tensor:
    """Compute InfoNCE loss with numerical stability."""
    batch_size = embeddings.size(0)
    
    # Normalize embeddings
    embeddings_norm = F.normalize(embeddings, dim=-1)
    
    # Compute similarity matrix
    similarity = torch.matmul(embeddings_norm, embeddings_norm.T) / temperature
    
    # Create labels (each sample is positive with itself)
    labels = torch.arange(batch_size, device=embeddings.device)
    
    # InfoNCE loss
    loss = F.cross_entropy(similarity, labels)
    
    return loss

def smoke_test(model: nn.Module, dataset: WeatherDatasetOptimized, config: OptimizedTrainingConfig, 
               logger: logging.Logger) -> bool:
    """Run 200-step smoke test to validate training setup."""
    logger.info("🔍 Running 200-step smoke test...")
    
    model.train()
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    
    for step in range(200):
        try:
            # Get batch
            batch = dataset.get_batch(split='train')
            weather_data, lead_times, months, hours = batch
            
            # Forward pass
            optimizer.zero_grad()
            
            if config.mixed_precision:
                with autocast():
                    embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings.float()
            else:
                embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings
            
            # Compute loss
            loss = compute_infonce_loss(embeddings_fp32, config.temperature)
            
            if torch.isnan(loss) or torch.isinf(loss):
                logger.error(f"❌ NaN/Inf loss at step {step}: {loss.item()}")
                return False
            
            # Backward pass
            if config.mixed_precision:
                scaler = GradScaler()
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip)
                optimizer.step()
            
            # Logging
            if step % 20 == 0:
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'))
                logger.info(f"Step {step}/200: Loss={loss.item():.4f}, GradNorm={grad_norm:.2e}")
                
                log_film_gamma_stats(model, logger, step)
                log_gradient_stats(model, logger)
            
        except Exception as e:
            logger.error(f"Failed to get batch at step {step}: {e}")
            return False
    
    logger.info("✅ Smoke test passed - proceeding to full training")
    return True

def train_epoch(model: nn.Module, dataset: WeatherDatasetOptimized, optimizer: optim.Optimizer,
                scheduler: optim.lr_scheduler._LRScheduler, config: OptimizedTrainingConfig,
                logger: logging.Logger, epoch: int, scaler: Optional[GradScaler] = None) -> float:
    """Train one epoch."""
    model.train()
    total_loss = 0.0
    num_batches = max(1, len(dataset.train_times) // config.batch_size)
    
    for batch_idx in range(num_batches):
        try:
            # Get batch
            batch = dataset.get_batch(split='train')
            weather_data, lead_times, months, hours = batch
            
            # Forward pass
            optimizer.zero_grad()
            
            if config.mixed_precision and scaler:
                with autocast():
                    embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings.float()
            else:
                embeddings = model(weather_data, lead_times, months, hours)
                embeddings_fp32 = embeddings
            
            # Compute loss
            loss = compute_infonce_loss(embeddings_fp32, config.temperature)
            
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
            
        except Exception as e:
            logger.warning(f"Batch {batch_idx} failed: {e}")
            continue
    
    return total_loss / num_batches

def validate(model: nn.Module, dataset: WeatherDatasetOptimized, config: OptimizedTrainingConfig) -> float:
    """Validate model."""
    model.eval()
    total_loss = 0.0
    num_batches = max(1, len(dataset.val_times) // config.batch_size)
    
    with torch.no_grad():
        for _ in range(min(num_batches, 20)):  # Limit validation batches
            try:
                batch = dataset.get_batch(split='val')
                weather_data, lead_times, months, hours = batch
                
                embeddings = model(weather_data, lead_times, months, hours)
                loss = compute_infonce_loss(embeddings, config.temperature)
                total_loss += loss.item()
                
            except Exception:
                continue
    
    return total_loss / min(num_batches, 20)

def main():
    """Main training function with all optimizations."""
    # Load configuration
    with open('configs/model.yaml', 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # Create optimized config
    config = OptimizedTrainingConfig(
        input_shape=config_dict['encoder']['input_shape'],
        embedding_dim=config_dict['encoder']['embedding_dim'],
        batch_size=config_dict['training']['batch_size'],
        learning_rate=config_dict['training']['learning_rate'],
        weight_decay=config_dict['training']['weight_decay'],
        max_epochs=config_dict['training']['max_epochs'],
        temperature=config_dict['contrastive']['temperature']
    )
    
    # Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"outputs/training_optimized_{timestamp}"
    logger = setup_logging(output_dir)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"🚀 Starting Optimized Weather CNN Training")
    logger.info(f"Device: {device}")
    logger.info(f"Learning Rate: {config.learning_rate}")
    logger.info(f"Temperature: {config.temperature}")
    logger.info(f"Mixed Precision: {config.mixed_precision}")
    logger.info(f"Batch Size: {config.batch_size}")
    logger.info(f"Output Dir: {output_dir}")
    
    # Load dataset
    logger.info("Loading dataset...")
    dataset = WeatherDatasetOptimized(config)
    
    # Load model
    logger.info("Loading model...")
    model = CNNEncoder(
        input_shape=config.input_shape,
        embedding_dim=config.embedding_dim,
        lead_time_embedding_dim=config.lead_time_embedding_dim,
        seasonal_embedding_dim=config.seasonal_embedding_dim
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {total_params/1e6:.2f}M")
    
    # Run smoke test
    smoke_success = smoke_test(model, dataset, config, logger)
    if not smoke_success:
        logger.error("❌ Smoke test failed - aborting training")
        return
    
    # Setup training
    optimizer = optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, 
        T_max=config.max_epochs, 
        eta_min=config.min_lr
    )
    
    scaler = GradScaler() if config.mixed_precision else None
    
    # Training loop
    logger.info("🚀 Starting full training...")
    best_val_loss = float('inf')
    
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
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'config': config
            }, f"{output_dir}/best_model.pt")
            logger.info(f"💾 Saved best model (val_loss={val_loss:.4f})")
    
    logger.info("🎉 Training completed!")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Model saved to: {output_dir}/best_model.pt")

if __name__ == "__main__":
    main()