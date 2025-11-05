#!/usr/bin/env python3
"""
Adelaide Weather Forecasting: Optimized CPU Embedding Generation
================================================================

Performance-optimized version implementing GPT-5 recommendations:
- Large zarr chunks to eliminate task overhead
- Single-process with controlled threading 
- Batched data processing to maximize CPU utilization

Usage:
    python generate_embeddings_optimized.py --output embeddings/ --batch-size 512 --threads 32
"""

import os
import sys
import argparse
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import xarray as xr
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from models.cnn_encoder import WeatherCNNEncoder as CNNEncoder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock class for loading checkpoint (needed for model loading)
class ProductionTrainingConfig:
    """Mock config class for checkpoint loading"""
    pass

class OptimizedEmbeddingGenerator:
    """Performance-optimized CPU embedding generator implementing GPT-5 recommendations."""
    
    def __init__(self, model_path: str, config_path: str, num_threads: int = 32):
        """Initialize optimized embedding generator.
        
        Args:
            model_path: Path to trained model weights
            config_path: Path to model configuration  
            num_threads: Number of CPU threads for PyTorch
        """
        # Set environment variables BEFORE importing torch/numpy (GPT-5 recommendation)
        os.environ['OMP_NUM_THREADS'] = str(num_threads)
        os.environ['MKL_NUM_THREADS'] = str(num_threads) 
        os.environ['OPENBLAS_NUM_THREADS'] = str(num_threads)
        os.environ['MKL_DYNAMIC'] = 'FALSE'
        
        # Configure PyTorch threading (single-process approach)
        torch.set_num_threads(num_threads)
        torch.set_num_interop_threads(1)  # Avoid nested parallelism
        
        # Force single-threaded dask scheduler to avoid conflicts
        import dask
        dask.config.set(scheduler='synchronous')
        
        logger.info(f"✅ Threading configured: {num_threads} threads, synchronous dask")
        logger.info(f"PyTorch threads: {torch.get_num_threads()}, interop: {torch.get_num_interop_threads()}")
        
        self.device = 'cpu'
        self.lead_times = [6, 12, 24, 48]  # Hours
        
        # Load trained model
        logger.info(f"Loading model from {model_path}")
        self.model = CNNEncoder(config_path=config_path)
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        logger.info("✅ Model loaded for CPU inference")
        
        # Load normalization statistics
        if 'norm_stats' in checkpoint:
            self.norm_stats = checkpoint['norm_stats']
            logger.info("✅ Normalization statistics loaded")
        else:
            logger.warning("⚠️ No normalization stats in checkpoint")
            self.norm_stats = None
            
        # Load ERA5 data with optimal chunking
        self._load_era5_data_optimized()
        
    def _load_era5_data_optimized(self):
        """Load ERA5 data with large chunks to minimize task overhead."""
        logger.info("Loading ERA5 data with optimized chunking...")
        
        try:
            # Load with large time chunks (GPT-5 recommendation: chunk size >> batch size)
            chunk_size = 2048  # Much larger than batch size to reduce overhead
            
            # Load surface data
            surface_path = "data/era5/zarr/era5_surface_2010_2020.zarr"
            self.surface_ds = xr.open_zarr(surface_path, chunks={'time': chunk_size})
            logger.info(f"Surface data chunks: {self.surface_ds.chunks}")
            
            # Load pressure level data  
            pressure_path = "data/era5/zarr/era5_pressure_2010_2019.zarr"
            self.pressure_ds = xr.open_zarr(pressure_path, chunks={'time': chunk_size})
            logger.info(f"Pressure data chunks: {self.pressure_ds.chunks}")
            
            # Slice to Adelaide region and persist in memory for faster access
            self.surface_ds = self.surface_ds.sel(
                latitude=slice(-33, -37),
                longitude=slice(137, 141)
            )
            self.pressure_ds = self.pressure_ds.sel(
                latitude=slice(-33, -37),
                longitude=slice(137, 141),
                isobaricInhPa=[500, 850]
            )
            
            # Persist data in memory to avoid repeated zarr reads (GPT-5 recommendation)
            logger.info("Persisting data in memory...")
            self.surface_ds = self.surface_ds.persist()
            self.pressure_ds = self.pressure_ds.persist()
            
            logger.info(f"✅ ERA5 data loaded and persisted - Adelaide region")
            logger.info(f"Surface grid: {self.surface_ds.latitude.size} x {self.surface_ds.longitude.size}")
            logger.info(f"Time range: {self.surface_ds.time.min().values} to {self.surface_ds.time.max().values}")
            
        except Exception as e:
            logger.error(f"Failed to load ERA5 data: {e}")
            raise
            
    def _normalize_variables(self, weather_array: np.ndarray) -> np.ndarray:
        """Apply per-variable normalization."""
        if self.norm_stats is None:
            return weather_array
            
        # Apply normalization per channel (vectorized)
        normalized = weather_array.copy()
        for i in range(weather_array.shape[-1]):
            var_name = f'var_{i}'
            if var_name in self.norm_stats:
                mean = self.norm_stats[var_name]['mean']
                std = self.norm_stats[var_name]['std']
                normalized[..., i] = (normalized[..., i] - mean) / (std + 1e-8)
                
        return normalized
        
    def _extract_batch_weather_data(self, time_indices: slice) -> Tuple[np.ndarray, List[Dict]]:
        """Extract weather data for a batch of timestamps - vectorized approach."""
        try:
            # Batch extraction using time slices (much more efficient than individual selects)
            surface_batch = self.surface_ds.isel(time=time_indices)
            pressure_batch = self.pressure_ds.isel(time=time_indices)
            
            # Extract times for metadata
            times = pd.to_datetime(surface_batch.time.values)
            
            # Extract surface MSL pressure
            msl_data = surface_batch['msl'].values  # Shape: (batch, lat, lon)
            
            # Resize from Adelaide grid to model input size (21x21)
            batch_size = msl_data.shape[0]
            msl_resized = np.array([np.resize(msl_data[i], (21, 21)) for i in range(batch_size)])
            
            # Extract pressure level variables (z, t, u, v at 500 and 850 hPa)
            pressure_vars = ['z', 't', 'u', 'v']
            all_arrays = [msl_resized]  # Start with surface pressure
            
            for var in pressure_vars:
                for level in [500, 850]:
                    var_data = pressure_batch[var].sel(isobaricInhPa=level).values
                    var_resized = np.array([np.resize(var_data[i], (21, 21)) for i in range(batch_size)])
                    all_arrays.append(var_resized)
            
            # Stack to create input array (batch, 21, 21, 9)
            weather_array = np.stack(all_arrays, axis=-1)
            
            # Generate metadata for batch
            metadata_list = []
            for i, time_val in enumerate(times):
                time_dt = time_val.to_pydatetime()
                metadata = {
                    'init_time': time_val,
                    'month': time_dt.month - 1,  # 0-11 for embedding
                    'hour': time_dt.hour,
                    'day_of_year': time_dt.timetuple().tm_yday,
                    'season': (time_dt.month - 1) // 3  # 0-3 for seasons
                }
                metadata_list.append(metadata)
            
            # Normalize variables
            normalized_array = np.array([self._normalize_variables(weather_array[i]) for i in range(batch_size)])
            
            return normalized_array, metadata_list
            
        except Exception as e:
            logger.error(f"Failed to extract batch weather data: {e}")
            return None, None
            
    def generate_embeddings_for_horizon(self, lead_time: int, batch_size: int = 512) -> Tuple[np.ndarray, pd.DataFrame]:
        """Generate embeddings for a specific forecast horizon - optimized batch processing.
        
        Args:
            lead_time: Forecast lead time in hours
            batch_size: Large batch size for CPU efficiency (GPT-5 recommendation)
            
        Returns:
            embeddings: (N, 256) normalized embeddings
            metadata: DataFrame with timestamps and target information
        """
        logger.info(f"🚀 Generating embeddings for {lead_time}h horizon (Optimized CPU)")
        
        # Get total number of timestamps
        total_times = len(self.surface_ds.time)
        logger.info(f"Processing {total_times} timestamps with batch_size={batch_size}")
        
        embeddings_list = []
        metadata_list = []
        
        start_time = time.time()
        
        # Process in large batches for maximum CPU utilization
        for i in range(0, total_times, batch_size):
            batch_start_time = time.time()
            
            end_idx = min(i + batch_size, total_times)
            time_slice = slice(i, end_idx)
            
            # Extract batch data (vectorized)
            weather_batch, batch_metadata = self._extract_batch_weather_data(time_slice)
            
            if weather_batch is None:
                continue
                
            # PyTorch inference with inference_mode for better performance
            with torch.inference_mode():
                # Convert to tensor (BHWC -> BCHW)
                weather_tensor = torch.from_numpy(weather_batch).float()
                weather_tensor = weather_tensor.permute(0, 3, 1, 2)
                
                # Generate conditioning variables
                batch_len = weather_tensor.shape[0]
                lead_times_tensor = torch.full((batch_len,), lead_time)
                months_tensor = torch.tensor([m['month'] for m in batch_metadata])
                hours_tensor = torch.tensor([m['hour'] for m in batch_metadata])
                
                # Generate embeddings (CPU inference)
                embeddings = self.model(weather_tensor, lead_times_tensor, months_tensor, hours_tensor)
                    
                # L2 normalize embeddings
                embeddings = F.normalize(embeddings, p=2, dim=1)
                embeddings_cpu = embeddings.numpy().astype(np.float32)
                
            # Add lead_time and valid_time to metadata
            for metadata in batch_metadata:
                time_dt = metadata['init_time'].to_pydatetime()
                valid_time = time_dt + timedelta(hours=lead_time)
                metadata['lead_time'] = lead_time
                metadata['valid_time'] = valid_time
                
            embeddings_list.append(embeddings_cpu)
            metadata_list.extend(batch_metadata)
            
            batch_time = time.time() - batch_start_time
            rate = batch_len / batch_time if batch_time > 0 else 0
            
            logger.info(f"Batch {i//batch_size + 1}: {end_idx}/{total_times} timestamps, "
                       f"{rate:.1f} timestamps/sec, {batch_time:.1f}s")
                
        # Combine all embeddings
        all_embeddings = np.vstack(embeddings_list)
        metadata_df = pd.DataFrame(metadata_list)
        
        total_time = time.time() - start_time
        avg_rate = len(metadata_df) / total_time if total_time > 0 else 0
        
        logger.info(f"✅ Generated {all_embeddings.shape[0]} embeddings for {lead_time}h")
        logger.info(f"Embedding shape: {all_embeddings.shape}")
        logger.info(f"⚡ Average rate: {avg_rate:.1f} timestamps/sec")
        
        return all_embeddings, metadata_df
        
    def save_embeddings(self, embeddings: np.ndarray, metadata: pd.DataFrame, 
                       output_dir: Path, lead_time: int):
        """Save embeddings and metadata to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save embeddings
        emb_path = output_dir / f"embeddings_{lead_time}h.npy"
        np.save(emb_path, embeddings)
        logger.info(f"💾 Saved embeddings to {emb_path}")
        
        # Save metadata
        meta_path = output_dir / f"metadata_{lead_time}h.parquet"
        metadata.to_parquet(meta_path, index=False)
        logger.info(f"💾 Saved metadata to {meta_path}")
        
    def generate_all_embeddings(self, output_dir: str, batch_size: int = 512):
        """Generate embeddings for all forecast horizons."""
        output_path = Path(output_dir)
        
        logger.info(f"🎯 Starting OPTIMIZED CPU embedding generation")
        logger.info(f"Output directory: {output_path}")
        logger.info(f"Forecast horizons: {self.lead_times}")
        logger.info(f"Batch size: {batch_size}")
        
        total_start = time.time()
        
        for lead_time in self.lead_times:
            horizon_start = time.time()
            
            embeddings, metadata = self.generate_embeddings_for_horizon(lead_time, batch_size)
            self.save_embeddings(embeddings, metadata, output_path, lead_time)
            
            horizon_time = time.time() - horizon_start
            rate = len(metadata) / horizon_time if horizon_time > 0 else 0
            logger.info(f"⏱️ {lead_time}h horizon: {horizon_time:.1f}s, {rate:.1f} timestamps/sec")
            
        total_time = time.time() - total_start
        logger.info(f"🎉 All embeddings generated in {total_time:.1f}s")

def main():
    parser = argparse.ArgumentParser(description='Generate embeddings - Performance Optimized (CPU)')
    parser.add_argument('--model', default='outputs/training_production_20251021_162407/best_model.pt',
                       help='Path to trained model')
    parser.add_argument('--config', default='configs/model.yaml',
                       help='Path to model config')
    parser.add_argument('--output', default='embeddings/',
                       help='Output directory')
    parser.add_argument('--batch-size', type=int, default=512,
                       help='Large batch size for CPU efficiency (recommended: 512+)')
    parser.add_argument('--threads', type=int, default=32,
                       help='Number of CPU threads (default: 32)')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Adelaide Weather Forecasting - Optimized Embedding Generation")
    logger.info(f"Configuration: batch_size={args.batch_size}, threads={args.threads}")
    
    # Initialize optimized generator
    generator = OptimizedEmbeddingGenerator(
        model_path=args.model,
        config_path=args.config,
        num_threads=args.threads
    )
    
    # Generate all embeddings
    generator.generate_all_embeddings(
        output_dir=args.output,
        batch_size=args.batch_size
    )
    
    logger.info("🎉 Optimized CPU embedding generation completed!")

if __name__ == "__main__":
    main()